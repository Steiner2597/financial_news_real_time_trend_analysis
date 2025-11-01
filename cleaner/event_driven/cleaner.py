"""
事件驱动清洗器主类
整合各个组件，提供完整的事件驱动清洗功能
"""
import logging
import time
from typing import Dict, Any
from pathlib import Path
import sys

# 从配置文件加载配置
import yaml

config_path = Path(__file__).parent.parent / "config_processing.yaml"
with open(config_path, 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

REDIS_HOST = CONFIG['redis']['host']
REDIS_PORT = CONFIG['redis']['port']
DB_IN = CONFIG['redis']['db_in']
DB_OUT = CONFIG['redis']['db_out']
QUEUE_IN = CONFIG['redis']['queue_in']
QUEUE_OUT = CONFIG['redis']['queue_out']
ID_CACHE_KEY = CONFIG['redis']['id_cache']
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 导入本模块的组件
from .redis_manager import RedisConnectionManager
from .notification_handler import NotificationHandler
from .cache_manager import CacheManager
from .signal_handler import SignalHandler
from .single_pass_cleaner import SinglePassCleaner

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "event_driven_cleaner.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EventDrivenCleaner:
    """事件驱动的清洗器"""
    
    def __init__(self):
        """初始化清洗器"""
        self.config = CONFIG
        
        # 监听配置（从 Scraper 接收）
        self.notification_listen = self.config.get('redis', {}).get('notification_listen', {})
        self.listen_enabled = self.notification_listen.get('enabled', False)
        self.listen_channel = self.notification_listen.get('channel', 'crawler_complete')
        self.mode = self.notification_listen.get('mode', 'event_driven')
        
        # 发送配置（发送给 Processor）
        self.notification_send = self.config.get('redis', {}).get('notification_send', {})
        self.send_enabled = self.notification_send.get('enabled', False)
        self.send_channel = self.notification_send.get('channel', 'cleaner_complete')
        
        # 去重配置
        self.dedup_config = self.config.get('deduplication', {})
        
        # 运行状态
        self.running = True
        
        # 初始化组件
        self.redis_manager = RedisConnectionManager(REDIS_HOST, REDIS_PORT)
        self.signal_handler = SignalHandler(self._stop)
        self.notification_handler = None  # 稍后初始化
        self.cache_manager = None  # 稍后初始化
        
        # 设置信号处理
        self.signal_handler.setup()
        
        # 打印初始化信息
        self._log_initialization()
    
    def _log_initialization(self):
        """记录初始化信息"""
        logger.info("=" * 70)
        logger.info("事件驱动清洗器初始化")
        logger.info("=" * 70)
        logger.info(f"模式: {self.mode}")
        logger.info(f"监听频道: {self.listen_channel} (启用: {self.listen_enabled})")
        logger.info(f"发送频道: {self.send_channel} (启用: {self.send_enabled})")
        logger.info("-" * 70)
        logger.info(f"去重模式: {self.dedup_config.get('mode', 'permanent')}")
        if self.dedup_config.get('mode') == 'time_window':
            logger.info(f"时间窗口: {self.dedup_config.get('window_hours', 24)} 小时")
        logger.info(f"启动时清空: {'是' if self.dedup_config.get('clear_on_start', False) else '否'}")
        logger.info("=" * 70)
    
    def _stop(self):
        """停止运行"""
        self.running = False
    
    def _connect_redis(self):
        """连接 Redis"""
        # 连接订阅
        self.redis_manager.connect_subscribe(DB_IN, self.listen_channel)
        
        # 连接发布（如果启用）
        if self.send_enabled:
            publish_client = self.redis_manager.connect_publish(DB_OUT)
        else:
            publish_client = None
        
        # 初始化通知处理器
        self.notification_handler = NotificationHandler(
            publish_client,
            self.send_enabled,
            self.send_channel
        )
        
        # 初始化缓存管理器（创建一个简单的连接器对象）
        import redis
        class SimpleConnector:
            def __init__(self, host, port, db):
                self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        
        r_out = SimpleConnector(REDIS_HOST, REDIS_PORT, DB_OUT)
        self.cache_manager = CacheManager(r_out, ID_CACHE_KEY, self.dedup_config)
        
        # 如果配置要求，清空 ID 缓存
        if self.dedup_config.get('clear_on_start', False):
            self.cache_manager.clear_cache()
    
    def _run_cleaning(self) -> int:
        """
        执行清洗任务（单次处理）
        
        Returns:
            清洗的数据量
        """
        try:
            # 创建单次清洗器
            cleaner = SinglePassCleaner(
                redis_host=REDIS_HOST,
                redis_port=REDIS_PORT,
                db_in=DB_IN,
                db_out=DB_OUT,
                queue_in=QUEUE_IN,
                queue_out=QUEUE_OUT,
                id_cache_key=ID_CACHE_KEY
            )
            
            # 执行单次清洗
            stats = cleaner.clean_once(batch_size=100)
            
            # 导出到文件
            if stats['cleaned'] > 0:
                logger.info("\n📦 导出清洗结果到文件...")
                output_dir = Path(__file__).parent.parent / "output"
                cleaner.export_to_file(output_dir)
            
            # 关闭清洗器
            cleaner.close()
            
            return stats['cleaned']
            
        except Exception as e:
            logger.error(f"清洗过程出错: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _process_notification(self, message: Dict[str, Any]):
        """
        处理收到的通知消息
        
        Args:
            message: 通知消息
        """
        try:
            # 显示清洗前的缓存状态
            self.cache_manager.log_cache_status("清洗前")
            
            # 处理消息并执行清洗
            cleaned_count = self.notification_handler.process_message(
                message,
                lambda msg: self._run_cleaning()
            )
            
            # 显示清洗后的缓存状态
            self.cache_manager.log_cache_status("清洗后")
            
            # 发送完成通知给 Processor
            logger.info("📤 准备发送清洗完成通知...")
            # 获取输出队列长度
            import redis
            r_out = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=DB_OUT,
                decode_responses=True
            )
            
            # 清理超过 24 小时的旧数据
            logger.info("\n🧹 清理超过 24 小时的旧数据...")
            clean_result = self._clean_old_data(r_out, QUEUE_OUT, hours=24)
            
            queue_length = r_out.llen(QUEUE_OUT)
            r_out.close()
            crawler_stats = message.get('statistics', {})
            
            self.notification_handler.send_completion_notification(
                cleaned_count,
                queue_length,
                crawler_stats
            )
            
            logger.info("=" * 70)
            logger.info("✨ 数据清洗完成")
            logger.info("=" * 70 + "\n")
            
        except Exception as e:
            logger.error(f"处理通知时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _clean_old_data(self, redis_conn, queue_name, hours=24):
        """
        清理超过指定时间的旧数据
        
        Args:
            redis_conn: Redis 连接对象（Redis 实例）
            queue_name: 队列名称
            hours: 保留时间（小时），默认 24 小时
            
        Returns:
            dict: 清理结果统计
        """
        logger.info(f"\n🗑️  开始清理超过 {hours} 小时的旧数据...")
        
        try:
            import json
            import time
            
            cutoff_timestamp = time.time() - (hours * 3600)
            removed_count = 0
            checked_count = 0
            
            # 获取队列长度
            queue_length = redis_conn.llen(queue_name)
            logger.info(f"队列 {queue_name} 当前长度: {queue_length}")
            
            if queue_length == 0:
                logger.info("队列为空，无需清理")
                return {
                    'removed': 0,
                    'checked': 0,
                    'remaining': 0
                }
            
            # 从队列尾部（最旧的数据）开始检查
            # 使用 LINDEX 逐个检查，遇到新数据就停止
            items_to_remove = []
            
            for i in range(queue_length - 1, -1, -1):  # 从尾部向头部遍历
                try:
                    # 获取队列中的数据
                    data_str = redis_conn.lindex(queue_name, i)
                    if not data_str:
                        continue
                    
                    checked_count += 1
                    data = json.loads(data_str)
                    
                    # 检查时间戳
                    if 'timestamp' not in data:
                        logger.warning(f"数据缺少 timestamp 字段，跳过: {data_str[:100]}")
                        continue
                    
                    timestamp = data['timestamp']
                    
                    # 如果是旧数据，标记删除
                    if timestamp < cutoff_timestamp:
                        items_to_remove.append(i)
                        removed_count += 1
                    else:
                        # 遇到新数据，停止检查（因为队列是按时间顺序的）
                        break
                    
                    # 每检查 100 条数据输出一次进度
                    if checked_count % 100 == 0:
                        logger.info(f"已检查 {checked_count} 条数据，发现 {removed_count} 条旧数据")
                
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 解析失败: {e}")
                    continue
                except Exception as e:
                    logger.error(f"处理数据时出错: {e}")
                    continue
            
            # 删除旧数据（从后往前删除，避免索引变化）
            if items_to_remove:
                logger.info(f"正在删除 {len(items_to_remove)} 条旧数据...")
                
                # 使用 LTRIM 删除尾部旧数据
                # 因为旧数据在尾部，我们只需要保留前面的新数据
                keep_count = queue_length - removed_count
                if keep_count > 0:
                    redis_conn.ltrim(queue_name, 0, keep_count - 1)
                else:
                    # 全部是旧数据，清空队列
                    redis_conn.delete(queue_name)
            
            remaining = redis_conn.llen(queue_name)
            
            logger.info(f"✅ 清理完成:")
            logger.info(f"   - 检查了 {checked_count} 条数据")
            logger.info(f"   - 删除了 {removed_count} 条旧数据")
            logger.info(f"   - 剩余 {remaining} 条数据")
            
            return {
                'removed': removed_count,
                'checked': checked_count,
                'remaining': remaining
            }
            
        except Exception as e:
            logger.error(f"清理旧数据时出错: {e}")
            import traceback
            traceback.print_exc()
            return {
                'removed': 0,
                'checked': 0,
                'remaining': redis_conn.llen(queue_name),
                'error': str(e)
            }
    
    def run_event_driven(self):
        """事件驱动模式：等待通知"""
        logger.info("\n" + "=" * 70)
        logger.info("🎧 事件驱动数据清洗器已就绪")
        logger.info("=" * 70)
        logger.info("监听频道: %s", self.listen_channel)
        logger.info("发送频道: %s", self.send_channel)
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 70 + "\n")
        
        # 连接 Redis
        self._connect_redis()
        
        # 获取 pubsub 对象
        pubsub = self.redis_manager.pubsub
        
        # 监听消息（使用超时以支持 Ctrl+C）
        try:
            while self.running:
                try:
                    # 使用 get_message() 带超时，而不是 listen()
                    raw_message = pubsub.get_message(timeout=1.0)
                    
                    if raw_message is None:
                        # 没有消息，继续等待
                        continue
                    
                    # 解析消息
                    message_data = self.notification_handler.parse_message(raw_message)
                    if message_data is None:
                        continue
                    
                    # 处理消息
                    self._process_notification(message_data)
                
                except KeyboardInterrupt:
                    logger.info("\n⚠️  收到键盘中断")
                    break
                except Exception as e:
                    if self.running:  # 只在运行时打印错误
                        logger.error(f"接收消息时出错: {e}")
                    time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("\n⚠️  收到中断信号")
        finally:
            self._cleanup()
    
    def run_continuous(self):
        """持续模式：定期检查队列（兼容旧模式）"""
        logger.info("\n" + "=" * 70)
        logger.info("🔄 持续轮询模式启动")
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 70 + "\n")
        
        try:
            import time
            # 使用单次清洗的轮询模式
            while self.running:
                try:
                    # 执行单次清洗
                    cleaned_count = self._run_cleaning()
                    
                    if cleaned_count > 0:
                        logger.info(f"✅ 本轮清洗完成，处理了 {cleaned_count} 条数据")
                    
                    # 等待一段时间再检查
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"轮询过程出错: {e}")
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            logger.info("\n⚠️  收到中断信号")
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        logger.info("\n" + "=" * 70)
        logger.info("🧹 清理资源...")
        
        # 清理 Redis 连接
        self.redis_manager.cleanup(self.listen_channel)
        
        # 恢复信号处理器
        self.signal_handler.restore()
        
        logger.info("👋 清洗器已停止")
        logger.info("=" * 70)
    
    def run(self):
        """根据配置运行"""
        if not self.listen_enabled:
            logger.warning("⚠️  通知功能未启用，使用持续模式")
            self.run_continuous()
        elif self.mode == 'event_driven':
            self.run_event_driven()
        else:
            self.run_continuous()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='事件驱动数据清洗器')
    parser.add_argument(
        '--mode',
        choices=['event_driven', 'continuous', 'once'],
        default=None,
        help='运行模式 (默认使用配置文件中的设置)'
    )
    args = parser.parse_args()
    
    cleaner = EventDrivenCleaner()
    
    # 命令行参数覆盖配置
    if args.mode:
        cleaner.mode = args.mode
    
    if args.mode == 'once':
        # 单次运行
        logger.info("🔄 单次运行模式")
        cleaner._run_cleaning()
    else:
        # 根据配置运行
        cleaner.run()


if __name__ == "__main__":
    main()
