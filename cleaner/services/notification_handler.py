"""
消息通知处理器
负责处理接收和发送 Redis Pub/Sub 消息
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import redis

logger = logging.getLogger(__name__)


class NotificationHandler:
    """消息通知处理器"""
    
    def __init__(
        self,
        publish_client: Optional[redis.Redis],
        send_enabled: bool,
        send_channel: str
    ):
        """
        初始化通知处理器
        
        Args:
            publish_client: Redis 发布客户端
            send_enabled: 是否启用发送通知
            send_channel: 发送频道
        """
        self.publish_client = publish_client
        self.send_enabled = send_enabled
        self.send_channel = send_channel
    
    def parse_message(self, raw_message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析收到的消息
        
        Args:
            raw_message: 原始消息
            
        Returns:
            解析后的消息数据，或 None（如果不是数据消息）
        """
        # 过滤掉订阅确认消息
        if raw_message['type'] != 'message':
            return None
        
        # 解析 JSON 消息
        try:
            return json.loads(raw_message['data'])
        except json.JSONDecodeError:
            logger.warning(f"无法解析消息: {raw_message['data']}")
            return None
    
    def log_received_message(self, message: Dict[str, Any]):
        """
        记录收到的消息
        
        Args:
            message: 消息数据
        """
        logger.info("\n" + "=" * 70)
        logger.info("📬 收到爬虫完成通知")
        logger.info("=" * 70)
        
        event = message.get('event', 'unknown')
        timestamp = message.get('timestamp', 'N/A')
        stats = message.get('statistics', {})
        
        logger.info(f"事件类型: {event}")
        logger.info(f"时间戳: {timestamp}")
        logger.info(f"总数据量: {stats.get('total_items', 0)}")
        logger.info(f"队列长度: {stats.get('queue_length', 0)}")
        logger.info("-" * 70)
        
        # 显示各来源统计
        by_source = stats.get('by_source', {})
        for source, source_stats in by_source.items():
            logger.info(f"  {source}: {source_stats}")
        
        logger.info("=" * 70)
    
    def send_completion_notification(
        self,
        cleaned_count: int,
        queue_length: int,
        crawler_stats: Dict[str, Any]
    ):
        """
        发送清洗完成通知
        
        Args:
            cleaned_count: 清洗的数据量
            queue_length: 当前队列长度
            crawler_stats: 原始爬虫统计信息
        """
        logger.info(f"\n🔍 准备发送通知 - send_enabled: {self.send_enabled}, "
                   f"publish_client: {self.publish_client is not None}")
        
        if not self.send_enabled:
            logger.warning("⚠️  发送通知已禁用 (send_enabled=False)")
            return
        
        if not self.publish_client:
            logger.warning("⚠️  Redis 发送客户端未初始化")
            return
        
        try:
            # 构建通知消息
            message = {
                'event': 'clean_complete',
                'timestamp': datetime.now().isoformat(),
                'statistics': {
                    'cleaned_items': cleaned_count,
                    'queue_length': queue_length,
                    'crawler_stats': crawler_stats
                }
            }
            
            # 发送通知
            json_message = json.dumps(message, ensure_ascii=False)
            subscribers = self.publish_client.publish(self.send_channel, json_message)
            
            logger.info(f"\n📢 清洗完成通知已发送到频道 '{self.send_channel}' "
                       f"({subscribers} 个订阅者)")
            
        except Exception as e:
            logger.error(f"发送清洗完成通知失败: {e}")
    
    def process_message(
        self,
        message: Dict[str, Any],
        processing_callback: Callable[[Dict[str, Any]], int]
    ) -> int:
        """
        处理收到的消息并执行清洗
        
        Args:
            message: 消息数据
            processing_callback: 处理回调函数，返回处理数量
            
        Returns:
            处理的数据量
        """
        try:
            # 记录收到的消息
            self.log_received_message(message)
            
            logger.info("🚀 开始执行数据清洗...")
            logger.info("=" * 70)
            
            # 执行处理（通过回调）
            cleaned_count = processing_callback(message)
            
            logger.info(f"📊 清洗完成，共处理 {cleaned_count} 条数据")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            import traceback
            traceback.print_exc()
            return 0
