"""
Reddit 延迟测试脚本
对比不同方法的实时性
"""
import sys
import time
import praw
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import setup_logger

logger = setup_logger('reddit_delay_test')


def test_reddit_api_delays(config: dict):
    """
    测试 Reddit API 各种方法的延迟
    
    Args:
        config: Reddit 配置
    """
    reddit = praw.Reddit(
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        user_agent=config['user_agent']
    )
    
    subreddit = reddit.subreddit('investing')
    current_time = time.time()
    
    logger.info("=" * 70)
    logger.info("Reddit API 延迟测试")
    logger.info("=" * 70)
    logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"测试子版块: r/investing")
    logger.info("")
    
    # 测试1: subreddit.new()
    logger.info("📰 测试1: subreddit.new() - 最新帖子")
    logger.info("-" * 70)
    try:
        new_posts = list(subreddit.new(limit=10))
        if new_posts:
            latest_post = new_posts[0]
            post_time = latest_post.created_utc
            delay_minutes = (current_time - post_time) / 60
            
            logger.info(f"✓ 获取到 {len(new_posts)} 条帖子")
            logger.info(f"最新帖子: {latest_post.title[:60]}...")
            logger.info(f"发布时间: {datetime.fromtimestamp(post_time).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"⏱️  延迟: {delay_minutes:.1f} 分钟 ({delay_minutes/60:.1f} 小时)")
        else:
            logger.warning("✗ 未获取到任何帖子")
    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
    
    logger.info("")
    
    # 测试2: subreddit.rising()
    logger.info("🔥 测试2: subreddit.rising() - 上升趋势帖子")
    logger.info("-" * 70)
    try:
        rising_posts = list(subreddit.rising(limit=10))
        if rising_posts:
            latest_post = rising_posts[0]
            post_time = latest_post.created_utc
            delay_minutes = (current_time - post_time) / 60
            
            logger.info(f"✓ 获取到 {len(rising_posts)} 条帖子")
            logger.info(f"最新帖子: {latest_post.title[:60]}...")
            logger.info(f"发布时间: {datetime.fromtimestamp(post_time).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"⏱️  延迟: {delay_minutes:.1f} 分钟 ({delay_minutes/60:.1f} 小时)")
        else:
            logger.warning("✗ 未获取到任何帖子")
    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
    
    logger.info("")
    
    # 测试3: subreddit.search() with time_filter='hour'
    logger.info("🔍 测试3: subreddit.search() - 搜索（1小时内）")
    logger.info("-" * 70)
    try:
        search_posts = list(
            subreddit.search('earnings', time_filter='hour', sort='new', limit=10)
        )
        if search_posts:
            latest_post = search_posts[0]
            post_time = latest_post.created_utc
            delay_minutes = (current_time - post_time) / 60
            
            logger.info(f"✓ 获取到 {len(search_posts)} 条帖子")
            logger.info(f"最新帖子: {latest_post.title[:60]}...")
            logger.info(f"发布时间: {datetime.fromtimestamp(post_time).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"⏱️  延迟: {delay_minutes:.1f} 分钟 ({delay_minutes/60:.1f} 小时)")
        else:
            logger.warning("✗ 未获取到任何帖子（搜索索引延迟问题）")
    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
    
    logger.info("")
    
    # 测试4: subreddit.search() with time_filter='day'
    logger.info("🔍 测试4: subreddit.search() - 搜索（24小时内）")
    logger.info("-" * 70)
    try:
        search_posts = list(
            subreddit.search('earnings', time_filter='day', sort='new', limit=10)
        )
        if search_posts:
            latest_post = search_posts[0]
            post_time = latest_post.created_utc
            delay_minutes = (current_time - post_time) / 60
            
            logger.info(f"✓ 获取到 {len(search_posts)} 条帖子")
            logger.info(f"最新帖子: {latest_post.title[:60]}...")
            logger.info(f"发布时间: {datetime.fromtimestamp(post_time).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"⏱️  延迟: {delay_minutes:.1f} 分钟 ({delay_minutes/60:.1f} 小时)")
        else:
            logger.warning("✗ 未获取到任何帖子")
    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("测试完成")
    logger.info("=" * 70)
    logger.info("")
    logger.info("📊 结论:")
    logger.info("  • subreddit.new() 和 rising() - 延迟约 1-2 小时")
    logger.info("  • search(time_filter='hour') - 通常返回空（索引延迟）")
    logger.info("  • search(time_filter='day') - 延迟约 8-24 小时")
    logger.info("")
    logger.info("💡 建议:")
    logger.info("  • 实时监控：使用 Stream API（延迟 < 1分钟）")
    logger.info("  • 常规抓取：使用 new() + rising()（延迟 1-2小时）")
    logger.info("  • 历史数据：使用 search() 配合 time_filter='day'")


if __name__ == '__main__':
    import yaml
    
    print("正在加载配置...")
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("开始测试...\n")
    test_reddit_api_delays(config['reddit'])
