"""
测试新闻和评论的去重逻辑
验证同一篇新闻下的多条评论不会被错误去重
"""
import json
import redis
import time
from datetime import datetime


def test_news_with_comments():
    """测试新闻和其评论能够正确区分"""
    
    print("=" * 70)
    print("测试场景：一篇新闻 + 多条评论")
    print("=" * 70)
    
    # 连接 Redis
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    queue_name = "financial_news_queue"
    
    # 清空测试队列
    r.delete(queue_name)
    
    # 1. 创建一篇新闻
    news = {
        "id": "news_12345",
        "title": "Tesla Stock Surges on Earnings Beat",
        "text": "Tesla Inc. reported better-than-expected earnings...",
        "source": "reuters",
        "url": "https://reuters.com/article/tesla-earnings",
        "created_at": datetime.now().isoformat(),
        "timestamp": int(time.time())
    }
    
    # 2. 创建该新闻的 3 条评论
    comments = [
        {
            "post_id": "news_12345",  # 父新闻 ID
            "comment_id": "comment_001",
            "text": "Great news for TSLA investors!",
            "author": "investor_joe",
            "source": "reddit",
            "created_at": datetime.now().isoformat(),
            "timestamp": int(time.time())
        },
        {
            "post_id": "news_12345",  # 同一父新闻 ID
            "comment_id": "comment_002",
            "text": "Time to buy more shares",
            "author": "trader_mike",
            "source": "reddit",
            "created_at": datetime.now().isoformat(),
            "timestamp": int(time.time())
        },
        {
            "post_id": "news_12345",  # 同一父新闻 ID
            "comment_id": "comment_003",
            "text": "Bearish sentiment continues despite earnings",
            "author": "bear_analyst",
            "source": "reddit",
            "created_at": datetime.now().isoformat(),
            "timestamp": int(time.time())
        }
    ]
    
    # 推送到 Redis
    print("\n📤 推送测试数据到 Redis...")
    r.lpush(queue_name, json.dumps(news, ensure_ascii=False))
    for comment in comments:
        r.lpush(queue_name, json.dumps(comment, ensure_ascii=False))
    
    print(f"✓ 已推送 1 篇新闻 + 3 条评论")
    print(f"✓ 队列长度: {r.llen(queue_name)}")
    
    # 显示预期结果
    print("\n" + "=" * 70)
    print("预期 ID 分配:")
    print("=" * 70)
    print(f"新闻: post_news_12345")
    print(f"评论1: comment_comment_001")
    print(f"评论2: comment_comment_002")
    print(f"评论3: comment_comment_003")
    
    print("\n" + "=" * 70)
    print("预期清洗结果:")
    print("=" * 70)
    print("✓ 清洗成功: 4 条（1篇新闻 + 3条评论）")
    print("✓ 去重过滤: 0 条（所有数据都应该保留）")
    print("✓ 无效数据: 0 条")
    
    print("\n" + "=" * 70)
    print("请运行 cleaner 来测试:")
    print("=" * 70)
    print("cd cleaner")
    print("python run_cleaner.py --mode once")
    print()


def test_duplicate_comments():
    """测试重复评论能够正确去重"""
    
    print("\n" + "=" * 70)
    print("测试场景：重复的评论")
    print("=" * 70)
    
    # 连接 Redis
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    queue_name = "financial_news_queue"
    
    # 清空测试队列
    r.delete(queue_name)
    
    # 创建 2 条相同的评论（相同 comment_id）
    comment1 = {
        "post_id": "news_99999",
        "comment_id": "comment_duplicate",
        "text": "This is a duplicate comment",
        "author": "test_user",
        "source": "reddit",
        "created_at": datetime.now().isoformat(),
        "timestamp": int(time.time())
    }
    
    comment2 = comment1.copy()  # 完全相同的评论
    
    # 推送到 Redis
    print("\n📤 推送测试数据到 Redis...")
    r.lpush(queue_name, json.dumps(comment1, ensure_ascii=False))
    r.lpush(queue_name, json.dumps(comment2, ensure_ascii=False))
    
    print(f"✓ 已推送 2 条相同评论（相同 comment_id）")
    print(f"✓ 队列长度: {r.llen(queue_name)}")
    
    print("\n" + "=" * 70)
    print("预期清洗结果:")
    print("=" * 70)
    print("✓ 清洗成功: 1 条（第一条评论）")
    print("✓ 去重过滤: 1 条（第二条重复评论）")
    print("✓ 无效数据: 0 条")
    
    print("\n" + "=" * 70)
    print("请运行 cleaner 来测试:")
    print("=" * 70)
    print("cd cleaner")
    print("python run_cleaner.py --mode once")
    print()


