import pandas as pd
from typing import List, Dict, Any
from sentiment_analyzer import SentimentAnalyzer


class NewsProcessor:
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()

    def generate_news_feed(self, df: pd.DataFrame, top_keywords: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        """生成新闻流数据"""
        # 按时间倒序排列
        sorted_df = df.sort_values('timestamp', ascending=False)

        news_feed = []
        for _, row in sorted_df.head(limit).iterrows():
            # 使用text作为标题，不再截取，完整展示
            title = row['text']

            # 分析该条新闻的情感分布
            news_sentiment = self.sentiment_analyzer.analyze_sentiment_distribution(
                df[df['id'] == row['id']],  # 这里简化处理，实际可能需要关联评论
                keyword=None
            )

            # 根据情感分布确定主要情感类型
            sentiment_label = self._determine_sentiment_label(news_sentiment)

            news_item = {
                "title": title,
                # ✅ ISO 8601 格式，带 UTC 时区标记
                "publish_time": row['timestamp'].strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(row['timestamp'], pd.Timestamp) else str(row['timestamp']),
                "source": row['source'],
                "url": row.get('url', ''),  # 获取URL，如果不存在则为空字符串
                "sentiment": sentiment_label  # 使用简单的字符串标签
            }

            news_feed.append(news_item)

        return news_feed

    def _determine_sentiment_label(self, sentiment_data: Dict[str, Any]) -> str:
        """
        根据情感分布确定主要情感标签
        
        Args:
            sentiment_data: 包含positive, neutral, negative的情感分布数据
            
        Returns:
            str: 'positive', 'neutral', 或 'negative'
        """
        positive = sentiment_data.get('positive', 0)
        neutral = sentiment_data.get('neutral', 0)
        negative = sentiment_data.get('negative', 0)
        
        # 找出最大的情感类型
        max_sentiment = max(positive, neutral, negative)
        
        if max_sentiment == positive:
            return 'positive'
        elif max_sentiment == negative:
            return 'negative'
        else:
            return 'neutral'