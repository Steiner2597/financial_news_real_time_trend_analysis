# backend/test_redis.py
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.redis_client import RedisClient, run_redis_test

if __name__ == "__main__":
    run_redis_test()