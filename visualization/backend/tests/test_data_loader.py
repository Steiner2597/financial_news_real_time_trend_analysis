# backend/test_data_loader.py
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.data_loader import DataLoader

if __name__ == "__main__":
    loader = DataLoader()
    loader.load_mock_data_to_redis()
    loader.get_redis_info()
