import json
from datetime import datetime
from data_loader import DataLoader
from text_analyzer import TextAnalyzer
from sentiment_analyzer import SentimentAnalyzer
from history_analyzer import HistoryAnalyzer
from news_processor import NewsProcessor
from redis_manager import RedisManager  # 新增导入
from config import CONFIG
import pandas as pd


class MainProcessor:
    def __init__(self):
        self.data_loader = DataLoader()
        self.text_analyzer = TextAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.history_analyzer = HistoryAnalyzer()
        self.news_processor = NewsProcessor()
        self.redis_manager = RedisManager()  # 新增
        self.config = CONFIG

    def process(self, input_file: str = None, output_file: str = None):
        """
        主处理流程
        
        Args:
            input_file: 输入文件路径（可选，优先使用 Redis）
            output_file: 输出文件路径
        """
        print("\n" + "="*60)
        print("🚀 Processer 处理开始")
        print("="*60)

        # 使用默认配置
        if input_file is None:
            input_file = self.config.get("input_file", "input_data.csv")
        if output_file is None:
            output_file = self.config.get("output_file", "output_data.json")

        # ✅ 验证 Redis 连接
        print("\n🔌 检查 Redis 连接...")
        if not self.redis_manager.verify_redis_connection():
            print("⚠️  警告：Redis 连接失败，系统将使用本地文件模式")
            print("         处理后的数据将无法推送到 Redis")

        # 1. 加载数据
        print("\n📥 加载数据...")
        raw_data = self.data_loader.load_data(input_file)
        
        if raw_data.empty:
            print("❌ 加载数据失败，退出处理")
            return False

        df = self.data_loader.preprocess_data(raw_data)
        time_windows = self.data_loader.get_time_windows(df)

        print(f"✓ 加载了 {len(df)} 条数据")
        print(f"  最早数据: {df['timestamp'].min().isoformat()}")
        print(f"  最新数据: {df['timestamp'].max().isoformat()}")

        # 2. 获取时间窗口数据
        # 当前窗口：最近1小时（用于计算实时趋势）
        # 历史窗口：过去24小时（用于计算历史基准）
        current_df = df[df['timestamp'] >= time_windows['current_window_start']]
        history_df = df[
            (df['timestamp'] >= time_windows['history_window_start']) &
            (df['timestamp'] < time_windows['current_window_start'])
        ]

        print(f"✓ 当前窗口数据（最近1小时）: {len(current_df)} 条")
        print(f"  时间范围: {time_windows['current_window_start'].isoformat()} ~ {time_windows['latest_time'].isoformat()}")
        print(f"✓ 历史窗口数据（过去24小时，不含当前小时）: {len(history_df)} 条")
        print(f"  时间范围: {time_windows['history_window_start'].isoformat()} ~ {time_windows['current_window_start'].isoformat()}")

        # 3. 词频分析
        print("\n🔍 执行文本分析...")
        current_keywords = self.text_analyzer.extract_keywords(current_df['clean_text'].tolist())

        # 计算历史24小时平均频率
        # 获取实际的时间区间数（每小时1次）
        history_start = time_windows['history_window_start']
        history_end = time_windows['latest_time']
        history_intervals = self.history_analyzer._create_time_intervals(history_start, history_end)
        total_intervals = len(history_intervals)
        
        print(f"  📊 历史分析: {total_intervals} 个时间区间 (每小时1个)")
        
        history_keywords_freq = {}
        for keyword, _ in current_keywords[:self.config['trending_keywords_count']]:
            keyword_history_df = history_df[history_df['clean_text'].str.contains(keyword, case=False, na=False)]
            history_avg_freq = len(keyword_history_df) / total_intervals if total_intervals > 0 else 0
            history_keywords_freq[keyword] = history_avg_freq

        # 4. 生成热词排行榜
        print("📊 生成热词排行榜...")
        trending_keywords = self._generate_trending_keywords(
            current_keywords, history_keywords_freq, df
        )

        # 5. 生成词云数据
        print("☁️  生成词云数据...")
        word_cloud = self._generate_word_cloud_data(current_keywords)

        # 6. 生成历史数据
        print("📈 生成历史数据...")
        top_keywords = [keyword for keyword, _ in current_keywords[:self.config['trending_keywords_count']]]
        # ✅ 传入精确的时间窗口，确保历史数据计算与主流程一致
        history_data = self.history_analyzer.generate_history_data(df, top_keywords, time_windows)

        # 7. 生成新闻流
        print("📰 生成新闻流...")
        news_feed = self.news_processor.generate_news_feed(df, top_keywords)

        # 8. 统计新闻来源
        print("📊 统计新闻来源分布...")
        news_sources = self._calculate_news_sources(df)

        # 9. 生成输出数据
        print("\n💾 生成输出数据...")
        output_data = self._generate_output_data(
            trending_keywords, word_cloud, history_data, news_feed, news_sources
        )

        # 10. 保存到本地文件
        print(f"💾 保存到本地文件: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"✅ 本地文件保存完成")

        # 11. 发布到 Redis
        print("\n📤 发布到 Redis...")
        if self.redis_manager.publish_processed_data(output_file):
            print("✅ 数据已成功发布到 Redis")
            
            # 验证 Redis 中的数据
            print("\n🔍 验证 Redis 输出键...")
            keys_info = self.redis_manager.check_output_keys()
            for key, status in keys_info.items():
                print(f"  {status} {key}")
        else:
            print("⚠️  数据发布到 Redis 失败")

        print("\n" + "="*60)
        print("✨ Processer 处理完成！")
        print("="*60)
        return True

    def _generate_trending_keywords(self, current_keywords: list, history_keywords_freq: dict,
                                    df: pd.DataFrame) -> list:
        """生成热词排行榜"""
        trending_data = []
        max_frequency = max([freq for _, freq in current_keywords]) if current_keywords else 1

        for rank, (keyword, current_freq) in enumerate(current_keywords[:self.config['trending_keywords_count']], 1):
            history_avg_freq = history_keywords_freq.get(keyword, 0)

            growth_rate = self.text_analyzer.calculate_growth_rate(current_freq, history_avg_freq)
            trend_score = self.text_analyzer.calculate_trend_score(current_freq, growth_rate, max_frequency)

            sentiment_data = self.sentiment_analyzer.analyze_sentiment_distribution(df, keyword)

            trending_data.append({
                "keyword": keyword,
                "rank": rank,
                "current_frequency": current_freq,
                "growth_rate": round(growth_rate, 1),
                "trend_score": trend_score,
                "sentiment": sentiment_data
            })

        return trending_data

    def _generate_word_cloud_data(self, keywords: list) -> list:
        """生成词云数据"""
        return [
            {"text": keyword, "value": freq}
            for keyword, freq in keywords[:self.config['word_cloud_count']]
        ]

    def _calculate_news_sources(self, df: pd.DataFrame) -> dict:
        """
        统计新闻来源分布
        
        Args:
            df: 数据框
            
        Returns:
            dict: 新闻来源统计数据，格式为 {"source_name": count, ...}
        """
        if 'source' not in df.columns:
            print("⚠️  警告：数据中没有 'source' 字段")
            return {}
        
        # 统计每个来源的数量
        source_counts = df['source'].value_counts().to_dict()
        
        # 处理空值或未知来源
        if pd.isna(list(source_counts.keys())[0]) if source_counts else False:
            source_counts['Unknown'] = source_counts.pop(list(source_counts.keys())[0])
        
        # 按数量排序
        source_counts = dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True))
        
        print(f"✓ 统计到 {len(source_counts)} 个新闻来源")
        for source, count in list(source_counts.items())[:5]:
            print(f"  - {source}: {count} 条")
        
        return source_counts

    def _generate_output_data(self, trending_keywords: list, word_cloud: list,
                              history_data: dict, news_feed: list, news_sources: dict) -> dict:
        """生成最终输出数据"""
        return {
            "metadata": {
                # ✅ ISO 8601 格式，带 UTC 时区标记
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "update_interval": self.config['history_interval_minutes'],
                "data_version": "1.0",
                "news_sources": news_sources  # 添加新闻来源统计
            },
            "trending_keywords": trending_keywords,
            "word_cloud": word_cloud,
            "history_data": history_data,
            "news_feed": news_feed
        }


if __name__ == "__main__":
    processor = MainProcessor()
    processor.process(
        input_file=CONFIG.get("input_file"),
        output_file=CONFIG.get("output_file")
    )