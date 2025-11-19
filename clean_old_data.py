"""
Redis 数据清理脚本
清理超过 24 小时的旧数据，保持数据新鲜度
"""
import redis
import json
import time
from datetime import datetime, timedelta


class RedisDataCleaner:
    """Redis 数据清理器"""
    
    def __init__(self, host='localhost', port=6379):
        self.host = host
        self.port = port
        
    def clean_old_data(self, db, queue_name, hours=24):
        """
        清理超过指定小时数的旧数据
        
        Args:
            db: Redis 数据库编号
            queue_name: 队列名称
            hours: 保留数据的小时数
        """
        r = redis.Redis(host=self.host, port=self.port, db=db, decode_responses=True)
        
        print(f"\n{'='*60}")
        print(f"清理 DB{db} 的 {queue_name} 队列")
        print(f"保留最近 {hours} 小时的数据")
        print('='*60)
        
        # 获取队列长度
        total = r.llen(queue_name)
        print(f"当前队列长度: {total}")
        
        if total == 0:
            print("队列为空，无需清理")
            return 0
        
        # 计算截止时间戳
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_timestamp = int(cutoff_time.timestamp())
        
        print(f"截止时间: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"截止时间戳: {cutoff_timestamp}")
        
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
                    
                    if removed % 100 == 0:
                        print(f"已清理 {removed} 条...")
                else:
                    # 遇到新数据，停止清理
                    break
                    
            except json.JSONDecodeError:
                # 无法解析的数据，删除
                r.rpop(queue_name)
                removed += 1
            except Exception as e:
                print(f"处理数据时出错: {e}")
                break
        
        remaining = r.llen(queue_name)
        
        print(f"\n清理完成:")
        print(f"  检查: {checked} 条")
        print(f"  删除: {removed} 条")
        print(f"  保留: {remaining} 条")
        
        return removed


def main():
    """主函数"""
    cleaner = RedisDataCleaner()
    
    print("\n" + "="*60)
    print("Redis 数据清理工具")
    print("="*60)
    
    # 清理原始数据队列（DB0）
    removed_raw = cleaner.clean_old_data(
        db=0,
        queue_name='data_queue',
        hours=24
    )
    
    # 清理清洗后数据队列（DB1）
    removed_clean = cleaner.clean_old_data(
        db=1,
        queue_name='clean_data_queue',
        hours=24
    )
    
    print("\n" + "="*60)
    print("清理总结")
    print("="*60)
    print(f"原始数据: 删除 {removed_raw} 条")
    print(f"清洗数据: 删除 {removed_clean} 条")
    print(f"总计删除: {removed_raw + removed_clean} 条")
    print("="*60)


if __name__ == '__main__':
    main()
