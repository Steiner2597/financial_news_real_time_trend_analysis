import re
from collections import Counter
from typing import List, Dict, Any, Tuple
import pandas as pd
from config import CONFIG


class TextAnalyzer:
    def __init__(self):
        self.config = CONFIG
        self.stop_words = set(self.config['stop_words'])

    def extract_keywords(self, texts: List[str], top_n: int = None) -> List[Tuple[str, int]]:
        """提取关键词并计算词频"""
        if top_n is None:
            top_n = self.config['word_cloud_count']

        all_words = []
        for text in texts:
            if isinstance(text, str):
                words = self._tokenize_text(text)
                all_words.extend(words)

        # 计算词频
        word_freq = Counter(all_words)

        # 返回前N个关键词
        return word_freq.most_common(top_n)

    def _tokenize_text(self, text: str) -> List[str]:
        """分词处理"""
        words = text.split()

        # 过滤停用词和短词
        filtered_words = [
            word for word in words
            if (len(word) > 2 and
                word not in self.stop_words and
                not word.isdigit())
        ]

        return filtered_words

    def calculate_growth_rate(self, current_freq: int, history_avg_freq: float) -> float:
        """计算增长率 - 当前30分钟频率与历史24小时平均频率比较"""
        if history_avg_freq == 0:
            return 0.0 if current_freq == 0 else 100.0
        return ((current_freq - history_avg_freq) / history_avg_freq) * 100

    def calculate_trend_score(self, frequency: int, growth_rate: float, max_frequency: int) -> float:
        """计算趋势分数"""
        # 归一化频率 (0-1)
        freq_score = frequency / max_frequency if max_frequency > 0 else 0

        # 归一化增长率 (0-1)
        growth_score = min(abs(growth_rate) / 100, 1.0)

        # 综合分数 (频率权重0.6，增长率权重0.4)
        trend_score = (freq_score * 0.6) + (growth_score * 0.4)

        return round(trend_score, 2)