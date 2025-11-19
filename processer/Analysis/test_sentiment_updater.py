"""
测试 BERT sentiment 更新功能
验证预测的 sentiment 是否成功写回 Redis 队列
"""
import sys
import json
from pathlib import Path
import redis

# 添加 Analysis 目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'Analysis'))

from config import CONFIG
from sentiment_updater import SentimentUpdater


def test_sentiment_updater():
    """测试 sentiment 更新器"""
    print("=" * 70)
    print("🧪 测试 BERT Sentiment 更新器")
    print("=" * 70)
    
    # 连接 Redis
    try:
        r = redis.Redis(
            host=CONFIG["redis"]["host"],
            port=CONFIG["redis"]["port"],
            db=CONFIG["redis"]["input_db"],
            decode_responses=True
        )
        r.ping()
        print("✅ Redis 连接成功\n")
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return
    
    # 创建更新器
    updater = SentimentUpdater(redis_client=r)
    
    # 获取队列状态
    print("📊 队列状态:")
    stats = updater.get_queue_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 检查队列中的数据
    print("\n📋 队列中的前 5 条数据:")
    queue_length = r.llen(updater.queue_name)
    for i in range(min(5, queue_length)):
        item_json = r.lindex(updater.queue_name, i)
        if item_json:
            try:
                item_data = json.loads(item_json)
                record_id = item_data.get('id') or item_data.get('post_id')
                sentiment = item_data.get('sentiment', '(缺失)')
                text_preview = item_data.get('text', '')[:50] if item_data.get('text') else '(无文本)'
                print(f"\n  [{i}] ID: {record_id}")
                print(f"      Sentiment: {sentiment}")
                print(f"      Text: {text_preview}...")
            except Exception as e:
                print(f"  [{i}] 解析失败: {e}")
    
    # 测试单条更新
    print("\n" + "=" * 70)
    print("🔄 测试单条 sentiment 更新")
    print("=" * 70)
    
    if queue_length > 0:
        # 获取第一条记录
        first_item_json = r.lindex(updater.queue_name, 0)
        try:
            first_item = json.loads(first_item_json)
            test_id = first_item.get('id') or first_item.get('post_id')
            old_sentiment = first_item.get('sentiment')
            
            # 测试更新
            new_sentiment = 'Bullish' if old_sentiment != 'Bullish' else 'Bearish'
            print(f"\n📝 更新记录:")
            print(f"  ID: {test_id}")
            print(f"  旧 Sentiment: {old_sentiment}")
            print(f"  新 Sentiment: {new_sentiment}")
            
            success = updater.update_sentiment_in_queue(str(test_id), new_sentiment)
            
            if success:
                print(f"\n✅ 更新成功!")
                
                # 验证更新结果
                updated_item_json = r.lindex(updater.queue_name, -1)  # 检查最后一条（重新插入的位置）
                updated_item = json.loads(updated_item_json)
                updated_id = updated_item.get('id') or updated_item.get('post_id')
                updated_sentiment = updated_item.get('sentiment')
                
                print(f"\n✓ 验证更新结果:")
                print(f"  ID: {updated_id}")
                print(f"  新 Sentiment: {updated_sentiment}")
                
                if updated_sentiment == new_sentiment:
                    print(f"\n✅ 验证通过！Sentiment 已正确更新")
                else:
                    print(f"\n❌ 验证失败！Sentiment 未正确更新")
            else:
                print(f"\n❌ 更新失败!")
        
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    else:
        print("⚠️  队列为空，无法测试")
    
    # 测试批量更新
    print("\n" + "=" * 70)
    print("📦 测试批量 sentiment 更新")
    print("=" * 70)
    
    if queue_length >= 2:
        try:
            # 获取前两条记录
            updates = []
            for i in range(min(2, queue_length)):
                item_json = r.lindex(updater.queue_name, i)
                if item_json:
                    item_data = json.loads(item_json)
                    record_id = item_data.get('id') or item_data.get('post_id')
                    sentiment = 'Bullish' if i == 0 else 'Bearish'
                    updates.append({'id': str(record_id), 'sentiment': sentiment})
            
            if updates:
                stats = updater.batch_update_sentiments(updates)
                print(f"\n✓ 批量更新统计: {stats}")
        
        except Exception as e:
            print(f"❌ 批量测试失败: {e}")
    else:
        print("⚠️  队列数据不足，无法测试")
    
    print("\n" + "=" * 70)
    print("✨ 测试完成")
    print("=" * 70)


if __name__ == '__main__':
    test_sentiment_updater()
