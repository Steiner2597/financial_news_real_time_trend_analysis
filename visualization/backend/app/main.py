# backend/app/main.py
import time
import signal
import sys
import threading
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import trends, news, wordcloud, websocket_routes
from .services.redis_client import RedisClient
from .services.scheduler import get_scheduler

# 全局变量
scheduler = None
is_running = False


def signal_handler(signum, frame):
    """信号处理"""
    global is_running, scheduler

    print(f"\n🛑 接收到信号 {signum}，正在优雅关闭...")
    is_running = False

    # 停止服务
    if scheduler:
        scheduler.stop()

    print("👋 服务已关闭")
    sys.exit(0)


def start_background_services():
    """启动后台服务"""
    global scheduler, is_running

    print("=" * 60)
    print("🚀 启动金融趋势分析后台服务")
    print("=" * 60)

    try:
        # 1. 初始化Redis客户端测试
        print("🔧 初始化Redis连接...")
        redis_client = RedisClient()
        if not redis_client.test_redis_connection():
            raise Exception("Redis连接测试失败")

        # 2. 启动数据调度器（可选）
        # 注意：数据由其他模块直接写入processed_data命名空间
        # 调度器主要用于定时检查等任务，如不需要可以注释掉
        # print("⏰ 启动数据调度器...")
        # scheduler = get_scheduler()
        # scheduler.start(initial_push=True)

        # 3. 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        is_running = True
        print("✅ 所有后台服务启动完成!")
        print("📝 数据从其他模块写入processed_data命名空间")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ 后台服务启动失败: {e}")
        return False


def stop_background_services():
    """停止后台服务"""
    global scheduler, is_running

    print("\n🛑 正在停止后台服务...")
    is_running = False

    if scheduler:
        scheduler.stop()
        print("✅ 数据调度器已停止")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🎯 启动应用生命周期...")
    success = start_background_services()

    if not success:
        print("❌ 应用启动失败，退出...")
        sys.exit(1)

    yield  # 应用运行期间

    # 关闭时
    print("🎯 关闭应用生命周期...")
    stop_background_services()


# 创建FastAPI应用
app = FastAPI(
    title="金融趋势分析API",
    version="1.0.0",
    description="实时金融趋势分析和可视化API",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.ALLOWED_ORIGINS,
    allow_origins=["*"],  # 改为允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(trends.router, prefix="/api/v1", tags=["trends"])  # 注册趋势路由
app.include_router(news.router, prefix="/api/v1", tags=["news"])  # 注册新闻路由
app.include_router(wordcloud.router, prefix="/api/v1", tags=["wordcloud"])  # 注册词云路由
app.include_router(websocket_routes.router, prefix="/api/v1", tags=["websocket"])  # 注册WebSocket路由


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "金融趋势分析API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    global is_running, scheduler

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }

    # 检查Redis连接
    try:
        redis_client = RedisClient()
        redis_client.test_redis_connection()
        health_status["services"]["redis_client"] = "healthy"
    except Exception as e:
        health_status["services"]["redis_client"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # 检查调度器状态
    if scheduler:
        scheduler_status = scheduler.get_status()
        health_status["services"]["scheduler"] = scheduler_status
        if not scheduler_status["is_running"]:
            health_status["status"] = "degraded"
    else:
        health_status["services"]["scheduler"] = "unhealthy"
        health_status["status"] = "degraded"

    # WebSocket 服务状态（基础检查）
    health_status["services"]["websocket"] = "available"

    return health_status


@app.get("/system/status")
async def system_status():
    """系统状态信息"""
    global scheduler

    status_info = {
        "timestamp": datetime.now().isoformat(),
        "application": {
            "name": "金融趋势分析API",
            "version": "1.0.0",
            "status": "running"
        },
        "data_flow": {
            "namespace": "processed_data:*",
            "description": "直接从processed_data命名空间读取数据"
        },
        "websocket": {
            "status": "enabled",
            "endpoints": [
                "/api/v1/ws/wordcloud",
                "/api/v1/ws/trending",
                "/api/v1/ws/news",
                "/api/v1/ws/all"
            ]
        }
    }

    # 添加调度器信息
    if scheduler:
        scheduler_status = scheduler.get_status()
        status_info["scheduler"] = scheduler_status
    else:
        status_info["scheduler"] = {"status": "not_running"}

    # 添加Redis信息
    try:
        redis_client = RedisClient()
        redis_client.test_redis_connection()
        status_info["redis"] = {"status": "connected"}

        # 添加键数量信息
        processed_data_keys = redis_client.redis_client.keys("processed_data:*")
        status_info["redis"]["processed_data_keys"] = len(processed_data_keys)

    except Exception as e:
        status_info["redis"] = {"status": f"disconnected: {str(e)}"}

    return status_info


@app.post("/system/refresh")
async def manual_refresh():
    """手动触发数据刷新"""
    global scheduler

    if not scheduler:
        return {"status": "error", "message": "调度器未运行"}

    success = scheduler.trigger_manual_update()

    if success:
        return {"status": "success", "message": "数据刷新已触发"}
    else:
        return {"status": "error", "message": "数据刷新失败"}


# 独立运行模式
if __name__ == "__main__":
    import uvicorn

    print("🎯 独立运行模式启动...")

    # 启动后台服务
    if start_background_services():
        # 启动FastAPI服务器 - 修正模块路径
        uvicorn.run(
            "backend.app.main:app",  # 改为完整路径
            host="localhost",
            port=8000,
            reload=settings.DEBUG,
            log_level="info"
        )
    else:
        print("❌ 启动失败，退出程序")
        sys.exit(1)