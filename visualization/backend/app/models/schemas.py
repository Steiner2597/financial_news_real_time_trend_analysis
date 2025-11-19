# Pydantic数据模型
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime


class SentimentData(BaseModel):
    positive: int
    neutral: int
    negative: int
    total_comments: int


class TrendingKeyword(BaseModel):
    keyword: str
    rank: int
    current_frequency: int
    growth_rate: float
    trend_score: float
    sentiment: SentimentData


class WordCloudItem(BaseModel):
    text: str
    value: int


class HistoryPoint(BaseModel):
    timestamp: str
    frequency: int


class NewsItem(BaseModel):
    title: str
    publish_time: str
    source: str
    sentiment: SentimentData


class APIResponse(BaseModel):
    metadata: Dict[str, Any]
    trending_keywords: List[TrendingKeyword]
    word_cloud: List[WordCloudItem]
    history_data: Dict[str, List[HistoryPoint]]
    news_feed: List[NewsItem]
