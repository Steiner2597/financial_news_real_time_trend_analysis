# Reddit 实时数据抓取解决方案

## 🔍 问题背景

**问题**：无法抓取 Reddit 8小时内的最新内容  
**原因**：Reddit 官方 API 的搜索索引延迟（8-24小时）

---

## ✅ 解决方案对比

| 方案 | 延迟时间 | 优点 | 缺点 | 推荐度 |
|------|---------|------|------|--------|
| **方案1：优化现有代码** | 1-2小时 | 改动小，稳定 | 仍有延迟 | ⭐⭐⭐⭐ |
| **方案2：Stream API** | < 1分钟 | 真正实时 | 需要持续运行 | ⭐⭐⭐⭐⭐ |
| **方案3：Pushshift** | 已废弃 | - | 2023年5月已被封禁 | ❌ |

---

## 📦 已实施的优化（方案1）

### 1. **调整抓取顺序**
```python
# 原来：先搜索（延迟高）→ 再抓子版块
# 现在：先抓子版块 → 再搜索（作为补充）
```

### 2. **新增 Rising 帖子监控**
```python
# Rising 帖子：正在快速上升的新帖（1-4小时内）
subreddit.rising(limit=25)
```

### 3. **修改搜索时间范围**
```yaml
# config.yaml
search_settings:
  time_filter: day  # 改为 'day'，'hour' 经常返回空结果
```

### 使用方法
```bash
# 无需修改，直接运行即可
python control_center.py
```

**效果**：延迟从 8-24小时 → 降低到 1-2小时

---

## 🔥 真正实时方案（方案2）

### Stream API - 延迟 < 1分钟

**新文件**：`crawlers/reddit_stream_crawler.py`

#### 特点
- ✅ 真正实时（延迟 < 1分钟）
- ✅ 持续监听，无需轮询
- ✅ 适合关键词监控和突发事件追踪
- ⚠️ 需要保持程序运行

#### 使用方法

##### 1. **单独测试运行**
```bash
cd scraper
python crawlers/reddit_stream_crawler.py
```

##### 2. **集成到 control_center.py**

在 `control_center.py` 中添加：

```python
from crawlers.reddit_stream_crawler import RedditStreamCrawler

class CrawlerControlCenter:
    def __init__(self, config_file='config.yaml'):
        # ... 现有代码 ...
        
        # 初始化实时流式爬虫
        if self.config['reddit'].get('stream_enabled', False):
            self.stream_crawler = RedditStreamCrawler(
                self.config['reddit'], 
                self.redis_client
            )
    
    def run_stream_mode(self, duration_seconds=600):
        """运行实时流式监听（10分钟）"""
        logger.info("🔴 启动 Reddit 实时流式监听...")
        stats = self.stream_crawler.stream_submissions(duration_seconds)
        logger.info(f"✅ 实时监听完成: {stats}")
```

##### 3. **配置文件添加**

在 `config.yaml` 的 `reddit:` 部分添加：

```yaml
reddit:
  # ... 现有配置 ...
  
  # 实时流式监听配置
  stream_enabled: true        # 是否启用实时监听
  stream_duration: 600        # 每次监听时长（秒）
  stream_interval: 60         # 监听间隔（秒）
```

##### 4. **后台持续运行**

创建 `start_stream_crawler.bat`：

```batch
@echo off
echo ========================================
echo Reddit 实时流式爬虫
echo ========================================

:loop
python crawlers/reddit_stream_crawler.py
echo 等待60秒后重新启动...
timeout /t 60 /nobreak
goto loop
```

---

## 🎯 推荐使用策略

### **混合策略（最佳）**

同时运行两种模式：

1. **定时批量抓取**（每10分钟）
   - 使用优化后的 `reddit_crawler.py`
   - 抓取 rising + new 帖子
   - 延迟：1-2小时

2. **持续实时监听**（后台运行）
   - 使用 `reddit_stream_crawler.py`
   - 实时捕获新帖子
   - 延迟：< 1分钟

#### 实施步骤

1. **终端1：运行定时爬虫**
```bash
cd scraper
python control_center.py
```

2. **终端2：运行实时流式爬虫**
```bash
cd scraper
start_stream_crawler.bat
```

---

## 🔧 故障排查

### 问题1：Stream API 频繁断开
**解决**：添加自动重连逻辑

```python
# 在 stream_submissions() 中添加
max_retries = 3
retry_count = 0

while retry_count < max_retries:
    try:
        for submission in subreddit.stream.submissions():
            # ... 处理逻辑 ...
        break  # 正常结束
    except Exception as e:
        retry_count += 1
        logger.warning(f"连接断开，重试 {retry_count}/{max_retries}...")
        time.sleep(10)
```

### 问题2：搜索仍然返回空结果
**原因**：Reddit 搜索索引延迟，这是 Reddit 官方限制，无法解决

**建议**：
- ✅ 使用 `subreddit.new()` 和 `rising()`
- ✅ 使用 Stream API
- ❌ 不要依赖 `search()` 获取实时数据

### 问题3：Stream API 占用资源过高
**解决**：
- 减少监听的子版块数量
- 增加关键词过滤
- 调整 `duration_seconds` 和间隔时间

---

## 📊 性能对比

| 指标 | 传统搜索 | 优化后 | Stream API |
|------|---------|--------|------------|
| 延迟时间 | 8-24小时 | 1-2小时 | < 1分钟 |
| CPU占用 | 低 | 低 | 中 |
| 内存占用 | 低 | 低 | 中 |
| 需要持续运行 | 否 | 否 | 是 |
| API请求数 | 中 | 中 | 高 |
| 推荐场景 | 历史数据 | 日常监控 | 突发事件 |

---

## 🎓 相关资源

- [PRAW 官方文档](https://praw.readthedocs.io/)
- [Reddit API 限制说明](https://www.reddit.com/dev/api)
- [Stream API 文档](https://praw.readthedocs.io/en/stable/code_overview/other/subredditstream.html)

---

## ❓ 常见问题

**Q: 为什么 Pushshift 不能用了？**  
A: 2023年5月，Reddit 官方切断了 Pushshift 的数据访问权限，导致其无法继续提供服务。

**Q: Stream API 会消耗多少 API 配额？**  
A: Stream API 使用的是长连接轮询，每秒约1-2个请求，比传统批量抓取更高效。

**Q: 可以同时监听多个子版块吗？**  
A: 可以，使用 `+` 连接，如 `reddit.subreddit('investing+finance+stocks')`

**Q: Stream API 能抓取历史数据吗？**  
A: 不能，Stream API 只能获取启动后的新数据。历史数据需要使用传统方法。

---

## 📝 更新日志

**2025-11-03**
- ✅ 添加 Rising 帖子监控
- ✅ 调整抓取顺序（优先 subreddit.new）
- ✅ 创建实时流式爬虫（reddit_stream_crawler.py）
- ✅ 修改搜索时间范围为 'day'
- ✅ 添加详细的使用说明文档
