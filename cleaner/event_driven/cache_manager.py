"""
ID 缓存管理器
负责管理去重 ID 缓存的状态和操作
"""
import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CacheManager:
    """ID 缓存管理器"""
    
    def __init__(self, redis_connector, cache_key: str, dedup_config: Dict[str, Any]):
        """
        初始化缓存管理器
        
        Args:
            redis_connector: Redis 连接器（data_cleaner_module 中的 RedisConnector）
            cache_key: 缓存键名
            dedup_config: 去重配置
        """
        self.redis_connector = redis_connector
        self.cache_key = cache_key
        self.dedup_mode = dedup_config.get('mode', 'permanent')
        self.window_hours = dedup_config.get('window_hours', 24)
        self.clear_on_start = dedup_config.get('clear_on_start', False)
    
    def clear_cache(self):
        """清空 ID 缓存"""
        try:
            deleted = self.redis_connector.r.delete(self.cache_key)
            
            if deleted > 0:
                logger.info(f"✓ 已清空 ID 缓存: {self.cache_key}")
            else:
                logger.info(f"ℹ️  ID 缓存为空或不存在: {self.cache_key}")
        except Exception as e:
            logger.error(f"清空 ID 缓存失败: {e}")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        获取缓存状态信息
        
        Returns:
            包含缓存状态的字典
        """
        try:
            key_type = self.redis_connector.r.type(self.cache_key)
            
            status = {
                'type': key_type,
                'count': 0,
                'valid_count': 0,
                'expired_count': 0
            }
            
            if key_type == 'set':
                # SET 类型（永久模式）
                status['count'] = self.redis_connector.r.scard(self.cache_key)
                status['mode'] = 'permanent'
            
            elif key_type == 'zset':
                # ZSET 类型（时间窗口模式）
                count = self.redis_connector.r.zcard(self.cache_key)
                status['count'] = count
                status['mode'] = 'time_window'
                
                if count > 0 and self.dedup_mode == 'time_window':
                    # 统计过期和有效 ID
                    current_time = time.time()
                    expiry_time = current_time - (self.window_hours * 3600)
                    expired_count = self.redis_connector.r.zcount(self.cache_key, 0, expiry_time)
                    status['valid_count'] = count - expired_count
                    status['expired_count'] = expired_count
            
            elif key_type == 'none':
                status['mode'] = 'empty'
            else:
                status['mode'] = 'unknown'
            
            return status
            
        except Exception as e:
            logger.warning(f"获取缓存状态失败: {e}")
            return {'type': 'error', 'error': str(e)}
    
    def log_cache_status(self, stage: str = ""):
        """
        记录 ID 缓存状态到日志
        
        Args:
            stage: 阶段标识（如 "清洗前", "清洗后"）
        """
        status = self.get_cache_status()
        
        if stage:
            logger.info(f"\n📊 ID 缓存状态 ({stage}):")
        else:
            logger.info(f"\n📊 ID 缓存状态:")
        
        key_type = status.get('type')
        
        if key_type == 'set':
            logger.info(f"  类型: SET (永久模式)")
            logger.info(f"  总 ID 数: {status['count']}")
        
        elif key_type == 'zset':
            logger.info(f"  类型: ZSET (时间窗口模式)")
            logger.info(f"  总 ID 数: {status['count']}")
            
            if status['valid_count'] > 0 or status['expired_count'] > 0:
                logger.info(f"  有效 ID: {status['valid_count']}")
                logger.info(f"  过期 ID: {status['expired_count']}")
        
        elif key_type == 'none':
            logger.info(f"  状态: 空（未初始化）")
        elif key_type == 'error':
            logger.warning(f"  错误: {status.get('error', 'Unknown')}")
        else:
            logger.info(f"  类型: {key_type} (未知)")
