# backend/app/routes/new.py
from fastapi import APIRouter
import logging
from datetime import datetime
from ..services.redis_client import RedisClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/news")
async def get_news_feed():
    """获取新闻流数据"""
    try:
        redis_client = RedisClient()
        news_feed = redis_client.get_news_feed()
        metadata = redis_client.get_metadata()
        
        return {
            "success": True,
            "data": news_feed,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取新闻数据失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "timestamp": datetime.now().isoformat()
        }

@router.get("/news/health")
async def news_health_check():
    """新闻服务健康检查"""
    try:
        redis_client = RedisClient()
        news_feed = redis_client.get_news_feed()
        return {
            "success": True,
            "service": "news",
            "status": "healthy",
            "data_count": len(news_feed)
        }
    except Exception as e:
        logger.error(f"新闻服务健康检查失败: {e}")
        return {
            "success": False,
            "service": "news",
            "status": "unhealthy",
            "error": str(e)
        }
