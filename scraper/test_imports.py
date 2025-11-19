"""测试导入是否正常"""
import sys
from pathlib import Path

# 添加 scraper 目录到路径
scraper_dir = Path(__file__).parent
sys.path.insert(0, str(scraper_dir))

print(f"Python 路径: {sys.path[:3]}")
print(f"Scraper 目录: {scraper_dir}")

try:
    from utils.logger import setup_logger
    from utils.redis_client import RedisClient
    print("✅ 导入成功!")
    print("✅ utils.logger 可用")
    print("✅ utils.redis_client 可用")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

print("\n现在测试 Reddit Stream Crawler...")
try:
    from crawlers.reddit_stream_crawler import RedditStreamCrawler
    print("✅ RedditStreamCrawler 导入成功!")
except ImportError as e:
    print(f"❌ RedditStreamCrawler 导入失败: {e}")
    sys.exit(1)

print("\n✨ 所有导入测试通过!")
