import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from config import CONFIG


class HistoryAnalyzer:
    def __init__(self):
        self.config = CONFIG

    def generate_history_data(self, df: pd.DataFrame, keywords: List[str], 
                            time_windows: Optional[Dict] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        生成历史趋势数据 - 严格生成 24 个整点的词频统计
        
        ✅ 关键修改：使用 created_at 字段而不是 timestamp
        
        Args:
            df: 数据框
            keywords: 关键词列表
            time_windows: 时间窗口字典，包含 'history_window_start' 和 'latest_time'
                         如果为 None，则自动计算（不推荐）
        """
        history_data = {}

        # ✅ 使用 created_at 字段（Cleaner 的真实时间）
        time_field = 'created_at' if 'created_at' in df.columns else 'timestamp'

        # 获取时间范围
        if time_windows is not None:
            # ✅ 使用外部传入的时间窗口（由 main.py 精确计算）
            end_time = time_windows['latest_time']  # 应该是整点时间
            start_time = time_windows['history_window_start']  # 应该是 end_time - 25h
        else:
            # ⚠️  备用方案：自动计算（可能与 main.py 的计算不一致）
            end_time = df[time_field].max().replace(minute=0, second=0, microsecond=0)
            start_time = end_time - timedelta(hours=25)
            print("⚠️  警告：未传入 time_windows，已自动计算，可能与主流程不一致")

        # ✅ 创建严格的 24 个整点时间区间
        time_intervals = self._create_24hour_intervals(start_time, end_time)
        
        print(f"\n📊 历史数据生成配置:")
        print(f"  时间字段: {time_field} ✅")
        print(f"  固定词集数: {len(keywords)} 个 ✅（固定不变）")
        print(f"  时间窗口: {start_time.isoformat()} ~ {end_time.isoformat()}")
        print(f"  时间区间数: {len(time_intervals)} 个（应为 24 个）")

        for keyword in keywords:
            keyword_data = []

            # 过滤包含关键词的数据
            keyword_df = df[df['clean_text'].str.contains(keyword, case=False, na=False)]

            for interval_start, interval_end in time_intervals:
                # ✅ 使用 created_at 字段统计每个时间区间的频率（闭区间：[start, end]）
                interval_count = len(
                    keyword_df[
                        (keyword_df[time_field] >= interval_start) &
                        (keyword_df[time_field] < interval_end)
                        ]
                )

                keyword_data.append({
                    # ✅ 使用整点时间，ISO 8601 格式，带 UTC 时区标记
                    "timestamp": interval_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "frequency": interval_count
                })

            history_data[keyword] = keyword_data
            
        # 验证输出
        if history_data:
            first_keyword = list(history_data.keys())[0]
            print(f"\n✅ 历史数据生成完成:")
            print(f"  关键词数: {len(history_data)}")
            print(f"  每个关键词的数据点: {len(history_data[first_keyword])} 个")

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

    def _create_24hour_intervals(self, start_time: datetime, end_time: datetime) -> List[tuple]:
        """
        严格生成 24 个整点时间区间（向后 24 小时）
        
        确保生成的区间数始终为 24，每个区间跨度为 1 小时
        
        ✅ 关键改动：确保生成的是最后 24 个完整的小时
        例如：
          - 最新时间: 09:50
          - 向上取整到: 10:00
          - start_time: 10:00 - 25h = 09:00（前一天）
          - end_time: 10:00
          - 生成区间: [09:00, 10:00], [10:00, 11:00], ..., [08:00, 09:00]（下一天）
          - 共 24 个区间，覆盖整个 24 小时
        
        Args:
            start_time: 起始时间
            end_time: 结束时间
        
        Returns:
            List[tuple]: 24 个时间区间，每个为 (start, end) 元组
        """
        intervals = []
        
        # ✅ 确保 end_time 是整点
        end_time_hour = end_time.replace(minute=0, second=0, microsecond=0)
        
        # ✅ 生成严格的 24 个整点时间区间
        # 从 end_time 向后推 24 小时
        for i in range(24):
            interval_start = end_time_hour - timedelta(hours=(24 - i))
            interval_end = interval_start + timedelta(hours=1)
            intervals.append((interval_start, interval_end))
        
        return intervals