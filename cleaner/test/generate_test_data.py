"""
生成测试数据脚本
为 Cleaner 生成 100 条测试数据到 Redis DB0
"""
import redis
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
import yaml

# 加载配置（配置文件在上一层目录）
config_path = Path(__file__).parent.parent / "config_processing.yaml"
with open(config_path, 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

REDIS_HOST = CONFIG['redis']['host']
REDIS_PORT = CONFIG['redis']['port']
DB_IN = CONFIG['redis']['db_in']
QUEUE_IN = CONFIG['redis']['queue_in']

# 测试数据模板
SOURCES = ["alphavantage", "newsapi", "reddit", "stocktwits", "twitter", "rss"]
SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD", "INTC", "CRM"]
DOMAINS = [
    "www.benzinga.com",
    "www.cnbc.com", 
    "www.reuters.com",
    "www.bloomberg.com",
    "finance.yahoo.com",
    "seekingalpha.com",
    "reddit.com",
    "twitter.com"
]

TITLES = [
    "Bulls And Bears: Microsoft, Joby Aviation, Meta - And Nvidia Tops $5 Trillion",
    "Stock Market Surge: Tech Giants Lead Rally",
    "Fed Rate Decision Impact on Market Volatility",
    "Earnings Report: Apple Beats Expectations",
    "Crypto Market Rebounds After Correction",
    "Market Correction Signals Economic Uncertainty",
    "Tech IPO Boom Continues in Q4",
    "Oil Prices Hit New High Amid Geopolitical Tensions",
    "Real Estate Market Shows Signs of Recovery",
    "Inflation Data Triggers Market Reaction",
    "Dividend Announcement Boosts Stock Price",
    "Merger Deal Between Two Tech Giants",
    "Bitcoin Surge Past $100K Milestone",
    "Healthcare Stock Rally on New Drug Approval",
    "Financial Sector Outperforms Market Average",
]

SUMMARIES = [
    "Wall Street extended its record-setting rally as Nvidia Corp. ( NASDAQ:NVDA ) crossed the $5 trillion market-cap milestone - a first in history.",
    "Market analysts predict continued gains in technology sector over the coming quarter.",
    "Federal Reserve signals potential interest rate cuts in 2024.",
    "Major corporation reports better-than-expected quarterly earnings.",
    "Cryptocurrency market shows signs of recovery after recent downturn.",
    "Economic indicators suggest slower growth ahead for the economy.",
    "New product launch drives consumer enthusiasm for major retailer.",
    "Supply chain improvements lead to higher profit margins.",
    "Market volatility expected as earnings season concludes.",
    "International trade developments impact commodity prices.",
    "Tech startups attract record venture capital investments.",
    "Banking sector shows resilience amid economic headwinds.",
    "Real estate market benefits from lower mortgage rates.",
    "Energy sector transforms with renewable energy investments.",
    "Retail sales data indicates strong consumer spending.",
]

TEXT_SAMPLES = [
    "Bulls And Bears: Microsoft, Joby Aviation, Meta - And Nvidia Tops $5 Trillion - Apple ( NASDAQ:AAPL ), Amazon.com ( NASDAQ:AMZN ). Benzinga examined the prospects for many investors' favorite stocks over the last week - here's a look at some of our top stories. Wall Street extended its record-setting rally as Nvidia Corp. ( NASDAQ:NVDA ) crossed the $5 trillion market-cap milestone - a first in history.",
    "The stock market continues to show strength as major indices reach new all-time highs. Investors remain optimistic about corporate earnings and economic growth prospects. Technology stocks lead the gains with strong performance from cloud computing and artificial intelligence companies.",
    "Financial markets respond positively to recent economic data showing resilience in consumer spending and business investment. Market analysts maintain their bullish outlook for the remainder of the year despite some lingering concerns about inflation.",
    "Trading volumes remain elevated as institutional investors continue to rotate into growth stocks. The semiconductor sector shows particular strength driven by increased demand for AI chips and computing infrastructure upgrades.",
    "Market sentiment improves on dovish Fed commentary suggesting patience with interest rate policy. Bond markets rally on expectations of potential rate cuts in the coming year, supporting equity valuations.",
]

URLS = [
    "https://www.benzinga.com/markets/market-summary/25/11/48578014/benzinga-bulls-and-bears-microsoft-joby-aviation-meta-and-nvidia-tops-5-trillion",
    "https://www.cnbc.com/markets/stocks/",
    "https://www.reuters.com/finance/",
    "https://finance.yahoo.com/",
    "https://seekingalpha.com/market-news/",
    "https://reddit.com/r/stocks/",
    "https://www.bloomberg.com/quote/",
]

AUTHORS = [
    "Benzinga Senior Editor",
    "Financial Times Reporter",
    "Reuters Market Correspondent",
    "Bloomberg Analyst",
    "MarketWatch Columnist",
    "Seeking Alpha Contributor",
    "CNBC Producer",
    "Financial News Desk",
]

def generate_test_data(count: int = 500) -> list:
    """
    生成全面的测试数据，包含：
    - 重复数据（测试去重功能）
    - 缺少必要字段的数据（测试验证功能）
    - 超过24小时的数据（测试时间窗口清理）
    - 正常数据
    
    Args:
        count: 生成的数据条数
        
    Returns:
        测试数据列表
    """
    test_data = []
    
    # 时间戳范围
    now = time.time()
    week_ago = now - (7 * 24 * 3600)  # 7天前
    hours_25_ago = now - (25 * 3600)  # 25小时前（超过24小时）
    hours_1_ago = now - (1 * 3600)    # 1小时前（在24小时内）
    
    print(f"📊 开始生成 {count} 条全面测试数据...")
    print(f"  - 时间范围: {datetime.fromtimestamp(week_ago)} ~ {datetime.fromtimestamp(now)}")
    print(f"  - 24小时分界线: {datetime.fromtimestamp(hours_25_ago)}")
    
    # 数据分布计划
    normal_count = int(count * 0.60)      # 60% 正常数据
    duplicate_count = int(count * 0.15)   # 15% 重复数据
    invalid_count = int(count * 0.10)     # 10% 无效数据（缺少必要字段）
    old_count = int(count * 0.15)         # 15% 超过24小时的数据
    
    print(f"  - 正常数据: {normal_count} 条")
    print(f"  - 重复数据: {duplicate_count} 条")
    print(f"  - 无效数据: {invalid_count} 条")
    print(f"  - 超时数据: {old_count} 条")
    print()
    
    # 1. 生成正常数据
    print("🔧 生成正常数据...")
    for i in range(normal_count):
        timestamp = random.uniform(hours_1_ago, now)  # 最近1小时
        dt = datetime.fromtimestamp(timestamp)
        
        data = {
            "id": f"normal_{i+1:05d}",
            "text": random.choice(TEXT_SAMPLES),
            "source": random.choice(SOURCES),
            "timestamp": int(timestamp),
            "url": f"{random.choice(URLS)}?id=normal_{i+1}",
            "symbol": random.choice(SYMBOLS),
            "title": f"{random.choice(TITLES)} #normal_{i+1}",
            "summary": random.choice(SUMMARIES),
            "source_domain": random.choice(DOMAINS),
            "authors": random.choice(AUTHORS),
            "published_at": dt.strftime("%Y%m%dT%H%M%S"),
            "score": random.randint(0, 1000),
            "comments": random.randint(0, 500),
            "created_at": dt.isoformat() + "Z",
            "tags": random.sample(["tech", "market", "stocks", "crypto", "finance"], k=random.randint(1, 3)),
        }
        
        # 随机添加字段变化
        if random.random() < 0.3:
            data["sentiment"] = random.choice(["Bullish", "Bearish", "Neutral"])
        if random.random() < 0.3:
            data["content"] = data["text"]
        if random.random() < 0.2:
            data["post_id"] = data["id"]
        if random.random() < 0.2:
            data["tweet_id"] = data["id"]
        
        test_data.append(data)
    
    # 2. 生成重复数据（基于前面的正常数据）
    print("🔄 生成重复数据...")
    base_data_for_dups = test_data[:min(20, normal_count)]  # 用前20条作为重复的基础
    
    for i in range(duplicate_count):
        # 选择一个基础数据进行"重复"
        base_data = random.choice(base_data_for_dups).copy()
        
        # 修改一些不影响去重判断的字段
        base_data["timestamp"] = int(random.uniform(hours_1_ago, now))
        base_data["score"] = random.randint(0, 1000)
        base_data["comments"] = random.randint(0, 500)
        
        # 重复类型：
        if i % 3 == 0:
            # 完全相同的ID
            pass  # 保持原ID不变
        elif i % 3 == 1:
            # 相同的title+source组合（会生成相同的哈希）
            base_data.pop("id", None)  # 删除ID，让系统用title+source生成哈希
        else:
            # 相同的URL
            base_data["id"] = f"dup_{i+1:05d}_different_id"  # 不同ID
            # 但保持相同的 title 和 source，会生成相同哈希
        
        test_data.append(base_data)
    
    # 3. 生成无效数据（缺少必要字段）
    print("❌ 生成无效数据...")
    for i in range(invalid_count):
        timestamp = random.uniform(hours_1_ago, now)
        dt = datetime.fromtimestamp(timestamp)
        
        # 随机缺少必要字段
        data = {
            "id": f"invalid_{i+1:05d}",
            "timestamp": int(timestamp),
            "url": f"{random.choice(URLS)}?id=invalid_{i+1}",
            "published_at": dt.strftime("%Y%m%dT%H%M%S"),
        }
        
        invalid_type = i % 4
        if invalid_type == 0:
            # 缺少 source 字段
            data["text"] = random.choice(TEXT_SAMPLES)
            data["title"] = f"No Source Data #{i+1}"
        elif invalid_type == 1:
            # 缺少所有文本字段（text, content, title）
            data["source"] = random.choice(SOURCES)
        elif invalid_type == 2:
            # source 为空
            data["source"] = ""
            data["text"] = random.choice(TEXT_SAMPLES)
        else:
            # 文本字段为空
            data["source"] = random.choice(SOURCES)
            data["text"] = ""
            data["content"] = ""
            data["title"] = ""
        
        test_data.append(data)
    
    # 4. 生成超过24小时的旧数据
    print("⏰ 生成超过24小时的旧数据...")
    for i in range(old_count):
        # 生成25小时到7天前的时间戳
        timestamp = random.uniform(week_ago, hours_25_ago)
        dt = datetime.fromtimestamp(timestamp)
        
        data = {
            "id": f"old_{i+1:05d}",
            "text": f"这是超过24小时的旧数据 #{i+1}: {random.choice(TEXT_SAMPLES)}",
            "source": random.choice(SOURCES),
            "timestamp": int(timestamp),
            "url": f"{random.choice(URLS)}?id=old_{i+1}",
            "symbol": random.choice(SYMBOLS),
            "title": f"[旧数据] {random.choice(TITLES)} #old_{i+1}",
            "summary": f"[{dt.strftime('%Y-%m-%d %H:%M')}] {random.choice(SUMMARIES)}",
            "source_domain": random.choice(DOMAINS),
            "authors": random.choice(AUTHORS),
            "published_at": dt.strftime("%Y%m%dT%H%M%S"),
            "score": random.randint(0, 1000),
            "comments": random.randint(0, 500),
            "created_at": dt.isoformat() + "Z",
            "tags": ["old_data", "test"] + random.sample(["tech", "market", "stocks"], k=random.randint(0, 2)),
        }
        
        test_data.append(data)
    
    # 5. 补齐到指定数量（如果有缺少的）
    remaining = count - len(test_data)
    if remaining > 0:
        print(f"🔧 补齐剩余 {remaining} 条数据...")
        for i in range(remaining):
            timestamp = random.uniform(hours_1_ago, now)
            dt = datetime.fromtimestamp(timestamp)
            
            data = {
                "id": f"extra_{i+1:05d}",
                "text": random.choice(TEXT_SAMPLES),
                "source": random.choice(SOURCES),
                "timestamp": int(timestamp),
                "url": f"{random.choice(URLS)}?id=extra_{i+1}",
                "title": f"Extra Data #{i+1}",
                "created_at": dt.isoformat() + "Z",
            }
            test_data.append(data)
    
    # 打乱顺序
    random.shuffle(test_data)
    
    print(f"✅ 生成完成！总共 {len(test_data)} 条数据")
    print()
    
    return test_data

def push_to_redis(test_data: list) -> dict:
    """
    推送测试数据到 Redis
    
    Args:
        test_data: 测试数据列表
        
    Returns:
        推送结果统计
    """
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=DB_IN,
            decode_responses=True
        )
        
        stats = {
            'total': len(test_data),
            'pushed': 0,
            'failed': 0,
            'errors': []
        }
        
        # 清空现有队列（可选）
        old_count = r.llen(QUEUE_IN)
        if old_count > 0:
            r.delete(QUEUE_IN)
            print(f"✓ 清空旧数据: {old_count} 条")
        
        # 推送新数据
        for idx, data in enumerate(test_data, 1):
            try:
                json_str = json.dumps(data, ensure_ascii=False)
                r.rpush(QUEUE_IN, json_str)
                stats['pushed'] += 1
                
                if idx % 20 == 0:
                    print(f"  已推送: {idx}/{len(test_data)}")
                    
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append(f"数据 #{idx}: {str(e)}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return None

def send_crawler_complete_notification() -> bool:
    """
    发送爬虫完成通知给 Cleaner
    模拟 Scraper 的通知消息
    
    Returns:
        是否发送成功
    """
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=DB_IN,
            decode_responses=True
        )
        
        # 获取队列长度
        queue_length = r.llen(QUEUE_IN)
        
        # 构造通知消息（与 Scraper 的消息格式一致）
        notification = {
            "message": "crawler_complete",
            "timestamp": int(time.time()),
            "statistics": {
                "total_items": queue_length,
                "timestamp": int(time.time())
            }
        }
        
        # 发布通知到 crawler_complete 频道
        channel = "crawler_complete"
        result = r.publish(channel, json.dumps(notification, ensure_ascii=False))
        
        return result > 0
        
    except Exception as e:
        print(f"❌ 发送通知失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 80)
    print("🔧 Cleaner 全面测试数据生成工具")
    print("=" * 80)
    print("本工具将生成包含以下类型的测试数据:")
    print("✓ 60% 正常数据（有效且在24小时内）")
    print("✓ 15% 重复数据（测试去重功能）")
    print("✓ 10% 无效数据（缺少必要字段）")
    print("✓ 15% 超时数据（超过24小时，测试清理功能）")
    print()
    
    # 1. 生成测试数据
    print("📊 生成测试数据...")
    print("-" * 80)
    test_data = generate_test_data(count=500)  # 生成500条数据
    
    # 统计数据类型（安全地检查ID字段）
    normal_data = [d for d in test_data if d.get('id', '').startswith('normal_')]
    duplicate_data = [d for d in test_data if 'dup_' in d.get('id', '') or 
                     any(base_d for base_d in normal_data[:20] 
                         if (d.get('id') == base_d.get('id') and d != base_d) or
                            (d.get('title') == base_d.get('title') and 
                             d.get('source') == base_d.get('source') and d != base_d))]
    invalid_data = [d for d in test_data if d.get('id', '').startswith('invalid_')]
    old_data = [d for d in test_data if d.get('id', '').startswith('old_')]
    
    print(f"✅ 数据生成完成！")
    print(f"  - 总数: {len(test_data)} 条")
    print(f"  - 正常数据: {len(normal_data)} 条")
    print(f"  - 重复数据: {len(duplicate_data)} 条")
    print(f"  - 无效数据: {len(invalid_data)} 条") 
    print(f"  - 超时数据: {len(old_data)} 条")
    print()
    
    # 显示数据样本
    print("📝 数据样本:")
    print("-" * 80)
    
    # 显示正常数据样本
    if normal_data:
        print("🟢 正常数据样本:")
        sample = normal_data[0]
        print(f"  ID: {sample.get('id', 'N/A')}")
        print(f"  Source: {sample.get('source', 'N/A')}")
        print(f"  Title: {sample.get('title', 'N/A')[:50]}...")
        print(f"  Text: {sample.get('text', 'N/A')[:50]}...")
        print(f"  Timestamp: {sample.get('timestamp', 'N/A')} ({datetime.fromtimestamp(sample['timestamp']) if sample.get('timestamp') else 'N/A'})")
        print()
    
    # 显示无效数据样本
    if invalid_data:
        print("🔴 无效数据样本:")
        sample = invalid_data[0]
        print(f"  ID: {sample.get('id', '❌ 缺失')}")
        print(f"  Source: {sample.get('source', '❌ 缺失')}")
        text_value = sample.get('text', '❌ 缺失')
        print(f"  Text: {text_value[:30] if text_value != '❌ 缺失' else text_value}...")
        title_value = sample.get('title', '❌ 缺失')
        print(f"  Title: {title_value[:30] if title_value != '❌ 缺失' else title_value}...")
        print()
    
    # 显示超时数据样本
    if old_data:
        print("🕐 超时数据样本:")
        sample = old_data[0]
        timestamp = sample.get('timestamp')
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            hours_ago = (time.time() - timestamp) / 3600
            print(f"  ID: {sample.get('id', 'N/A')}")
            print(f"  Source: {sample.get('source', 'N/A')}")
            print(f"  Title: {sample.get('title', 'N/A')[:50]}...")
            print(f"  时间: {dt} ({hours_ago:.1f} 小时前)")
        else:
            print(f"  ID: {sample.get('id', 'N/A')}")
            print(f"  ❌ 缺少时间戳")
        print()
    
    # 2. 推送到 Redis
    print("📤 推送到 Redis...")
    print("-" * 80)
    print(f"连接: {REDIS_HOST}:{REDIS_PORT} (DB{DB_IN})")
    print(f"队列: {QUEUE_IN}")
    print()
    
    stats = push_to_redis(test_data)
    
    if stats:
        print(f"✅ 推送完成!")
        print(f"  - 总数: {stats['total']}")
        print(f"  - 成功: {stats['pushed']}")
        print(f"  - 失败: {stats['failed']}")
        
        if stats['errors']:
            print(f"  - 错误信息:")
            for error in stats['errors'][:5]:
                print(f"    • {error}")
    print()
    
    # 3. 验证数据
    print("✅ 验证...")
    print("-" * 80)
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=DB_IN,
            decode_responses=True
        )
        queue_len = r.llen(QUEUE_IN)
        print(f"✓ 队列 {QUEUE_IN} 中有 {queue_len} 条数据")
        
        if queue_len > 0:
            # 随机抽样验证
            sample_indices = random.sample(range(min(queue_len, 100)), min(3, queue_len))
            print(f"✓ 随机抽样验证 (位置: {sample_indices}):")
            
            for idx in sample_indices:
                sample = r.lindex(QUEUE_IN, idx)
                sample_data = json.loads(sample)
                print(f"  位置 {idx}:")
                print(f"    - ID: {sample_data.get('id')}")
                print(f"    - Source: {sample_data.get('source', '❌ 缺失')}")
                print(f"    - 有文本: {'✓' if sample_data.get('text') or sample_data.get('title') or sample_data.get('content') else '❌'}")
                
                timestamp = sample_data.get('timestamp')
                if timestamp:
                    hours_ago = (time.time() - timestamp) / 3600
                    print(f"    - 时间: {hours_ago:.1f} 小时前")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    
    print()
    
    # 4. 发送清洗通知
    print("📢 发送清洗通知...")
    print("-" * 80)
    print("正在向 Cleaner 发送 'crawler_complete' 通知...")
    print()
    
    if send_crawler_complete_notification():
        print("✅ 通知已发送！")
        print("  Cleaner 应该立即开始清洗数据")
    else:
        print("⚠️  通知可能未被接收")
        print("  请确保 Cleaner 正在运行")
    
    print()
    print("=" * 80)
    print("🧪 测试预期结果:")
    print("=" * 80)
    print("Cleaner 处理后，你应该看到:")
    print(f"✓ 约 {len(normal_data)} 条正常数据被清洗")
    print(f"❌ 约 {len(duplicate_data)} 条重复数据被过滤（去重）")
    print(f"❌ 约 {len(invalid_data)} 条无效数据被拒绝（验证失败）")
    print(f"❌ 约 {len(old_data)} 条超时数据可能被清理（如果启用时间窗口清理）")
    print()
    print("💡 监控命令:")
    print("=" * 80)
    print("1. 查看 Cleaner 日志:")
    print("   tail -f cleaner/logs/event_driven_cleaner.log")
    print()
    print("2. 查看清洗结果队列:")
    print("   redis-cli -n 1 LLEN clean_data_queue")
    print("   redis-cli -n 1 LRANGE clean_data_queue 0 2")
    print()
    print("3. 查看去重缓存:")
    print("   redis-cli -n 1 SCARD \"set:cleaned_ids\"")
    print("   redis-cli -n 1 SMEMBERS \"set:cleaned_ids\" | head -10")
    print()
    print("4. 查看清洗统计（如果启用）:")
    print("   redis-cli -n 1 GET \"stats:accepted\"")
    print("   redis-cli -n 1 GET \"stats:discarded\"")
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
