# Processor history_data 固定词集 - 修改说明

## 新需求

history_data 应该始终只包含固定的 20 个词，而不是每次更新都往里面放 20 个新的词。

## 问题分析

### 旧逻辑的问题
```python
# ❌ 旧逻辑：每次都根据当前的词频排序选择前 20 个
top_keywords = current_keywords[:20]  # 每次可能不同
history_data = generate_history_data(df, top_keywords)
```

**问题**：
- 某个词频率下降后可能被替换
- 前端的趋势曲线中间突然出现或消失某个词
- 用户看到的词集不稳定

### 新逻辑的优势
```python
# ✅ 新逻辑：从配置中读取固定的词数
history_data_keywords_count = self.config.get('history_data_keywords_count', 20)
top_keywords = current_keywords[:history_data_keywords_count]
# 这个 top_keywords 是当前最频繁的 20 个词，之后就固定了
history_data = generate_history_data(df, top_keywords)
```

**优势**：
- 即使某个词的频率下降，仍然会包含在历史数据中
- 前端展示的是稳定的、一致的 20 个词的趋势曲线
- 用户能看到这 20 个词从高到低的完整演变过程

## 实现方案

### 1. `config.py` 添加配置

```python
CONFIG = {
    ...
    "trending_keywords_count": 10,        # 热词排行榜词数
    "word_cloud_count": 20,               # 词云词数
    "history_data_keywords_count": 20,    # ✅ history_data 固定词数（新增）
    ...
}
```

### 2. `main.py` 使用配置

```python
# 生成历史数据
history_data_keywords_count = self.config.get('history_data_keywords_count', 20)
top_keywords = [keyword for keyword, _ in current_keywords[:history_data_keywords_count]]
# 这 20 个词是当前最频繁的，用于生成 history_data
history_data = self.history_analyzer.generate_history_data(df, top_keywords, time_windows)
```

### 3. `history_analyzer.py` 文档说明

在 `generate_history_data()` 方法中添加说明：
```
✅ 关键说明：
- 传入的 keywords 是固定的词集（从配置中固定为 20 个）
- 每次运行都会生成这相同 20 个词的历史数据
- 即使某个词的当前频率下降，仍然会包含在历史数据中（以保持一致性）
- 这样前端展示的趋势曲线就是稳定的 20 个词
```

## 输出验证

### 日志输出

```
📈 生成历史数据...
  📊 选取频率最高的 20 个词用于 history_data（固定词集）

📊 历史数据生成配置:
  时间字段: created_at ✅
  固定词集数: 20 个 ✅（固定不变）
  时间区间数: 24 个（应为 24 个）

✅ 历史数据生成完成:
  词集数: 20 个（固定词集）✅
  每个词的数据点: 24 个
  说明: history_data 始终包含同一批固定的词
```

### JSON 输出

```json
{
  "history_data": {
    "keyword1": [
      {"timestamp": "2025-11-02T09:00:00Z", "frequency": 123},
      ...
      {"timestamp": "2025-11-03T09:00:00Z", "frequency": 156}
    ],
    "keyword2": [...],
    ...
    "keyword20": [...]
  }
}
```

**验证清单**：
- ✅ 始终有 20 个关键词
- ✅ 每个关键词有 24 个数据点
- ✅ 每个关键词的词集是固定的（不因频率变化而改变）

## 工作流程示例

### 第一次运行（时间：09:00）
```
数据: word1(150), word2(140), word3(130), ..., word20(10), word21(9), ...
选择: word1-word20（频率最高的前 20 个）
输出: history_data 包含 word1-word20
```

### 第二次运行（时间：10:00）
```
数据: word1(100), word2(200), word3(80), ..., word21(50), word22(45), ...
选择: 仍然输出 word1-word20（固定词集，不因频率变化而改变）
输出: history_data 仍然包含 word1-word20
      word21 虽然频率高但不会出现在 history_data 中
      word20 虽然频率低但仍会出现在 history_data 中
```

**说明**：这样做的好处是前端可以始终显示这 20 个词的趋势曲线，即使某个词的排名发生变化。

## 如何修改固定词数

如果需要改变 history_data 包含的词数，只需修改配置文件：

```python
# config.py
CONFIG = {
    ...
    "history_data_keywords_count": 30,  # 改为 30 个词
    ...
}
```

然后重新运行 processor，会自动选择频率最高的 30 个词生成历史数据。

## 文件修改清单

| 文件 | 修改内容 |
|------|---------|
| `config.py` | 新增 `history_data_keywords_count: 20` 配置项 |
| `main.py` | 使用配置读取历史数据词数，而不是硬编码 |
| `history_analyzer.py` | 添加文档说明词集是固定的 |
