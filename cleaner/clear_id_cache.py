"""
清空 ID 缓存 - 解决类型冲突
"""
import redis
import yaml
from pathlib import Path

def clear_cache():
    """清空 ID 缓存"""
    
    # 加载配置（当前目录下的配置文件）
    config_path = Path(__file__).parent / "config_processing.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    redis_config = config['redis']
    cache_key = redis_config['id_cache']
    
    print("=" * 70)
    print("清空 ID 缓存工具")
    print("=" * 70)
    
    # 连接 Redis
    r = redis.Redis(
        host=redis_config['host'],
        port=redis_config['port'],
        db=redis_config['db_out'],
        decode_responses=True
    )
    
    try:
        r.ping()
        print(f"✅ Redis 连接成功")
    except:
        print(f"❌ Redis 连接失败")
        return
    
    # 检查当前缓存
    key_type = r.type(cache_key)
    print(f"\n当前缓存:")
    print(f"  键名: {cache_key}")
    print(f"  类型: {key_type}")
    
    if key_type == 'set':
        count = r.scard(cache_key)
        print(f"  数量: {count} 个 ID")
    elif key_type == 'zset':
        count = r.zcard(cache_key)
        print(f"  数量: {count} 个 ID")
    elif key_type == 'none':
        print(f"  状态: 空")
    
    # 确认删除
    print("\n⚠️  这将删除所有已记录的 ID，允许重新处理所有数据")
    confirm = input("确认删除？(yes/no): ").strip().lower()
    
    if confirm == 'yes':
        deleted = r.delete(cache_key)
        if deleted > 0:
            print(f"\n✅ 已删除缓存键: {cache_key}")
        else:
            print(f"\n✅ 缓存已经是空的")
        
        print("\n现在可以重启 Cleaner，它将使用新的去重模式")
        print("运行: start_cleaner.bat")
    else:
        print("\n❌ 已取消")
    
    r.close()

if __name__ == "__main__":
    try:
        clear_cache()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