def test_mixed_data():
    """测试混合数据（新闻 + 评论 + 重复）"""
    
    print("\n" + "=" * 70)
    print("测试场景：混合数据（新闻 + 评论 + 重复）")
    print("=" * 70)
    
    # 连接 Redis
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    queue_name = "financial_news_queue"
    
    # 清空测试队列
    r.delete(queue_name)
    
    # 创建测试数据
    data = []
    
    # 2 篇新闻
    for i in range(1, 3):
        news = {
            "id": f"news_{i}",
            "title": f"Market News #{i}",
            "text": f"This is news article {i}",
            "source": "reuters",
            "url": f"https://reuters.com/article/{i}",
            "created_at": datetime.now().isoformat(),
            "timestamp": int(time.time())
        }
        data.append(news)
    
    # 每篇新闻 2 条评论
    for news_id in range(1, 3):
        for comment_id in range(1, 3):
            comment = {
                "post_id": f"news_{news_id}",
                "comment_id": f"comment_{news_id}_{comment_id}",
                "text": f"Comment {comment_id} on news {news_id}",
                "author": f"user_{comment_id}",
                "source": "reddit",
                "created_at": datetime.now().isoformat(),
                "timestamp": int(time.time())
            }
            data.append(comment)
    
    # 1 条重复新闻
    duplicate_news = {
        "id": "news_1",  # 与第一篇新闻相同 ID
        "title": "Market News #1 (Duplicate)",
        "text": "This is a duplicate of news 1",
        "source": "reuters",
        "url": "https://reuters.com/article/1",
        "created_at": datetime.now().isoformat(),
        "timestamp": int(time.time())
    }
    data.append(duplicate_news)
    
    # 1 条重复评论
    duplicate_comment = {
        "post_id": "news_1",
        "comment_id": "comment_1_1",  # 与之前的评论相同 ID
        "text": "Duplicate comment",
        "author": "user_1",
        "source": "reddit",
        "created_at": datetime.now().isoformat(),
        "timestamp": int(time.time())
    }
    data.append(duplicate_comment)
    
    # 推送到 Redis
    print("\n📤 推送测试数据到 Redis...")
    for item in data:
        r.lpush(queue_name, json.dumps(item, ensure_ascii=False))
    
    print(f"✓ 已推送:")
    print(f"  - 2 篇新闻")
    print(f"  - 4 条评论 (每篇新闻2条)")
    print(f"  - 1 条重复新闻")
    print(f"  - 1 条重复评论")
    print(f"✓ 队列长度: {r.llen(queue_name)}")
    
    print("\n" + "=" * 70)
    print("预期清洗结果:")
    print("=" * 70)
    print("✓ 清洗成功: 6 条（2篇新闻 + 4条评论）")
    print("✓ 去重过滤: 2 条（1条重复新闻 + 1条重复评论）")
    print("✓ 无效数据: 0 条")
    
    print("\n" + "=" * 70)
    print("请运行 cleaner 来测试:")
    print("=" * 70)
    print("cd cleaner")
    print("python run_cleaner.py --mode once")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='测试新闻和评论的去重逻辑')
    parser.add_argument(
        '--test',
        choices=['basic', 'duplicate', 'mixed', 'all'],
        default='all',
        help='选择测试场景'
    )
    args = parser.parse_args()
    
    if args.test in ['basic', 'all']:
        test_news_with_comments()
    
    if args.test in ['duplicate', 'all']:
        test_duplicate_comments()
    
    if args.test in ['mixed', 'all']:
        test_mixed_data()
    
    print("\n" + "=" * 70)
    print("测试数据生成完成！")
    print("=" * 70)
