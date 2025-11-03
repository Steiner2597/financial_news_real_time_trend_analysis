"""
验证 Redis 中的数据是否都在24小时内
"""
import redis
import json
from datetime import datetime, timedelta
from collections import defaultdict

def verify_24hour_data():
    """验证数据时间范围"""
    
    # 连接 Redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✓ Redis 连接成功\n")
    except Exception as e:
        print(f"✗ Redis 连接失败: {e}")
        return
    
    # 获取队列长度
    queue_length = r.llen('data_queue')
    print(f"📊 当前队列长度: {queue_length} 条\n")
    
    if queue_length == 0:
        print("队列为空，无数据可验证")
        return
    
    # 获取所有数据
    print(f"正在读取 {queue_length} 条数据...")
    items = r.lrange('data_queue', 0, -1)
    
    # 统计数据
    now = datetime.now()
    cutoff = now - timedelta(hours=24)
    
    total_count = 0
    old_data_count = 0
    invalid_time_count = 0
    by_source = defaultdict(lambda: {'total': 0, 'old': 0, 'invalid': 0, 'oldest': None, 'newest': None})
    
    print(f"开始分析数据...\n")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"24小时截止: {cutoff.strftime('%Y-%m-%d %H:%M:%S')}\n")
    print("=" * 80)
    
    for item in items:
        try:
            data = json.loads(item)
            total_count += 1
            
            source = data.get('source', 'unknown')
            
            # 获取发布时间
            dt = None
            if 'created_at' in data:
                try:
                    # 尝试解析 ISO 格式
                    created_at = data['created_at']
                    if 'Z' in created_at:
                        created_at = created_at.replace('Z', '+00:00')
                    dt = datetime.fromisoformat(created_at.replace('+00:00', ''))
                except Exception as e:
                    pass
            
            if dt is None and 'timestamp' in data:
                try:
                    # Unix 时间戳
                    dt = datetime.fromtimestamp(data['timestamp'])
                except Exception as e:
                    pass
            
            if dt is None and 'published' in data:
                try:
                    # published 字段
                    published = data['published']
                    if 'Z' in published:
                        published = published.replace('Z', '+00:00')
                    dt = datetime.fromisoformat(published.replace('+00:00', ''))
                except Exception as e:
                    pass
            
            if dt is None:
                # 无法获取时间
                by_source[source]['invalid'] += 1
                invalid_time_count += 1
                continue
            
            # 更新统计
            by_source[source]['total'] += 1
            
            # 更新最早和最新时间
            if by_source[source]['oldest'] is None or dt < by_source[source]['oldest']:
                by_source[source]['oldest'] = dt
            if by_source[source]['newest'] is None or dt > by_source[source]['newest']:
                by_source[source]['newest'] = dt
            
            # 检查是否超过24小时
            if dt < cutoff:
                old_data_count += 1
                by_source[source]['old'] += 1
        
        except json.JSONDecodeError:
            print(f"⚠️ 无法解析数据: {item[:100]}...")
            continue
        except Exception as e:
            print(f"⚠️ 处理数据时出错: {e}")
            continue
    
    # 打印结果
    print("\n📈 整体统计")
    print("=" * 80)
    print(f"总数据量: {total_count} 条")
    print(f"超过24小时的数据: {old_data_count} 条 ({old_data_count/total_count*100:.2f}%)" if total_count > 0 else "总数据量: 0 条")
    print(f"无法获取时间的数据: {invalid_time_count} 条 ({invalid_time_count/total_count*100:.2f}%)" if total_count > 0 else "")
    print(f"有效且在24小时内: {total_count - old_data_count - invalid_time_count} 条 ({(total_count - old_data_count - invalid_time_count)/total_count*100:.2f}%)" if total_count > 0 else "")
    
    print("\n📊 各数据源详细统计")
    print("=" * 80)
    print(f"{'数据源':<20} {'总数':<8} {'超时':<8} {'无效时间':<10} {'超时比例':<10} {'时间范围'}")
    print("-" * 80)
    
    for source in sorted(by_source.keys()):
        stats = by_source[source]
        old_ratio = (stats['old'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        # 时间范围
        time_range = ""
        if stats['oldest'] and stats['newest']:
            time_range = f"{stats['oldest'].strftime('%m-%d %H:%M')} ~ {stats['newest'].strftime('%m-%d %H:%M')}"
        
        print(f"{source:<20} {stats['total']:<8} {stats['old']:<8} {stats['invalid']:<10} {old_ratio:>6.1f}%     {time_range}")
    
    print("=" * 80)
    
    # 结论
    print("\n🎯 验证结论")
    print("=" * 80)
    if old_data_count == 0 and invalid_time_count == 0:
        print("✅ 所有数据都在24小时内，目标达成！")
    elif old_data_count == 0:
        print(f"⚠️ 虽然没有超过24小时的数据，但有 {invalid_time_count} 条数据无法获取时间戳")
    else:
        print(f"❌ 有 {old_data_count} 条数据超过24小时，需要检查爬虫逻辑")
        print("\n超过24小时数据的来源:")
        for source, stats in by_source.items():
            if stats['old'] > 0:
                print(f"  - {source}: {stats['old']} 条")
    
    print("=" * 80)

if __name__ == "__main__":
    verify_24hour_data()
