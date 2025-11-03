"""
事件驱动清洗器主类
整合各个组件，提供完整的事件驱动清洗功能

改进：改为基于 data_queue 的变化来自动触发清洗
不再依赖 scraper 的显式通知
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
from .queue_monitor import QueueMonitor, BatchedQueueMonitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "queue_driven_cleaner.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EventDrivenCleaner:
    """事件驱动的清洗器 - 现在改为基于队列变化自动触发清洗"""
    
    def __init__(self):
        """初始化清洗器"""
        self.config = CONFIG
        
        # 队列监控配置（新）
        self.queue_monitor_config = self.config.get('redis', {}).get('queue_monitor', {})
        self.monitor_enabled = self.queue_monitor_config.get('enabled', True)
        self.monitor_mode = self.queue_monitor_config.get('mode', 'batched')  # 'realtime' 或 'batched'
        self.batch_size = self.queue_monitor_config.get('batch_size', 10)
        self.max_wait_sec = self.queue_monitor_config.get('max_wait_sec', 5.0)
        self.check_interval = self.queue_monitor_config.get('check_interval_sec', 0.5)
        
        # 旧配置（兼容，用于可选的通知发送）
        self.notification_listen = self.config.get('redis', {}).get('notification_listen', {})
        self.listen_enabled = self.notification_listen.get('enabled', False)
        self.listen_channel = self.notification_listen.get('channel', 'crawler_complete')
        self.mode = self.notification_listen.get('mode', 'queue_driven')  # 改为 'queue_driven'
        
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
        self.notification_handler = None  # 可选初始化
        self.cache_manager = None  # 稍后初始化
        self.queue_monitor = None  # 队列监控器
        
        # 设置信号处理
        self.signal_handler.setup()
        
        # 打印初始化信息
        self._log_initialization()
    
    def _log_initialization(self):
        """记录初始化信息"""
        logger.info("=" * 70)
        logger.info("✨ 事件驱动清洗器初始化（基于队列变化触发）")
        logger.info("=" * 70)
        logger.info(f"监控模式: {self.monitor_mode}")
        logger.info(f"监控启用: {self.monitor_enabled}")
        
        if self.monitor_mode == 'batched':
            logger.info(f"批量大小: {self.batch_size} 条数据")
            logger.info(f"最长等待: {self.max_wait_sec} 秒")
        
        logger.info(f"检查间隔: {self.check_interval} 秒")
        logger.info(f"发送通知: {self.send_enabled} ({self.send_channel})")
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
        
        保留逻辑：只保留当前整点往前 N 小时的数据
        时间基准：使用 created_at 字段（数据的原始发布时间），如果没有则使用 timestamp
        
        示例：现在是 2025-11-02 15:30:45，当前整点是 15:00
        保留范围：2025-11-01 15:00:00 到现在
        删除范围：2025-11-01 15:00:00 之前的所有数据
        
        Args:
            redis_conn: Redis 连接对象（Redis 实例）
            queue_name: 队列名称
            hours: 保留时间（小时），默认 24 小时
            
        Returns:
            dict: 清理结果统计
        """
        logger.info(f"\n🗑️  开始清理数据 - 仅保留当前整点往前 {hours} 小时的数据...")
        logger.info(f"   📌 时间基准字段: created_at (原始发布时间) 或 timestamp (如果无 created_at)")
        
        try:
            import json
            from datetime import datetime, timezone
            
            # 获取当前时间的整点时刻（向下取整到整点）
            now = datetime.now(timezone.utc)
            current_hour = now.replace(minute=0, second=0, microsecond=0)
            
            # 计算保留时间的下界（当前整点 - N 小时）
            from datetime import timedelta
            cutoff_time = current_hour - timedelta(hours=hours)
            cutoff_timestamp = cutoff_time.timestamp()
            
            logger.info(f"当前时间: {now.isoformat()}")
            logger.info(f"当前整点: {current_hour.isoformat()}")
            logger.info(f"保留时间范围: {cutoff_time.isoformat()} 到现在")
            logger.info(f"删除阈值 (cutoff_timestamp): {cutoff_timestamp}")
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
                    
                    # 优先使用 created_at（原始发布时间），其次使用 timestamp（处理时间）
                    # created_at 是数据的原始发布时间（如 Reddit 帖子发布时间）
                    # timestamp 是 Cleaner 处理数据时添加的当前时间
                    time_field = None
                    if 'created_at' in data:
                        time_field = 'created_at'
                    elif 'timestamp' in data:
                        time_field = 'timestamp'
                    else:
                        logger.warning(f"数据既无 created_at 也无 timestamp，跳过: {data_str[:100]}")
                        continue
                    
                    time_value = data[time_field]
                    
                    # 转换时间戳为浮点数（处理字符串或数字类型）
                    try:
                        if isinstance(time_value, str):
                            # 如果是 ISO 格式字符串，转换为时间戳
                            if 'T' in time_value or '-' in time_value:
                                from datetime import datetime
                                # 处理不同的 ISO 格式
                                ts = time_value.replace('Z', '+00:00').replace(' ', 'T')
                                dt = datetime.fromisoformat(ts)
                                timestamp = dt.timestamp()
                            else:
                                # 尝试直接转为浮点数
                                timestamp = float(time_value)
                        elif isinstance(time_value, (int, float)):
                            # 已经是数字类型
                            timestamp = float(time_value)
                        else:
                            logger.warning(f"时间值类型不支持: {type(time_value)}, 跳过")
                            continue
                        
                    except (ValueError, TypeError) as e:
                        logger.warning(f"时间值转换失败: {time_value} ({type(time_value)}), 字段: {time_field}, 错误: {e}")
                        continue
                    
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
            logger.info(f"   📊 总检查数据: {checked_count} 条")
            logger.info(f"   🗑️  已删除数据: {removed_count} 条 (发布时间 < {cutoff_time.isoformat()})")
            logger.info(f"   ✨ 保留数据: {remaining} 条 (发布时间 >= {cutoff_time.isoformat()})")
            logger.info(f"   📌 判断依据: created_at 字段 (原始发布时间) / timestamp")
            logger.info(f"   🎯 时间窗口: {cutoff_time.isoformat()} 到 现在")
            
            return {
                'removed': removed_count,
                'checked': checked_count,
                'remaining': remaining,
                'cutoff_time': cutoff_time.isoformat(),
                'current_hour': current_hour.isoformat()
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
    
    def run_queue_driven(self):
        """
        基于队列变化触发的运行模式（新方式）
        监控 data_queue，只要有新数据就自动触发清洗
        """
        logger.info("\n" + "=" * 70)
        logger.info("✨ 基于队列变化的自动清洗模式启动")
        logger.info("=" * 70)
        logger.info(f"监控队列: {QUEUE_IN}")
        logger.info(f"监控模式: {self.monitor_mode}")
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 70 + "\n")
        
        try:
            # 初始化缓存管理器
            import redis
            class SimpleConnector:
                def __init__(self, host, port, db):
                    self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            
            r_out = SimpleConnector(REDIS_HOST, REDIS_PORT, DB_OUT)
            self.cache_manager = CacheManager(r_out, ID_CACHE_KEY, self.dedup_config)
            
            if self.dedup_config.get('clear_on_start', False):
                self.cache_manager.clear_cache()
            
            # 初始化通知处理器（可选，仅用于发送完成通知）
            if self.send_enabled:
                r_publish = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=DB_OUT,
                    decode_responses=True
                )
                self.notification_handler = NotificationHandler(
                    r_publish,
                    self.send_enabled,
                    self.send_channel
                )
            
            # 创建队列监控器
            if self.monitor_mode == 'batched':
                # 批量模式：累积到指定数量或超时才清洗
                self.queue_monitor = BatchedQueueMonitor(
                    redis_host=REDIS_HOST,
                    redis_port=REDIS_PORT,
                    queue_name=QUEUE_IN,
                    db=DB_IN,
                    on_queue_update=self._on_queue_update,
                    batch_size=self.batch_size,
                    max_wait_sec=self.max_wait_sec,
                    check_interval_sec=self.check_interval
                )
            else:
                # 实时模式：有任何变化都立即清洗
                self.queue_monitor = QueueMonitor(
                    redis_host=REDIS_HOST,
                    redis_port=REDIS_PORT,
                    queue_name=QUEUE_IN,
                    db=DB_IN,
                    on_queue_update=self._on_queue_update,
                    min_batch_size=1,
                    check_interval_sec=self.check_interval
                )
            
            # 启动监控
            self.queue_monitor.run()
        
        except KeyboardInterrupt:
            logger.info("\n⚠️  收到中断信号")
        except Exception as e:
            logger.error(f"队列驱动模式出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._cleanup()
    
    def _on_queue_update(self, new_items: int):
        """
        队列更新回调 - 执行清洗
        
        Args:
            new_items: 新增的数据条数
        """
        logger.info(f"\n📨 队列更新回调: 新增 {new_items} 条数据")
        
        try:
            # 显示清洗前的缓存状态
            if self.cache_manager:
                self.cache_manager.log_cache_status("清洗前")
            
            # 执行清洗
            cleaned_count = self._run_cleaning()
            
            # 显示清洗后的缓存状态
            if self.cache_manager:
                self.cache_manager.log_cache_status("清洗后")
            
            # 清理超过 24 小时的旧数据
            logger.info("\n🧹 清理超过 24 小时的旧数据...")
            import redis
            r_out = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=DB_OUT,
                decode_responses=True
            )
            clean_result = self._clean_old_data(r_out, QUEUE_OUT, hours=24)
            queue_length = r_out.llen(QUEUE_OUT)
            r_out.close()
            
            # 发送完成通知（如果启用）
            if self.send_enabled and self.notification_handler:
                logger.info("📤 发送清洗完成通知...")
                self.notification_handler.send_completion_notification(
                    cleaned_count,
                    queue_length,
                    {'new_items': new_items}
                )
            
            logger.info("=" * 70)
            logger.info(f"✨ 本次清洗完成: {cleaned_count} 条数据")
            logger.info("=" * 70 + "\n")
            
        except Exception as e:
            logger.error(f"清洗回调出错: {e}")
            import traceback
            traceback.print_exc()
    
    def run_event_driven(self):
        """事件驱动模式：等待通知（兼容旧模式）"""
        logger.info("\n" + "=" * 70)
        logger.info("🎧 事件驱动数据清洗器已就绪（基于 crawler_complete 通知）")
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
        # 优先使用基于队列监控的新方式
        if self.monitor_enabled and self.mode == 'queue_driven':
            self.run_queue_driven()
        # 兼容旧的基于通知的方式
        elif self.listen_enabled and self.mode == 'event_driven':
            self.run_event_driven()
        else:
            logger.warning("⚠️  两种模式都未启用，使用持续轮询模式作为备用")
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
