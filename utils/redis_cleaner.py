"""
Redis 数据清理工具模块
提供清理超过指定时间的旧数据功能
"""
import redis
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def clean_old_data_from_queue(
    host: str,
    port: int,
    db: int,
    queue_name: str,
    hours: int = 24,
    password: Optional[str] = None
) -> dict:
    """
    清理 Redis 队列中超过指定小时数的旧数据
    
    Args:
        host: Redis 主机
        port: Redis 端口
        db: 数据库编号
        queue_name: 队列名称
        hours: 保留数据的小时数
        password: Redis 密码（可选）
        
    Returns:
        dict: 清理统计信息
    """
    try:
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        r.ping()
    except Exception as e:
        logger.error(f"连接 Redis 失败: {e}")
        return {'success': False, 'error': str(e)}
    
    # 获取队列长度
    total = r.llen(queue_name)
    
    if total == 0:
        return {
            'success': True,
            'checked': 0,
            'removed': 0,
            'remaining': 0
        }
    
    # 计算截止时间戳
    cutoff_time = datetime.now() - timedelta(hours=hours)
    cutoff_timestamp = int(cutoff_time.timestamp())
    
    # 从队列尾部（最旧）开始检查
    removed = 0
    checked = 0
    
    while True:
        # 查看队列最后一个元素（最旧的数据）
        item = r.lindex(queue_name, -1)
        
        if not item:
            break
        
        checked += 1
        
        try:
            data = json.loads(item)
            item_timestamp = data.get('timestamp', 0)
            
            # 如果是 ISO 格式字符串，转换为时间戳
            if isinstance(item_timestamp, str):
                try:
                    dt = datetime.fromisoformat(item_timestamp.replace('Z', '+00:00'))
                    item_timestamp = int(dt.timestamp())
                except:
                    # 无法解析时间，保留数据
                    break
            
            # 如果数据时间在截止时间之前，删除
            if item_timestamp < cutoff_timestamp:
                r.rpop(queue_name)
                removed += 1
            else:
                # 遇到新数据，停止清理
                break
                
        except json.JSONDecodeError:
            # 无法解析的数据，删除
            r.rpop(queue_name)
            removed += 1
        except Exception as e:
            logger.error(f"处理数据时出错: {e}")
            break
    
    remaining = r.llen(queue_name)
    
    return {
        'success': True,
        'checked': checked,
        'removed': removed,
        'remaining': remaining,
        'cutoff_time': cutoff_time.isoformat()
    }
