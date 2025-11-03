# 后端架构简化总结

## 修改日期
2025-10-27

## 架构变更

### 原架构
- 使用发布-订阅模式
- 数据流：mock_data_generator → redis_publisher → processed_data_publisher:* → data_sync_service → processed_data:*
- 组件：RedisPublisher, DataSyncService, RedisClient(含订阅功能), Scheduler(生成mock数据)

### 新架构
- 直接读取模式
- 数据流：其他模块 → processed_data:* ← RedisClient(直接读取)
- 组件：RedisClient(仅读取功能), Scheduler(可选，不再生成数据)

## 已删除的文件

1. **`app/services/data_sync_service.py`**
   - 功能：订阅 processed_data_publisher 并同步数据到 processed_data
   - 删除原因：不再需要发布-订阅模式

2. **`app/services/redis_publisher.py`**
   - 功能：发布数据到 processed_data_publisher 命名空间并发送更新消息
   - 删除原因：其他模块直接写入 processed_data，不需要发布者

## 修改的文件

### 1. `app/services/redis_client.py`
**删除的功能：**
- `subscribe_to_updates()` - 订阅数据更新
- `unsubscribe()` - 取消订阅
- `sync_from_publisher()` - 从发布者同步数据
- `self.pubsub` - 发布订阅对象

**保留的功能：**
- `get_trend_data()` - 从 processed_data 获取完整数据
- `get_metadata()` - 获取元数据
- `get_trending_keywords()` - 获取热词数据
- `get_word_cloud()` - 获取词云数据
- `get_history_data()` - 获取历史数据
- `get_news_feed()` - 获取新闻数据
- `test_redis_connection()` - 测试连接
- `test_data_retrieval()` - 测试数据检索
- `check_redis_info()` - 检查Redis信息

**修改说明：**
- 简化为仅从 `processed_data:*` 命名空间读取数据
- 移除所有订阅相关功能

### 2. `app/main.py`
**删除的导入：**
- `from .services.data_sync_service import DataSyncService`

**删除的全局变量：**
- `sync_service`

**修改的函数：**

#### `signal_handler()`
- 移除 `sync_service.stop_sync_service()` 调用

#### `start_background_services()`
- 移除 Redis 发布者初始化
- 移除数据同步服务启动
- 注释掉 scheduler 启动（因为不再需要生成 mock 数据）
- 添加说明：数据由其他模块写入 processed_data

#### `stop_background_services()`
- 移除同步服务停止逻辑

#### `health_check()`
- 移除 Redis 发布者健康检查
- 移除同步服务状态检查

#### `system_status()`
- 简化 `data_flow` 信息，只显示 processed_data 命名空间
- 移除同步服务状态信息
- 移除发布者键统计，只显示 processed_data 键数量

### 3. `app/services/scheduler.py`
**删除的导入：**
- `from backend.app.services.mock_data_generator import MockDataGenerator`
- `from backend.app.services.redis_publisher import RedisPublisher`

**删除的功能：**
- `self.generator` - Mock 数据生成器
- `self.redis_publisher` - Redis 发布者
- `generate_and_push_data()` - 生成并推送数据

**新增的功能：**
- `check_data_status()` - 检查数据状态（示例方法）

**修改说明：**
- 转变为通用调度器，不再负责数据生成和推送
- 添加注释说明数据由其他模块写入
- `start()` 方法中注释掉定时任务（如需要可自行启用）
- `trigger_manual_update()` 改为调用 `check_data_status()`

## 可选删除的文件

以下文件不再被主程序使用，但保留用于测试或独立运行：

1. **`app/services/mock_data_generator.py`**
   - 仅被 `data_loader.py` 引用
   - 如果不需要 mock 数据可以删除

2. **`app/services/data_loader.py`**
   - 仅被测试文件引用
   - 用于独立加载测试数据
   - 如果不需要可以删除

3. **`tests/test_data_loader.py`**
   - 测试 data_loader 的测试文件
   - 如果删除了 data_loader.py 可以一并删除

## 当前数据流

```
其他模块 (scraper/processor/cleaner)
    ↓
    直接写入 Redis
    ↓
processed_data:metadata
processed_data:trending_keywords
processed_data:word_cloud
processed_data:news_feed
processed_data:history_data:*
    ↓
visualization 后端通过 RedisClient 读取
    ↓
API 端点返回给前端
```

## 主要命名空间

### processed_data:*
后端从此命名空间读取所有数据：
- `processed_data:metadata` - 元数据
- `processed_data:trending_keywords` - 热词列表
- `processed_data:word_cloud` - 词云数据
- `processed_data:news_feed` - 新闻列表
- `processed_data:history_data:{keyword}` - 关键词历史数据

## 启动说明

### 正常运行（依赖其他模块提供数据）
```bash
cd visualization/backend
python -m backend.app.main
```

后端会：
1. 连接 Redis
2. 等待其他模块写入 processed_data
3. 通过 API 提供数据访问

### 使用 Scheduler（可选）
如果需要定时任务，可以在 `main.py` 的 `start_background_services()` 中取消注释：
```python
print("⏰ 启动数据调度器...")
scheduler = get_scheduler()
scheduler.start(initial_push=True)
```

## 测试

### 测试 Redis 连接
```bash
cd visualization/backend
python -m backend.app.services.redis_client
```

### 健康检查
```bash
curl http://localhost:8000/health
```

### 系统状态
```bash
curl http://localhost:8000/system/status
```

## 注意事项

1. **数据依赖**：后端现在完全依赖其他模块往 `processed_data:*` 写入数据
2. **Scheduler**：默认关闭，如需定时任务可自行启用
3. **Mock 数据**：如需测试可使用 `data_loader.py` 独立脚本
4. **兼容性**：前端 API 接口保持不变，无需修改前端代码

## 相关配置

### config.py
确保 Redis 配置正确：
```python
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PASSWORD = None  # 根据实际情况设置
```
