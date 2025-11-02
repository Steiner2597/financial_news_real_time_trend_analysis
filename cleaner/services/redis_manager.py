"""
Redis 连接管理器
负责管理 Redis 的订阅和发送连接
"""
import redis
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    """Redis 连接管理器"""
    
    def __init__(self, host: str, port: int):
        """
        初始化连接管理器
        
        Args:
            host: Redis 主机地址
            port: Redis 端口
        """
        self.host = host
        self.port = port
        self.subscribe_client: Optional[redis.Redis] = None
        self.publish_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
    
    def connect_subscribe(self, db: int, channel: str) -> redis.client.PubSub:
        """
        创建订阅连接
        
        Args:
            db: 数据库编号
            channel: 订阅频道
            
        Returns:
            PubSub 对象
        """
        try:
            self.subscribe_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=db,
                decode_responses=True
            )
            self.subscribe_client.ping()
            logger.info(f"✓ Redis 订阅连接成功: {self.host}:{self.port}/DB{db}")
            
            # 创建发布订阅对象
            self.pubsub = self.subscribe_client.pubsub()
            self.pubsub.subscribe(channel)
            logger.info(f"✓ 已订阅频道: {channel}")
            
            return self.pubsub
            
        except Exception as e:
            logger.error(f"✗ Redis 订阅连接失败: {e}")
            raise
    
    def connect_publish(self, db: int) -> redis.Redis:
        """
        创建发布连接
        
        Args:
            db: 数据库编号
            
        Returns:
            Redis 客户端
        """
        try:
            self.publish_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=db,
                decode_responses=True
            )
            self.publish_client.ping()
            logger.info(f"✓ Redis 发送连接成功: {self.host}:{self.port}/DB{db}")
            
            return self.publish_client
            
        except Exception as e:
            logger.error(f"✗ Redis 发送连接失败: {e}")
            raise
    
    def cleanup(self, listen_channel: str = ""):
        """
        清理所有连接
        
        Args:
            listen_channel: 订阅的频道名（用于日志）
        """
        logger.info("\n🧹 清理 Redis 连接...")
        
        # 清理订阅连接
        if self.pubsub:
            try:
                self.pubsub.unsubscribe()
                if listen_channel:
                    logger.info(f"✓ 已发送取消订阅请求: {listen_channel}")
            except Exception as e:
                logger.warning(f"  取消订阅时出错: {e}")
            
            try:
                self.pubsub.connection_pool = None
                self.pubsub.connection = None
                logger.info("✓ 已断开订阅连接")
            except Exception as e:
                logger.warning(f"  断开连接时出错: {e}")
        
        # 清理订阅客户端
        if self.subscribe_client:
            try:
                if hasattr(self.subscribe_client, 'connection_pool') and self.subscribe_client.connection_pool:
                    self.subscribe_client.connection_pool.disconnect()
                logger.info("✓ Redis 订阅连接已关闭")
            except Exception as e:
                logger.warning(f"  关闭订阅连接时出错: {e}")
        
        # 清理发布客户端
        if self.publish_client:
            try:
                if hasattr(self.publish_client, 'connection_pool') and self.publish_client.connection_pool:
                    self.publish_client.connection_pool.disconnect()
                logger.info("✓ Redis 发送连接已关闭")
            except Exception as e:
                logger.warning(f"  关闭发送连接时出错: {e}")
