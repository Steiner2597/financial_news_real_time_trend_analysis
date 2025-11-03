# backend/app/routes/wordcloud.py
from fastapi import APIRouter
import logging
from datetime import datetime

from ..services.redis_client import RedisClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/wordcloud")
async def get_wordcloud_data():
    """获取词云数据的 HTTP 端点"""
    try:
        redis_client = RedisClient()
        word_cloud_data = redis_client.get_word_cloud()
        metadata = redis_client.get_metadata()

        return {
            "success": True,
            "data": word_cloud_data,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取词云数据失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "timestamp": datetime.now().isoformat()
        }


@router.get("/wordcloud/health")
async def wordcloud_health_check():
    """词云服务健康检查"""
    try:
        redis_client = RedisClient()
        word_cloud_data = redis_client.get_word_cloud()

        return {
            "status": "healthy",
            "data_available": len(word_cloud_data) > 0,
            "data_count": len(word_cloud_data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
