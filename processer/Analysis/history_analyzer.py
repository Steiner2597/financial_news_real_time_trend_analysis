import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
from config import CONFIG


class HistoryAnalyzer:
    def __init__(self):
        self.config = CONFIG

    def generate_history_data(self, df: pd.DataFrame, keywords: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """生成历史趋势数据"""
        history_data = {}

        # 获取时间范围
        end_time = df['timestamp'].max()
        start_time = end_time - timedelta(hours=self.config['history_hours'])

        # 创建时间区间
        time_intervals = self._create_time_intervals(start_time, end_time)

        for keyword in keywords:
            keyword_data = []

            # 过滤包含关键词的数据
            keyword_df = df[df['clean_text'].str.contains(keyword, case=False, na=False)]

            for interval_start, interval_end in time_intervals:
                # 统计每个时间区间的频率
                interval_count = len(
                    keyword_df[
                        (keyword_df['timestamp'] >= interval_start) &
                        (keyword_df['timestamp'] < interval_end)
                        ]
                )

                keyword_data.append({
                    # ✅ ISO 8601 格式，带 UTC 时区标记
                    "timestamp": interval_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "frequency": interval_count
                })

            history_data[keyword] = keyword_data

        return history_data

    def _create_time_intervals(self, start_time: datetime, end_time: datetime) -> List[tuple]:
        """创建时间区间 - 按整点小时划分"""
        intervals = []
        
        # 将开始时间向下取整到整点
        current_hour_start = start_time.replace(minute=0, second=0, microsecond=0)
        
        # 将结束时间向下取整到当前所在整点
        end_hour_start = end_time.replace(minute=0, second=0, microsecond=0)
        
        # 如果结束时间不是整点，则包含当前小时
        if end_time.minute > 0 or end_time.second > 0 or end_time.microsecond > 0:
            end_hour_end = end_hour_start + timedelta(hours=1)
        else:
            end_hour_end = end_hour_start
        
        # 生成每个整点小时的区间
        current_time = current_hour_start
        while current_time < end_hour_end:
            next_time = current_time + timedelta(hours=1)
            intervals.append((current_time, next_time))
            current_time = next_time

        return intervals