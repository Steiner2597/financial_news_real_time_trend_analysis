"""
事件驱动的 Processor
监听 Cleaner 完成通知，收到通知后执行处理
"""
import time
import json
import signal
import sys
import redis
from datetime import datetime
from pathlib import Path

# 添加 Analysis 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG
from main import MainProcessor
from redis_manager import RedisManager


class EventDrivenProcessor:
    """事件驱动的处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.config = CONFIG
        self.notification_config = self.config['redis'].get('notification', {})
        self.enabled = self.notification_config.get('enabled', False)
        self.channel = self.notification_config.get('channel', 'cleaner_complete')
        self.mode = self.notification_config.get('mode', 'event_driven')
        
        self.processor = MainProcessor()
        self.redis_manager = RedisManager()
        self.running = True
        
        # Redis 订阅客户端
        self.redis_sub_client = None
        self.pubsub = None
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("=" * 70)
        print("事件驱动处理器初始化")
        print("=" * 70)
        print(f"模式: {self.mode}")
        print(f"监听频道: {self.channel}")
        print(f"通知启用: {self.enabled}")
        print("=" * 70)
    
    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        print("\n\n⚠️  收到退出信号，正在关闭...")
        self.running = False
        
        # 强制关闭 pubsub 连接以中断 get_message() 阻塞
        try:
            if self.pubsub:
                self.pubsub.close()
        except:
            pass
    
    def _connect_redis(self):
        """连接 Redis 订阅"""
        try:
            self.redis_sub_client = redis.Redis(
                host=self.config['redis']['host'],
                port=self.config['redis']['port'],
                db=self.config['redis']['input_db'],
                decode_responses=True
            )
            self.redis_sub_client.ping()
            print(f"✓ Redis 订阅连接成功: {self.config['redis']['host']}:{self.config['redis']['port']}/DB{self.config['redis']['input_db']}")
            
            # 创建发布订阅对象
            self.pubsub = self.redis_sub_client.pubsub()
            self.pubsub.subscribe(self.channel)
            print(f"✓ 已订阅频道: {self.channel}")
            
        except Exception as e:
            print(f"✗ Redis 连接失败: {e}")
            raise
    
    def _process_notification(self, message: dict):
        """
        处理收到的通知消息
        
        Args:
            message: 通知消息
        """
        try:
            print("\n" + "=" * 70)
            print("📬 收到清洗完成通知")
            print("=" * 70)
            
            # 解析消息
            if isinstance(message, dict):
                event = message.get('event', 'unknown')
                timestamp = message.get('timestamp', 'N/A')
                stats = message.get('statistics', {})
                
                print(f"事件类型: {event}")
                print(f"时间戳: {timestamp}")
                print(f"清洗数量: {stats.get('cleaned_items', 0)}")
                print(f"队列长度: {stats.get('queue_length', 0)}")
                
                # 显示原始爬虫统计
                crawler_stats = stats.get('crawler_stats', {})
                if crawler_stats:
                    print("\n原始数据统计:")
                    print(f"  总数据量: {crawler_stats.get('total_items', 0)}")
                    print(f"  总错误数: {crawler_stats.get('total_errors', 0)}")
            
            print("=" * 70)
            print("🚀 开始执行数据处理...")
            print("=" * 70)
            
            # 执行处理
            self._run_processing()
            
            print("=" * 70)
            print("✨ 数据处理完成")
            print("=" * 70 + "\n")
            
        except Exception as e:
            print(f"处理通知时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _run_processing(self):
        """执行处理任务"""
        try:
            # MainProcessor.process() 会自动：
            # 1. 从 Redis 读取数据（通过 DataLoader）
            # 2. 处理数据
            # 3. 保存到本地文件
            # 4. 发布到 Redis（通过 RedisManager）
            success = self.processor.process()
            
            if success:
                print("✅ 数据处理成功")
            else:
                print("⚠️  数据处理失败或无数据")
            
        except Exception as e:
            print(f"❌ 处理过程出错: {e}")
            import traceback
            traceback.print_exc()
    
    def run_event_driven(self):
        """事件驱动模式：等待通知"""
        print("\n" + "=" * 70)
        print("🎧 事件驱动数据处理器已就绪")
        print("=" * 70)
        print(f"监听频道: {self.channel}")
        print("按 Ctrl+C 停止")
        print("=" * 70 + "\n")
        
        # 连接 Redis
        self._connect_redis()
        
        # 监听消息（使用超时以支持 Ctrl+C）
        try:
            while self.running:
                try:
                    # 使用 get_message() 带超时，而不是 listen()
                    raw_message = self.pubsub.get_message(timeout=1.0)
                    
                    if raw_message is None:
                        # 没有消息，继续等待
                        continue
                    
                    # 过滤掉订阅确认消息
                    if raw_message['type'] != 'message':
                        continue
                    
                    # 解析消息
                    try:
                        message_data = json.loads(raw_message['data'])
                        self._process_notification(message_data)
                    except json.JSONDecodeError:
                        print(f"无法解析消息: {raw_message['data']}")
                    except Exception as e:
                        print(f"处理消息时出错: {e}")
                
                except Exception as e:
                    if self.running:  # 只在运行时打印错误
                        # 连接关闭是正常的（Ctrl+C 触发）
                        if "closed" not in str(e).lower():
                            print(f"接收消息时出错: {e}")
                    break
        
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        print("\n" + "=" * 70)
        print("🧹 清理资源...")
        
        try:
            # 直接关闭所有连接，不等待服务器响应
            if self.pubsub:
                try:
                    # 关闭底层连接（不发送 unsubscribe 命令）
                    if hasattr(self.pubsub, 'connection') and self.pubsub.connection:
                        self.pubsub.connection.disconnect()
                    self.pubsub.close()
                except:
                    pass
            
            if self.redis_sub_client:
                try:
                    # 直接断开连接池
                    self.redis_sub_client.close()
                except:
                    pass
            
        except:
            pass
        
        print("\n👋 处理器已停止")
    
    def run(self):
        """根据配置运行（仅支持事件驱动模式）"""
        if not self.enabled:
            print("❌ 错误：通知功能未启用")
            print("请在 config.py 中设置 redis.notification.enabled = True")
            return
        
        if self.mode != 'event_driven':
            print(f"⚠️  警告：不支持的模式 '{self.mode}'，切换到事件驱动模式")
            self.mode = 'event_driven'
        
        self.run_event_driven()


def main():
    """主函数"""
    processor = EventDrivenProcessor()
    processor.run()


if __name__ == "__main__":
    main()