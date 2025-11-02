"""
清洗调试脚本
直接测试单条数据的清洗过程
"""
import sys
from pathlib import Path
import json
import redis
import yaml

# 加载配置
config_path = Path(__file__).parent.parent / "config_processing.yaml"
with open(config_path, 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

REDIS_HOST = CONFIG['redis']['host']
REDIS_PORT = CONFIG['redis']['port']
DB_IN = CONFIG['redis']['db_in']
QUEUE_IN = CONFIG['redis']['queue_in']

# 导入清洗器
sys.path.insert(0, str(Path(__file__).parent.parent))
from event_driven.single_pass_cleaner import SinglePassCleaner

print("=" * 80)
print("🔍 Cleaner 调试工具")
print("=" * 80)
print()

# 连接 Redis
r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=DB_IN,
    decode_responses=True
)

queue_len = r.llen(QUEUE_IN)
print(f"📊 队列状态:")
print(f"  - 队列: {QUEUE_IN} (DB{DB_IN})")
print(f"  - 数据量: {queue_len}")
print()

if queue_len == 0:
    print("❌ 队列为空，无数据可清洗")
    sys.exit(1)

# 读取前几条数据进行检查
print("📝 检查前 3 条数据:")
print("-" * 80)

for idx in range(min(3, queue_len)):
    data_str = r.lindex(QUEUE_IN, idx)
    try:
        data = json.loads(data_str)
        print(f"\n数据 #{idx+1}:")
        print(f"  - ID: {data.get('id', '无')}")
        print(f"  - Source: {data.get('source', '无')}")
        print(f"  - Text 长度: {len(str(data.get('text', '')))} 字符")
        print(f"  - Title: {data.get('title', '无')[:50]}...")
        print(f"  - Timestamp 类型: {type(data.get('timestamp')).__name__}")
        print(f"  - Timestamp 值: {data.get('timestamp')}")
        
        # 验证
        has_source = 'source' in data and data['source']
        has_text = any(
            field in data and data[field]
            for field in ['text', 'content', 'title']
        )
        
        print(f"  ✓ 验证:")
        print(f"    - Source 有效: {has_source}")
        print(f"    - 文本有效: {has_text}")
        print(f"    - 通过验证: {has_source and has_text}")
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")

print()
print("=" * 80)
print("📌 诊断结果:")
print("=" * 80)
print("根据上面的检查结果：")
print("1. 如果 'Source 有效' 和 '文本有效' 都是 True")
print("   → 数据应该能通过验证，问题可能在其他地方")
print()
print("2. 如果 'Source 有效' 是 False")
print("   → 数据缺少或 source 字段为空")
print()
print("3. 如果 '文本有效' 是 False")
print("   → 数据缺少 text/content/title 或这些字段为空")
print()
print("=" * 80)
