# backend/visualization_app/services/mock_data_generator.py
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any


class MockDataGenerator:
    """模拟数据生成器"""
    
    def __init__(self):
        self.keywords_pool = [
            "美联储", "比特币", "A股", "黄金", "原油", "美元", "人民币", 
            "美股", "港股", "国债", "通胀", "加息", "降息", "汇率",
            "科技股", "银行股", "房地产", "新能源", "人工智能", "区块链"
        ]
        self.news_sources = ["新浪财经", "财联社", "华尔街见闻", "东方财富", "同花顺", "雪球"]
        
    def generate_metadata(self) -> Dict[str, Any]:
        """生成元数据"""
        # 生成新闻来源统计
        news_sources_distribution = {}
        for source in self.news_sources:
            news_sources_distribution[source] = random.randint(50, 500)
        
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "update_interval": 30,
            "data_version": "1.0",
            "news_sources": news_sources_distribution
        }
    
    def generate_sentiment(self, base_positive: int = 50) -> Dict[str, Any]:
        """生成情绪数据"""
        positive = random.randint(base_positive - 10, base_positive + 20)
        neutral = random.randint(10, 30)
        negative = 100 - positive - neutral
        
        # 确保数值合理
        negative = max(0, min(30, negative))
        total = positive + neutral + negative
        # 归一化到100
        scale = 100 / total if total > 0 else 1
        positive = int(positive * scale)
        neutral = int(neutral * scale)
        negative = 100 - positive - neutral
        
        return {
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "total_comments": random.randint(500, 2000)
        }
    
    def generate_trending_keywords(self, count: int = 10) -> List[Dict[str, Any]]:
        """生成实时热词数据"""
        trending_data = []
        used_keywords = random.sample(self.keywords_pool, count)
        
        for i, keyword in enumerate(used_keywords):
            rank = i + 1
            
            # 根据排名设置不同的增长率和情绪
            if rank <= 3:
                growth_rate = random.randint(200, 350)
                sentiment_base = 70  # 前3名更积极
            elif rank <= 6:
                growth_rate = random.randint(100, 200)
                sentiment_base = 50  # 中间名次中性
            else:
                growth_rate = random.randint(50, 100)
                sentiment_base = 30  # 后几名相对消极
            
            trending_data.append({
                "keyword": keyword,
                "rank": rank,
                "current_frequency": random.randint(30, 50),
                "growth_rate": float(growth_rate),
                "trend_score": round(1.0 - (i * 0.08), 2),  # 排名越高分数越高
                "sentiment": self.generate_sentiment(sentiment_base)
            })
        
        return trending_data
    
    def generate_word_cloud(self, count: int = 20) -> List[Dict[str, Any]]:
        """生成词云数据"""
        word_cloud_data = []
        used_keywords = random.sample(self.keywords_pool, count)
        
        for keyword in used_keywords:
            word_cloud_data.append({
                "text": keyword,
                "value": random.randint(10, 100)
            })
        
        # 按value降序排序
        word_cloud_data.sort(key=lambda x: x["value"], reverse=True)
        return word_cloud_data
    
    def generate_history_data(self, keywords: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """生成历史趋势数据"""
        history_data = {}
        # 为所有关键词使用相同的基础时间，确保时间戳一致
        base_time = datetime.now() - timedelta(hours=24)
        
        for keyword in keywords:
            time_series = []
            
            for i in range(48):  # 24小时 * 每30分钟 = 48个点
                timestamp = base_time + timedelta(minutes=30 * i)
                
                # 模拟波动趋势
                base_freq = random.randint(5, 20)
                # 添加一些随机波动
                fluctuation = random.randint(-3, 3)
                frequency = max(1, base_freq + fluctuation)
                
                time_series.append({
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "frequency": frequency
                })
            
            history_data[keyword] = time_series
        
        return history_data
    
    def generate_news_feed(self, count: int = 10) -> List[Dict[str, Any]]:
        """生成新闻流数据"""
        news_data = []
        
        news_templates = [
            ("{keyword}出现重大突破，市场反应热烈", 70),
            ("{keyword}面临调整压力，投资者谨慎观望", 40),
            ("{keyword}政策利好，行业前景看好", 80),
            ("{keyword}交易活跃，成交量创新高", 60),
            ("{keyword}监管政策收紧，市场波动加大", 30),
            ("{keyword}技术面强劲，多头占据优势", 75),
            ("{keyword}基本面稳健，长期价值凸显", 65)
        ]
        
        base_time = datetime.now()
        
        for i in range(count):
            keyword = random.choice(self.keywords_pool)
            template, sentiment_base = random.choice(news_templates)
            title = template.format(keyword=keyword)
            
            # 时间递减，最新的新闻在前面
            publish_time = base_time - timedelta(minutes=30 * i)
            
            # 根据sentiment_base确定情感标签
            if sentiment_base >= 70:
                sentiment_label = 'positive'
            elif sentiment_base <= 40:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'
            
            news_data.append({
                "title": title,
                "publish_time": publish_time.strftime("%Y-%m-%d %H:%M:%S"),
                "source": random.choice(self.news_sources),
                "sentiment": sentiment_label  # 使用简单的字符串标签
            })
        
        # 按发布时间倒序排序
        news_data.sort(key=lambda x: x["publish_time"], reverse=True)
        return news_data
    
    def generate_complete_data(self) -> Dict[str, Any]:
        """生成完整的模拟数据"""
        trending_keywords = self.generate_trending_keywords(10)
        keyword_list = [item["keyword"] for item in trending_keywords]
        
        return {
            "metadata": self.generate_metadata(),
            "trending_keywords": trending_keywords,
            "word_cloud": self.generate_word_cloud(20),
            "history_data": self.generate_history_data(keyword_list),
            "news_feed": self.generate_news_feed(15)
        }


# 使用示例
if __name__ == "__main__":
    generator = MockDataGenerator()
    mock_data = generator.generate_complete_data()
    
    # 保存到文件（可选）
    with open("mock_data.json", "w", encoding="utf-8") as f:
        json.dump(mock_data, f, ensure_ascii=False, indent=2)
    
    print("模拟数据生成完成！")
    print(f"包含 {len(mock_data['trending_keywords'])} 个热词")
    print(f"包含 {len(mock_data['word_cloud'])} 个词云词汇")
    print(f"包含 {len(mock_data['news_feed'])} 条新闻")
