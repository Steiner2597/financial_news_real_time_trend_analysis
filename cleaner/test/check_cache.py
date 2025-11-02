"""
缓存状态检查脚本
"""
import redis
import yaml
from pathlib import Path

# 加载配置
config_path = Path(__file__).parent.parent / "config_processing.yaml"
with open(config_path, 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

REDIS_HOST = CONFIG['redis']['host']
REDIS_PORT = CONFIG['redis']['port']
DB_OUT = CONFIG['redis']['db_out']
ID_CACHE_KEY = CONFIG['redis']['id_cache']

print("=" * 80)
print("🔍 缓存状态检查")
print("=" * 80)
print()

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=DB_OUT,
    decode_responses=True
)

print(f"连接: {REDIS_HOST}:{REDIS_PORT} (DB{DB_OUT})")
print(f"缓存键: {ID_CACHE_KEY}")
print()

cache_type = r.type(ID_CACHE_KEY)
print(f"缓存类型: {cache_type}")

if cache_type == 'set':
    count = r.scard(ID_CACHE_KEY)
    print(f"缓存大小: {count} 个 ID")
    
    if count > 0:
        print(f"\n示例 ID（前 5 个）:")
        sample_ids = r.srandmember(ID_CACHE_KEY, min(5, count))
        for idx, id_val in enumerate(sample_ids, 1):
            print(f"  {idx}. {id_val}")

elif cache_type == 'zset':
    count = r.zcard(ID_CACHE_KEY)
    print(f"缓存大小: {count} 个 ID")
    
    if count > 0:
        print(f"\n示例 ID（最新 5 个）:")
        latest = r.zrange(ID_CACHE_KEY, -5, -1, withscores=True)
        for idx, (id_val, score) in enumerate(latest, 1):
            from datetime import datetime
            ts = datetime.fromtimestamp(score)
            print(f"  {idx}. {id_val} (时间: {ts})")

elif cache_type == 'none':
    print("缓存不存在或为空")

else:
    print(f"未知类型: {cache_type}")

print()

# 检查统计信息
print("=" * 80)
print("📊 统计信息")
print("=" * 80)

accepted = r.get("stats:accepted")
discarded = r.get("stats:discarded")

print(f"已接受: {accepted or '0'}")
print(f"已丢弃: {discarded or '0'}")

print()
