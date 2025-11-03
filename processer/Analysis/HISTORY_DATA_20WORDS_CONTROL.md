# history_data 数量控制 - 修改说明

## 问题描述
- 每次 Processor 运行时，生成新的 20 个词频最高的数据
- 但旧数据仍然留在 Redis 中，导致 `history_data` 中的词数越来越多

## 解决方案
在 `redis_manager.py` 中的 `publish_processed_data()` 方法中：

### ✅ 新逻辑
1. **清理旧数据**：删除 Redis 中所有现存的 `processed_data:history_data:*` 键
2. **发布新数据**：发布当前 20 个词频最高的历史数据

## 代码改动

### `redis_manager.py` - `publish_processed_data()` 方法

```python
# 5. 发布历史数据
history_data = processed_data.get('history_data', {})

# ✅ 先删除所有旧的 history_data 键
old_history_keys = self.r.keys(f"{self.output_prefix}:history_data:*")
if old_history_keys:
    print(f"  🗑️  清理旧历史数据键: {len(old_history_keys)} 个")
    for old_key in old_history_keys:
        self.r.delete(old_key)

# 然后发布新的历史数据（只有当前的 20 个词）
for keyword, data in history_data.items():
    history_key = f"{self.output_prefix}:history_data:{keyword}"
    self.r.set(history_key, json.dumps(data, ensure_ascii=False))
    self.r.expire(history_key, self.key_ttl)

print(f"  ✓ {len(history_data)} 条历史数据（保持为 20 个）")
```

## 行为变化

### ❌ 之前的行为
```
第 1 次运行：Redis 中有 20 个 history_data
第 2 次运行：Redis 中有 40 个 history_data（新的 20 个 + 旧的 20 个）
第 3 次运行：Redis 中有 60 个 history_data（新的 20 个 + 旧的 40 个）
...
```

### ✅ 现在的行为
```
第 1 次运行：
  发布新数据 → Redis 中有 20 个 history_data

第 2 次运行：
  清理旧数据 → 删除之前的 20 个
  发布新数据 → Redis 中有 20 个 history_data（可能是不同的词）

第 3 次运行：
  清理旧数据 → 删除之前的 20 个
  发布新数据 → Redis 中有 20 个 history_data（可能是不同的词）

每次运行后，Redis 中的 history_data 始终保持 20 个关键词
```

## 输出日志示例

```
📤 发布到 Redis...
  ✓ processed_data:metadata
  ✓ processed_data:trending_keywords
  ✓ processed_data:word_cloud
  ✓ processed_data:news_feed
  🗑️  清理旧历史数据键: 18 个
  ✓ 20 条历史数据（保持为 20 个）
  ✓ 发布更新通知到 processed_data_updates
✅ 数据已成功发布到 Redis
```

## 前端行为

前端会自动从 Redis 获取当前的所有 `processed_data:history_data:*` 键，所以：
- ✅ TrendChart 中显示的关键词始终是 20 个
- ✅ 曲线图会根据最新的 20 个词自动更新
- ✅ 如果某个词从前 20 掉出来，该词的曲线会消失

## 验证方法

### 方法 1：检查 Redis
```bash
# 连接 Redis
redis-cli -n 2

# 查看 history_data 键数量
KEYS processed_data:history_data:* | wc -l

# 应该始终显示 20 个键
```

### 方法 2：查看日志
```
运行 main.py，查看是否有这两行：
  🗑️  清理旧历史数据键: X 个
  ✓ 20 条历史数据（保持为 20 个）
```

### 方法 3：检查输出 JSON
```bash
# 检查输出的 output_data.json
cat output_data.json | grep -A 1 '"history_data"' | head -5

# 应该看到 20 个关键词
```

## 修改文件

| 文件 | 修改内容 |
|------|---------|
| `processer/Analysis/redis_manager.py` | 修改 `publish_processed_data()` - 清理旧 history_data 键，只保留新的 20 个词 |

## 关键改动点

✅ **每次更新前清理**：删除 Redis 中所有旧的 `history_data:*` 键
✅ **发布新数据**：只发布当前词频最高的 20 个词
✅ **保持数量不变**：Redis 中的 history_data 始终只有 20 个关键词
✅ **自动选择**：每次运行时根据最新数据重新选择前 20 的词
