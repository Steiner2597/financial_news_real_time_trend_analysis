from typing import Dict, List, Any
import pandas as pd
from collections import Counter


class SentimentAnalyzer:
    def __init__(self):
        self.sentiment_labels = ['Bullish', 'Bearish']

    def analyze_sentiment_distribution(self, df: pd.DataFrame, keyword: str = None) -> Dict[str, Any]:
        """分析情感分布"""
        if keyword:
            # 过滤包含关键词的文本
            filtered_df = df[df['clean_text'].str.contains(keyword, case=False, na=False)]
        else:
            filtered_df = df

        # 统计情感分布
        sentiment_counts = filtered_df['sentiment'].value_counts()

        total = len(filtered_df)
        if total == 0:
            return {
                "positive": 0,
                "negative": 100,
                "total_comments": 0
            }

        # 计算百分比（内部使用 Bullish/Bearish，输出转换为 positive/negative）
        bullish_percent = round((sentiment_counts.get('Bullish', 0) / total) * 100)
        bearish_percent = round((sentiment_counts.get('Bearish', 0) / total) * 100)
        
        # 确保总和为100%
        total_percent = bullish_percent + bearish_percent
        if total_percent != 100:
            bearish_percent += (100 - total_percent)
        
        # 输出时转换为 positive/negative
        result = {
            "positive": bullish_percent,
            "negative": bearish_percent,
            "total_comments": total
        }

        return result

    def get_comments_for_keyword(self, df: pd.DataFrame, keyword: str, limit: int = 50) -> pd.DataFrame:
        """获取包含特定关键词的评论"""
        return df[df['clean_text'].str.contains(keyword, case=False, na=False)].head(limit)