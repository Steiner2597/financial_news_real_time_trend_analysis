"""
情感标签更新器
将 BERT 预测的 sentiment 实时更新到 Redis 队列
"""
import json
import redis
from typing import List, Dict, Any
from config import CONFIG


class SentimentUpdater:
    """将预测的 sentiment 更新回 Redis 队列"""
    
    def __init__(self, redis_client=None):
        """
        初始化情感更新器
        
        Args:
            redis_client: Redis 客户端（可选，如果为 None 则自动创建）
        """
        self.config = CONFIG
        
        if redis_client is not None:
            self.redis_client = redis_client
        else:
            try:
                self.redis_client = redis.Redis(
                    host=self.config["redis"]["host"],
                    port=self.config["redis"]["port"],
                    db=self.config["redis"]["input_db"],
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                self.redis_client.ping()
            except Exception as e:
                print(f"⚠️  Redis 连接失败: {e}")
                self.redis_client = None
        
        self.queue_name = self.config['redis'].get('output_queue_name', 'clean_data_queue')
    
    def update_sentiment_in_queue(self, record_id: str, sentiment: str) -> bool:
        """
        更新队列中特定记录的 sentiment 字段
        
        注意：由于 Redis 列表元素不可变，此方法将：
        1. 扫描列表找到目标记录
        2. 删除原记录
        3. 更新后重新插入到末尾
        
        Args:
            record_id: 记录 ID（id 或 post_id）
            sentiment: 预测的情感标签
            
        Returns:
            bool: 是否更新成功
        """
        if not self.redis_client:
            return False
        
        try:
            # 获取队列长度
            queue_length = self.redis_client.llen(self.queue_name)
            if queue_length == 0:
                return False
            
            # 逐个扫描队列元素
            found_index = -1
            original_data = None
            
            for i in range(queue_length):
                item_json = self.redis_client.lindex(self.queue_name, i)
                if not item_json:
                    continue
                
                try:
                    item_data = json.loads(item_json)
                    item_id = item_data.get('id') or item_data.get('post_id')
                    
                    if item_id == record_id:
                        found_index = i
                        original_data = item_data
                        break
                except json.JSONDecodeError:
                    continue
            
            # 如果找到目标记录
            if found_index >= 0 and original_data:
                # 更新 sentiment
                original_data['sentiment'] = sentiment
                
                # 删除原记录
                # 使用 LREM 删除第一个匹配项
                self.redis_client.lrem(self.queue_name, 1, json.dumps(original_data, ensure_ascii=False))
                
                # 重新插入到队尾
                self.redis_client.rpush(self.queue_name, json.dumps(original_data, ensure_ascii=False))
                
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ 更新 sentiment 失败 (ID: {record_id}): {e}")
            return False
    
    def batch_update_sentiments(self, updates: List[Dict[str, str]]) -> Dict[str, int]:
        """
        批量更新多条记录的 sentiment（优化版：并发更新）
        ✅ 使用 Redis 管道(pipeline) 和优化的扫描策略，加速批量更新
        
        Args:
            updates: 更新列表，每项格式为 {'id': record_id, 'sentiment': sentiment}
            
        Returns:
            dict: 统计信息 {'success': 成功数, 'failed': 失败数, 'not_found': 未找到数}
        """
        stats = {'success': 0, 'failed': 0, 'not_found': 0}
        
        if not self.redis_client:
            print("❌ Redis 未连接，无法更新")
            return stats
        
        if not updates:
            print("⚠️  没有需要更新的记录")
            return stats
        
        import time
        start_time = time.time()
        
        print(f"\n📤 开始批量更新 {len(updates)} 条 sentiment...")
        
        # ✅ 第一步：构建 ID -> sentiment 映射（加速查找）
        id_sentiment_map = {update['id']: update['sentiment'] for update in updates if update.get('id') and update.get('sentiment')}
        
        # ✅ 第二步：扫描队列并在一次管道中处理所有更新
        try:
            queue_length = self.redis_client.llen(self.queue_name)
            
            if queue_length == 0:
                print("⚠️  队列为空")
                return stats
            
            print(f"   队列长度: {queue_length}, 搜索 {len(id_sentiment_map)} 条记录...")
            
            # ✅ 优化：扫描整个队列一次，构建更新列表
            items_to_remove = []
            items_to_add = []
            
            for i in range(queue_length):
                item_json = self.redis_client.lindex(self.queue_name, i)
                if not item_json:
                    continue
                
                try:
                    item_data = json.loads(item_json)
                    item_id = str(item_data.get('id') or item_data.get('post_id', ''))
                    
                    # ✅ 如果这个 ID 需要更新
                    if item_id in id_sentiment_map:
                        item_data['sentiment'] = id_sentiment_map[item_id]
                        items_to_remove.append(item_json)
                        items_to_add.append(json.dumps(item_data, ensure_ascii=False))
                        stats['success'] += 1
                
                except json.JSONDecodeError:
                    continue
            
            # ✅ 第三步：使用管道一次性执行所有操作（避免网络往返开销）
            if items_to_remove or items_to_add:
                print(f"   找到 {stats['success']} 条需更新的记录，执行批量操作...")
                
                with self.redis_client.pipeline(transaction=False) as pipe:
                    # 删除旧记录
                    for item_json in items_to_remove:
                        pipe.lrem(self.queue_name, 1, item_json)
                    
                    # 添加新记录
                    if items_to_add:
                        pipe.rpush(self.queue_name, *items_to_add)
                    
                    # ✅ 执行管道
                    pipe.execute()
            else:
                stats['not_found'] = len(updates)
                print(f"   ⚠️  未在队列中找到需要更新的记录")
        
        except Exception as e:
            stats['failed'] = len(updates) - stats['success']
            print(f"  ❌ 批量更新异常: {e}")
            import traceback
            traceback.print_exc()
        
        # ✅ 性能统计
        elapsed_time = time.time() - start_time
        speed = len(updates) / elapsed_time if elapsed_time > 0 else 0
        
        print(f"\n📊 批量更新统计:")
        print(f"  成功: {stats['success']} 条")
        print(f"  失败: {stats['failed']} 条")
        print(f"  未找到: {stats['not_found']} 条")
        print(f"  耗时: {elapsed_time:.2f}s, 速度: {speed:.1f} 条/秒\n")
        
        return stats
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        if not self.redis_client:
            return {}
        
        try:
            queue_length = self.redis_client.llen(self.queue_name)
            
            # 统计缺失 sentiment 的记录数
            missing_sentiment_count = 0
            has_sentiment_count = 0
            
            for i in range(min(queue_length, 1000)):  # 只扫描前 1000 条以避免过慢
                item_json = self.redis_client.lindex(self.queue_name, i)
                if item_json:
                    try:
                        item_data = json.loads(item_json)
                        if item_data.get('sentiment'):
                            has_sentiment_count += 1
                        else:
                            missing_sentiment_count += 1
                    except:
                        pass
            
            return {
                'queue_length': queue_length,
                'has_sentiment': has_sentiment_count,
                'missing_sentiment': missing_sentiment_count,
                'scanned_items': min(queue_length, 1000)
            }
        
        except Exception as e:
            print(f"❌ 获取队列统计失败: {e}")
            return {}
