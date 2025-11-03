# 快速参考 - 后端架构简化

## 已删除的文件
✅ `app/services/data_sync_service.py` - 已删除
✅ `app/services/redis_publisher.py` - 已删除

## 核心变更

### RedisClient (简化)
- ✅ 仅从 `processed_data:*` 读取数据
- ❌ 不再订阅 `processed_data_publisher`
- ❌ 不再同步数据

### Scheduler (简化)
- ❌ 不再生成 mock 数据
- ❌ 不再发布数据到 Redis
- ⚠️  默认已禁用（可选启用用于定时任务）

### Main (简化)
- ❌ 不再启动 DataSyncService
- ❌ 不再初始化 RedisPublisher
- ⚠️  Scheduler 已注释（可选启用）

## 数据来源

现在所有数据由**其他模块**直接写入 `processed_data:*`：
- ✅ 不需要发布-订阅
- ✅ 不需要数据同步
- ✅ 直接读取即可

## 快速测试

```bash
# 验证架构
cd visualization/backend
python verify_architecture.py

# 启动后端
python -m backend.app.main
```

## API 端点
所有 API 端点**保持不变**，前端无需修改：
- GET `/api/v1/trends/trending-keywords`
- GET `/api/v1/trends/history`
- GET `/api/v1/wordcloud`
- GET `/api/v1/news`
- WebSocket `/api/v1/ws/*`

## 注意
⚠️  确保其他模块（scraper/processor/cleaner）正在往 Redis 的 `processed_data:*` 写入数据！
