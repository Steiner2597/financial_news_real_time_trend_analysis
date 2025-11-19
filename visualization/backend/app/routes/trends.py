# backend/app/routes/trends.py
from fastapi import APIRouter
import logging
from datetime import datetime
from ..services.redis_client import RedisClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/trends/all")
async def get_all_trend_data():
    """获取所有趋势数据"""
    try:
        redis_client = RedisClient()
        trending_keywords = redis_client.get_trending_keywords()
        history_data = redis_client.get_history_data()
        metadata = redis_client.get_metadata()
        
        return {
            "success": True,
            "data": {
                "trending_keywords": trending_keywords,
                "history_data": history_data
            },
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取趋势数据失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {},
            "timestamp": datetime.now().isoformat()
        }

@router.get("/trends/keywords")
async def get_trending_keywords():
    """获取热词数据"""
    try:
        redis_client = RedisClient()
        trending_keywords = redis_client.get_trending_keywords()
        metadata = redis_client.get_metadata()
        
        return {
            "success": True,
            "data": trending_keywords,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取热词数据失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "timestamp": datetime.now().isoformat()
        }

@router.get("/trends/history")
async def get_history_data():
    """获取历史趋势数据"""
    try:
        redis_client = RedisClient()
        history_data = redis_client.get_history_data()
        metadata = redis_client.get_metadata()
        
        return {
            "success": True,
            "data": history_data,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取历史数据失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {},
            "timestamp": datetime.now().isoformat()
        }

@router.get("/trends/health")
async def trends_health_check():
    """趋势服务健康检查"""
    try:
        redis_client = RedisClient()
        trending_keywords = redis_client.get_trending_keywords()
        return {
            "success": True,
            "service": "trends",
            "status": "healthy",
            "data_count": len(trending_keywords)
        }
    except Exception as e:
        logger.error(f"趋势服务健康检查失败: {e}")
        return {
            "success": False,
            "service": "trends",
            "status": "unhealthy",
            "error": str(e)
        }
