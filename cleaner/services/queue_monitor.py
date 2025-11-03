"""
数据队列监控器
实时监控 Redis data_queue 的变化，自动触发清洗
使用 Redis 键空间通知(Keyspace Notifications) 或轮询方式
"""
import logging
import time
import redis
from typing import Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class QueueMonitor:
    """
    队列监控器
    
    支持两种模式：
    1. Keyspace Notifications（推荐）- 需要 Redis 配置支持，实时性最好
    2. 轮询模式（备用）- 定期检查队列长度变化
    """
    
    def __init__(
        self,
        redis_host: str,
        redis_port: int,
        queue_name: str,
        db: int = 0,
        on_queue_update: Optional[Callable] = None,
        min_batch_size: int = 1,
        check_interval_sec: float = 0.5
    ):
        """
        初始化队列监控器
        
        Args:
            redis_host: Redis 主机地址
            redis_port: Redis 端口
            queue_name: 要监控的队列名称
            db: 数据库编号
            on_queue_update: 队列有更新时的回调函数
            min_batch_size: 触发清洗的最小批次大小
            check_interval_sec: 轮询间隔（秒）
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.queue_name = queue_name
        self.db = db
        self.on_queue_update = on_queue_update
        self.min_batch_size = min_batch_size
        self.check_interval_sec = check_interval_sec
        
        # 连接
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        
        # 状态
        self.running = True
        self.last_queue_length = 0
        self.last_check_time = time.time()
        self.update_count = 0
        self.keyspace_notifications_available = False
        
        self._connect()
    
    def _connect(self):
        """连接 Redis"""
        try:
            self.client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.db,
                decode_responses=True
            )
            self.client.ping()
            logger.info(f"✓ 队列监控器已连接 Redis: {self.redis_host}:{self.redis_port}/DB{self.db}")
            
            # 检查是否支持键空间通知
            self._check_keyspace_notifications_support()
            
        except Exception as e:
            logger.error(f"✗ 连接 Redis 失败: {e}")
            raise
    
    def _check_keyspace_notifications_support(self):
        """检查 Redis 是否支持键空间通知"""
        try:
            config = self.client.config_get('notify-keyspace-events')
            notify_config = config.get('notify-keyspace-events', '')
            
            # 检查是否启用了列表相关的通知
            # 'l' 表示列表操作，'E' 表示常规事件
            if 'l' in notify_config and 'E' in notify_config:
                self.keyspace_notifications_available = True
                logger.info(f"✓ Redis 键空间通知已启用: {notify_config}")
            else:
                logger.warning(f"⚠️  Redis 键空间通知未完全启用")
                logger.warning(f"   当前配置: {notify_config}")
                logger.warning(f"   建议配置: 'Kl' 或 'KEsl'")
                logger.info("   将使用轮询模式作为备用...")
                self.keyspace_notifications_available = False
                
        except Exception as e:
            logger.warning(f"⚠️  检查键空间通知支持时出错: {e}")
            logger.info("   将使用轮询模式作为备用...")
            self.keyspace_notifications_available = False
    
    def run_keyspace_mode(self):
        """
        使用键空间通知模式（推荐）
        监听 Redis 中队列的变化事件
        """
        logger.info("\n" + "=" * 70)
        logger.info("🔍 队列监控器 - 键空间通知模式")
        logger.info("=" * 70)
        logger.info(f"监控队列: {self.queue_name}")
        logger.info(f"最小触发批次: {self.min_batch_size}")
        logger.info("按 Ctrl+C 停止监控")
        logger.info("=" * 70 + "\n")
        
        try:
            # 创建订阅连接
            self.pubsub = self.client.pubsub()
            
            # 订阅列表操作事件
            # 频道格式: __keyspace_notification@{db}__:{key}
            # 事件包括: lpush, rpush, lpop, rpop, lset, ltrim 等
            channel = f"__keyevent@{self.db}__:lpush"
            self.pubsub.psubscribe(f"__keyevent@{self.db}__:*push")
            
            logger.info(f"✓ 已订阅键空间事件")
            
            # 初始化队列长度
            self.last_queue_length = self._get_queue_length()
            logger.info(f"初始队列长度: {self.last_queue_length}\n")
            
            # 监听事件
            while self.running:
                try:
                    message = self.pubsub.get_message(timeout=1.0)
                    
                    if message and message['type'] == 'pmessage':
                        # 检查是否是 data_queue 相关的事件
                        channel = message.get('channel', '')
                        if self.queue_name in channel or message.get('data') == self.queue_name:
                            self._handle_queue_update()
                    
                except Exception as e:
                    if self.running:
                        logger.error(f"监听事件出错: {e}")
                        time.sleep(1)
        
        except Exception as e:
            logger.error(f"键空间监听模式错误: {e}")
            logger.info("切换到轮询模式...")
            self.run_polling_mode()
        
        finally:
            self._cleanup_keyspace_mode()
    
    def run_polling_mode(self):
        """
        使用轮询模式（备用）
        定期检查队列长度是否有变化
        """
        logger.info("\n" + "=" * 70)
        logger.info("🔄 队列监控器 - 轮询模式（备用）")
        logger.info("=" * 70)
        logger.info(f"监控队列: {self.queue_name}")
        logger.info(f"检查间隔: {self.check_interval_sec} 秒")
        logger.info(f"最小触发批次: {self.min_batch_size}")
        logger.info("按 Ctrl+C 停止监控")
        logger.info("=" * 70 + "\n")
        
        try:
            # 初始化队列长度
            self.last_queue_length = self._get_queue_length()
            logger.info(f"初始队列长度: {self.last_queue_length}\n")
            
            consecutive_idle_rounds = 0
            max_idle_rounds = 3  # 连续3个检查周期无变化则打印一次
            
            # 使用小粒度 sleep 以支持快速中断
            min_sleep_unit = 0.1  # 最小 sleep 单位（秒）
            remaining_sleep = 0  # 剩余 sleep 时间
            
            while self.running:
                try:
                    # 分割 sleep 为多个小块，以实现快速响应中断信号
                    if remaining_sleep <= 0:
                        remaining_sleep = self.check_interval_sec
                    
                    sleep_time = min(min_sleep_unit, remaining_sleep)
                    time.sleep(sleep_time)
                    remaining_sleep -= sleep_time
                    
                    # 当完成一个完整的检查间隔时，执行检查
                    if remaining_sleep <= 0:
                        current_length = self._get_queue_length()
                        
                        # 检查队列是否有新数据
                        if current_length > self.last_queue_length:
                            # 有新数据进入
                            new_items = current_length - self.last_queue_length
                            
                            logger.info(f"\n📊 队列更新检测到!")
                            logger.info(f"   前次长度: {self.last_queue_length}")
                            logger.info(f"   当前长度: {current_length}")
                            logger.info(f"   新增数据: {new_items}")
                            
                            self.last_queue_length = current_length
                            self.update_count += 1
                            consecutive_idle_rounds = 0
                            
                            # 触发回调
                            if self.on_queue_update:
                                logger.info(f"🔔 触发清洗回调...")
                                try:
                                    self.on_queue_update(new_items)
                                except Exception as e:
                                    logger.error(f"执行回调出错: {e}")
                                    import traceback
                                    traceback.print_exc()
                        
                        elif current_length < self.last_queue_length:
                            # 队列长度减少（被处理或清理）
                            removed_items = self.last_queue_length - current_length
                            logger.info(f"📉 队列长度减少: {removed_items} 条 "
                                      f"({self.last_queue_length} → {current_length})")
                            self.last_queue_length = current_length
                            consecutive_idle_rounds = 0
                        
                        else:
                            # 队列长度无变化
                            consecutive_idle_rounds += 1
                            if consecutive_idle_rounds == max_idle_rounds:
                                logger.debug(f"✓ 持续监控中... 队列长度: {current_length}")
                                consecutive_idle_rounds = 0  # 重置计数
                
                except Exception as e:
                    if self.running:
                        logger.error(f"轮询出错: {e}")
                        remaining_sleep = self.check_interval_sec
        
        except KeyboardInterrupt:
            logger.info("\n⚠️  收到中断信号")
        
        finally:
            self._cleanup()
    
    def _handle_queue_update(self):
        """处理队列更新事件"""
        current_length = self._get_queue_length()
        
        if current_length > self.last_queue_length:
            new_items = current_length - self.last_queue_length
            
            logger.info(f"\n📊 键空间事件 - 队列更新")
            logger.info(f"   前次长度: {self.last_queue_length}")
            logger.info(f"   当前长度: {current_length}")
            logger.info(f"   新增数据: {new_items}")
            
            self.last_queue_length = current_length
            self.update_count += 1
            
            # 触发回调
            if self.on_queue_update:
                logger.info(f"🔔 触发清洗回调...")
                try:
                    self.on_queue_update(new_items)
                except Exception as e:
                    logger.error(f"执行回调出错: {e}")
                    import traceback
                    traceback.print_exc()
    
    def _get_queue_length(self) -> int:
        """获取当前队列长度"""
        try:
            return self.client.llen(self.queue_name)
        except Exception as e:
            logger.warning(f"获取队列长度失败: {e}")
            return 0
    
    def _cleanup_keyspace_mode(self):
        """清理键空间监听模式资源"""
        logger.info("\n🧹 清理键空间监听连接...")
        if self.pubsub:
            try:
                self.pubsub.punsubscribe()
                logger.info("✓ 已取消订阅")
            except Exception as e:
                logger.warning(f"取消订阅时出错: {e}")
    
    def _cleanup(self):
        """清理所有资源"""
        logger.info("\n🧹 队列监控器 - 清理资源")
        
        try:
            self._cleanup_keyspace_mode()
        except:
            pass
        
        if self.client:
            try:
                self.client.close()
                logger.info("✓ Redis 连接已关闭")
            except Exception as e:
                logger.warning(f"关闭连接时出错: {e}")
        
        logger.info(f"📊 监控统计: 检测到 {self.update_count} 次队列更新")
        logger.info("👋 队列监控器已停止")
    
    def stop(self):
        """停止监控"""
        self.running = False
    
    def run(self):
        """自动选择最优模式运行"""
        if self.keyspace_notifications_available:
            try:
                self.run_keyspace_mode()
            except Exception as e:
                logger.warning(f"键空间模式失败，切换到轮询模式: {e}")
                self.run_polling_mode()
        else:
            self.run_polling_mode()


class BatchedQueueMonitor(QueueMonitor):
    """
    批量队列监控器
    只在队列中累积到指定大小时才触发清洗，提高效率
    """
    
    def __init__(
        self,
        redis_host: str,
        redis_port: int,
        queue_name: str,
        db: int = 0,
        on_queue_update: Optional[Callable] = None,
        batch_size: int = 10,
        max_wait_sec: float = 5.0,
        check_interval_sec: float = 0.5
    ):
        """
        初始化批量队列监控器
        
        Args:
            redis_host: Redis 主机地址
            redis_port: Redis 端口
            queue_name: 要监控的队列名称
            db: 数据库编号
            on_queue_update: 队列有更新时的回调函数
            batch_size: 累积多少条数据才触发清洗
            max_wait_sec: 最长等待时间（秒），超过此时间即使未达到批量大小也触发
            check_interval_sec: 检查间隔（秒）
        """
        self.batch_size = batch_size
        self.max_wait_sec = max_wait_sec
        self.last_trigger_time = time.time()
        
        super().__init__(
            redis_host=redis_host,
            redis_port=redis_port,
            queue_name=queue_name,
            db=db,
            on_queue_update=None,  # 自己处理回调
            min_batch_size=batch_size,
            check_interval_sec=check_interval_sec
        )
        
        # 保存用户的回调函数
        self.user_callback = on_queue_update
        self.accumulated_items = 0
    
    def run_polling_mode(self):
        """重写轮询模式，实现批量触发逻辑"""
        logger.info("\n" + "=" * 70)
        logger.info("🔄 批量队列监控器 - 轮询模式")
        logger.info("=" * 70)
        logger.info(f"监控队列: {self.queue_name}")
        logger.info(f"批量大小: {self.batch_size} 条")
        logger.info(f"最长等待: {self.max_wait_sec} 秒")
        logger.info(f"检查间隔: {self.check_interval_sec} 秒")
        logger.info("按 Ctrl+C 停止监控")
        logger.info("=" * 70 + "\n")
        
        try:
            self.last_queue_length = self._get_queue_length()
            self.last_trigger_time = time.time()
            self.accumulated_items = 0
            
            logger.info(f"初始队列长度: {self.last_queue_length}\n")
            
            consecutive_idle_rounds = 0
            max_idle_rounds = 5
            
            while self.running:
                try:
                    time.sleep(self.check_interval_sec)
                    
                    current_length = self._get_queue_length()
                    current_time = time.time()
                    
                    # 检查是否有新数据
                    if current_length > self.last_queue_length:
                        new_items = current_length - self.last_queue_length
                        self.accumulated_items += new_items
                        
                        logger.info(f"📊 新增数据: {new_items} 条 (累计: {self.accumulated_items}/批次)")
                        
                        # 检查是否应该触发
                        should_trigger = False
                        trigger_reason = ""
                        
                        if self.accumulated_items >= self.batch_size:
                            should_trigger = True
                            trigger_reason = f"达到批量大小 ({self.batch_size})"
                            self.last_trigger_time = current_time
                        
                        elif (current_time - self.last_trigger_time) >= self.max_wait_sec:
                            should_trigger = True
                            trigger_reason = f"超过最长等待时间 ({self.max_wait_sec}秒)"
                            self.last_trigger_time = current_time
                        
                        if should_trigger:
                            logger.info(f"🔔 触发清洗 - {trigger_reason}")
                            if self.user_callback:
                                try:
                                    self.user_callback(self.accumulated_items)
                                except Exception as e:
                                    logger.error(f"执行回调出错: {e}")
                                    import traceback
                                    traceback.print_exc()
                            
                            self.accumulated_items = 0
                        
                        self.last_queue_length = current_length
                        consecutive_idle_rounds = 0
                    
                    elif current_length < self.last_queue_length:
                        # 队列被处理（外部清洗器）
                        removed_items = self.last_queue_length - current_length
                        logger.info(f"📉 队列处理: -({removed_items}条) "
                                  f"({self.last_queue_length} → {current_length})")
                        self.last_queue_length = current_length
                        consecutive_idle_rounds = 0
                    
                    else:
                        consecutive_idle_rounds += 1
                        if consecutive_idle_rounds == max_idle_rounds:
                            elapsed = current_time - self.last_trigger_time
                            logger.debug(f"✓ 监控中... 队列: {current_length}, "
                                       f"累计: {self.accumulated_items}, "
                                       f"距上次: {elapsed:.1f}秒")
                            consecutive_idle_rounds = 0
                
                except Exception as e:
                    if self.running:
                        logger.error(f"轮询出错: {e}")
                        time.sleep(self.check_interval_sec)
        
        except KeyboardInterrupt:
            logger.info("\n⚠️  收到中断信号")
        
        finally:
            self._cleanup()
