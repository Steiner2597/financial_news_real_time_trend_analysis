# Processer 模块修复方案

## 概览

本文档提供了将 Processer 模块从**本地 CSV 文件处理**改为**实时 Redis 流处理**的完整修复方案。

---

## 修复方案详解

### 第一步：修改配置文件

**文件路径：** `processer/Analysis/config.py`

**修改内容：**

```python
# 配置文件
CONFIG = {
    # 原有配置...
    "input_file": "input_data.csv",  # 保留为备份/回退方案
    "output_file": "output_data.json",
    "trending_keywords_count": 10,
    "word_cloud_count": 20,
    "history_hours": 24,
    "history_interval_minutes": 30,

    # ==================== 修改：Redis配置 ====================
    "redis": {
        "host": "localhost",
        "port": 6379,
        
        # 💡 新增：明确的数据流配置
        "input_db": 1,              # 从 DB1 读取（Cleaner 的输出）
        "output_db": 0,             # 输出到 DB0（Visualization 的输入）
        
        # 💡 新增：队列名配置
        "input_queue": "clean_data_queue",    # 从 Cleaner 的输出队列读取
        "output_prefix": "processed_data",    # 输出键的前缀
        
        # 可选：发布订阅（用于实时通知）
        "publish_channel": "processed_data_updates",
        
        # 过期时间
        "key_ttl_seconds": 86400,  # 24小时
        
        "password": None,
    },

    "stop_words": [
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        # ... 保持原样 ...
    ]
}
```

---

### 第二步：修改数据加载器

**文件路径：** `processer/Analysis/data_loader.py`

**替换为：**

```python
import json
import redis
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config import CONFIG


class DataLoader:
    """数据加载器 - 支持 Redis 实时流和本地文件两种模式"""

    def __init__(self):
        self.config = CONFIG
        self._init_redis()

    def _init_redis(self):
        """初始化 Redis 连接到 DB1（Cleaner 的输出 DB）"""
        try:
            self.redis_client = redis.Redis(
                host=self.config["redis"]["host"],
                port=self.config["redis"]["port"],
                db=self.config["redis"]["input_db"],  # 连接到 DB1
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            print("✅ Redis 连接成功（DB1 - Cleaner 输出）")
        except Exception as e:
            print(f"⚠️  Redis 连接失败: {e}，将使用本地文件模式")
            self.redis_client = None

    def load_data_from_redis(self) -> pd.DataFrame:
        """
        从 Redis 队列读取清洗后的数据
        
        Returns:
            pd.DataFrame: 清洗后的数据
        """
        if not self.redis_client:
            print("❌ Redis 未连接，无法从队列读取数据")
            return pd.DataFrame()

        queue_name = self.config["redis"]["input_queue"]
        data_list = []
        
        try:
            # 统计初始队列长度
            initial_queue_len = self.redis_client.llen(queue_name)
            print(f"📊 Redis 队列 '{queue_name}' 中有 {initial_queue_len} 条数据")
            
            # 批量读取队列中的所有数据
            # 注意：这会清空队列，确保已备份重要数据
            timeout = 300  # 5分钟超时
            start_time = datetime.now()
            
            while (datetime.now() - start_time).total_seconds() < timeout:
                # 使用 lpop 逐条读取（FIFO）
                item_json = self.redis_client.lpop(queue_name)
                
                if not item_json:
                    break
                
                try:
                    item_data = json.loads(item_json)
                    data_list.append(item_data)
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON 解析错误，跳过该数据: {e}")
                    continue
            
            if data_list:
                print(f"✅ 成功从 Redis 队列读取 {len(data_list)} 条数据")
                df = pd.DataFrame(data_list)
                return df
            else:
                print(f"⚠️  警告：Redis 队列 '{queue_name}' 为空")
                return pd.DataFrame()

        except Exception as e:
            print(f"❌ 从 Redis 读取数据失败: {e}")
            return pd.DataFrame()

    def load_data_from_file(self, file_path: str) -> pd.DataFrame:
        """
        从本地 CSV 文件读取数据（备份方案）
        
        Args:
            file_path: CSV 文件路径
            
        Returns:
            pd.DataFrame: 数据
        """
        try:
            print(f"📂 从本地文件加载数据: {file_path}")
            df = pd.read_csv(file_path)
            print(f"✅ 成功加载本地文件，共 {len(df)} 条数据")
            return df
        except FileNotFoundError:
            print(f"❌ 文件不存在: {file_path}")
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ 加载文件失败: {e}")
            return pd.DataFrame()

    def load_data(self, input_file: str = None) -> pd.DataFrame:
        """
        加载数据（优先 Redis，回退本地文件）
        
        Args:
            input_file: 本地 CSV 文件路径（可选）
            
        Returns:
            pd.DataFrame: 加载的数据
        """
        # 策略 1: 优先尝试从 Redis 读取
        print("\n🔄 尝试从 Redis 队列读取数据...")
        df_redis = self.load_data_from_redis()
        
        if not df_redis.empty:
            print("✨ 使用 Redis 实时数据处理模式")
            return df_redis
        
        # 策略 2: 回退到本地 CSV 文件
        csv_path = input_file or self.config.get("input_file", "input_data.csv")
        print(f"\n🔄 Redis 队列为空，尝试本地文件...")
        df_file = self.load_data_from_file(csv_path)
        
        if not df_file.empty:
            print("✨ 使用本地文件处理模式")
            return df_file
        
        # 都失败则返回空
        print("❌ 无法加载任何数据")
        return pd.DataFrame()

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        数据预处理（保持原逻辑）
        
        Args:
            df: 输入数据框
            
        Returns:
            pd.DataFrame: 预处理后的数据
        """
        if df.empty:
            return df

        # 转换时间格式
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # 转换情感标签（如果存在）
        if 'sentiment' in df.columns:
            sentiment_mapping = {
                '正面': 'positive',
                '中性': 'neutral',
                '负面': 'negative',
                'positive': 'positive',
                'neutral': 'neutral',
                'negative': 'negative',
            }
            df['sentiment'] = df['sentiment'].map(sentiment_mapping)
            df['sentiment'] = df['sentiment'].fillna('neutral')

        # 清理文本数据
        if 'text' in df.columns:
            df['clean_text'] = df['text'].fillna('').apply(self._clean_text)
        elif 'content' in df.columns:
            df['clean_text'] = df['content'].fillna('').apply(self._clean_text)
        else:
            df['clean_text'] = ''

        return df

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not isinstance(text, str):
            return ""

        import re
        
        # 移除URL
        text = re.sub(r'http\S+', '', text)

        # 移除股票代码（如$ETH.X）
        text = re.sub(r'\$\w+\.\w+', '', text)

        # 移除特殊字符，保留字母数字和空格
        text = re.sub(r'[^\w\s]', ' ', text)

        # 转换为小写
        text = text.lower()

        # 移除多余空格
        text = ' '.join(text.split())

        return text

    def get_time_windows(self, df: pd.DataFrame) -> Dict[str, datetime]:
        """获取时间窗口"""
        if df.empty:
            # 返回默认时间窗口
            now = datetime.now()
            return {
                'latest_time': now,
                'current_window_start': now - timedelta(minutes=30),
                'history_window_start': now - timedelta(hours=24)
            }

        # 从数据中获取时间
        time_column = 'created_at' if 'created_at' in df.columns else 'timestamp'
        
        if time_column not in df.columns:
            now = datetime.now()
            return {
                'latest_time': now,
                'current_window_start': now - timedelta(minutes=30),
                'history_window_start': now - timedelta(hours=24)
            }

        latest_time = pd.to_datetime(df[time_column]).max()
        current_window_start = latest_time - timedelta(minutes=30)
        history_window_start = latest_time - timedelta(hours=24)

        return {
            'latest_time': latest_time,
            'current_window_start': current_window_start,
            'history_window_start': history_window_start
        }
```

---

### 第三步：修改 Redis 管理器

**文件路径：** `processer/Analysis/redis_manager.py`

**关键修改：使用 String 结构而不是 Hash 结构**

```python
import json
import redis
import os
from datetime import datetime
from config import CONFIG


class RedisManager:
    def __init__(self):
        # Redis连接配置 - 连接到 DB0（输出数据库）
        self.redis_host = CONFIG["redis"]["host"]
        self.redis_port = CONFIG["redis"]["port"]
        self.redis_db = CONFIG["redis"]["output_db"]  # 使用 output_db
        self.redis_password = CONFIG["redis"]["password"]
        self.output_prefix = CONFIG["redis"]["output_prefix"]
        self.key_ttl = CONFIG["redis"]["key_ttl_seconds"]

        # 连接Redis
        self.r = self._connect_redis()

    def _connect_redis(self):
        """连接 Redis 数据库"""
        try:
            r = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True
            )
            r.ping()
            print(f"✅ Redis 连接成功 (DB{self.redis_db})")
            return r
        except redis.ConnectionError as e:
            print(f"❌ Redis 连接失败: {e}")
            return None

    def publish_processed_data(self, output_file_path=None):
        """
        将处理后的数据发布到 Redis
        
        使用 String 结构（而非 Hash）确保与 Visualization 兼容
        """
        if not self.r:
            print("❌ Redis 未连接，无法发布数据")
            return False

        try:
            # 读取处理后的数据
            if output_file_path is None:
                output_file_path = "output_data.json"

            with open(output_file_path, 'r', encoding='utf-8') as f:
                processed_data = json.load(f)

            # 添加发布时间戳
            processed_data['metadata']['redis_publish_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # ==================== 使用 String 结构存储 ====================
            # 这样 Visualization 可以通过 redis.get("processed_data:metadata") 读取
            
            print("\n📤 发布处理后的数据到 Redis...")
            
            # 1. 发布元数据
            metadata_key = f"{self.output_prefix}:metadata"
            self.r.set(
                metadata_key,
                json.dumps(processed_data['metadata'], ensure_ascii=False)
            )
            self.r.expire(metadata_key, self.key_ttl)
            print(f"  ✓ {metadata_key}")

            # 2. 发布热词数据
            keywords_key = f"{self.output_prefix}:trending_keywords"
            self.r.set(
                keywords_key,
                json.dumps(processed_data['trending_keywords'], ensure_ascii=False)
            )
            self.r.expire(keywords_key, self.key_ttl)
            print(f"  ✓ {keywords_key}")

            # 3. 发布词云数据
            wordcloud_key = f"{self.output_prefix}:word_cloud"
            self.r.set(
                wordcloud_key,
                json.dumps(processed_data['word_cloud'], ensure_ascii=False)
            )
            self.r.expire(wordcloud_key, self.key_ttl)
            print(f"  ✓ {wordcloud_key}")

            # 4. 发布新闻数据
            news_key = f"{self.output_prefix}:news_feed"
            self.r.set(
                news_key,
                json.dumps(processed_data['news_feed'], ensure_ascii=False)
            )
            self.r.expire(news_key, self.key_ttl)
            print(f"  ✓ {news_key}")

            # 5. 发布历史数据
            history_data = processed_data.get('history_data', {})
            for keyword, data in history_data.items():
                history_key = f"{self.output_prefix}:history_data:{keyword}"
                self.r.set(
                    history_key,
                    json.dumps(data, ensure_ascii=False)
                )
                self.r.expire(history_key, self.key_ttl)
            
            print(f"  ✓ {len(history_data)} 条历史数据")

            # 可选：发布通知消息
            if "publish_channel" in CONFIG["redis"]:
                channel = CONFIG["redis"]["publish_channel"]
                self.r.publish(channel, json.dumps({
                    "event": "data_updated",
                    "timestamp": datetime.now().isoformat(),
                    "keywords_count": len(processed_data['trending_keywords']),
                    "history_count": len(history_data)
                }))
                print(f"  ✓ 发布更新通知到 {channel}")

            print("✅ 所有数据已成功发布到 Redis (DB0)")
            return True

        except FileNotFoundError:
            print(f"❌ 文件不存在: {output_file_path}")
            return False
        except Exception as e:
            print(f"❌ 发布数据时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_processed_data(self) -> dict:
        """从 Redis 读取处理后的数据（验证）"""
        if not self.r:
            print("❌ Redis 未连接")
            return None

        try:
            metadata_key = f"{self.output_prefix}:metadata"
            metadata_json = self.r.get(metadata_key)
            
            if not metadata_json:
                print(f"⚠️  Redis 中未找到数据（键：{metadata_key}）")
                return None

            keywords_json = self.r.get(f"{self.output_prefix}:trending_keywords")
            wordcloud_json = self.r.get(f"{self.output_prefix}:word_cloud")
            news_json = self.r.get(f"{self.output_prefix}:news_feed")

            result = {
                "metadata": json.loads(metadata_json) if metadata_json else {},
                "trending_keywords": json.loads(keywords_json) if keywords_json else [],
                "word_cloud": json.loads(wordcloud_json) if wordcloud_json else [],
                "news_feed": json.loads(news_json) if news_json else []
            }

            print(f"✅ 成功读取处理数据：{len(result['trending_keywords'])} 个热词")
            return result

        except Exception as e:
            print(f"❌ 读取处理数据失败: {e}")
            return None

    def verify_redis_connection(self) -> bool:
        """验证 Redis 连接"""
        if self.r:
            try:
                self.r.ping()
                info = self.r.info()
                print(f"✅ Redis 已连接 (DB{self.redis_db})")
                print(f"   Redis 版本: {info.get('redis_version')}")
                print(f"   已连接客户端: {info.get('connected_clients')}")
                print(f"   已用内存: {info.get('used_memory_human')}")
                return True
            except Exception as e:
                print(f"❌ Redis 连接已断开: {e}")
                return False
        return False

    def check_output_keys(self) -> dict:
        """检查输出键是否存在"""
        keys_info = {}
        for suffix in ['metadata', 'trending_keywords', 'word_cloud', 'news_feed']:
            key = f"{self.output_prefix}:{suffix}"
            exists = self.r.exists(key)
            if exists:
                size = len(self.r.get(key) or "")
                keys_info[key] = f"✓ 存在 ({size} bytes)"
            else:
                keys_info[key] = "✗ 不存在"
        
        return keys_info
```

---

### 第四步：修改主处理程序

**文件路径：** `processer/Analysis/main.py`

**关键修改：添加 Redis 连接检查和改进的日志**

```python
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

        # 2. 获取时间窗口数据
        current_df = df[df['created_at'] >= time_windows['current_window_start']]
        history_df = df[
            (df['created_at'] >= time_windows['history_window_start']) &
            (df['created_at'] < time_windows['current_window_start'])
        ]

        print(f"✓ 当前窗口数据: {len(current_df)} 条")
        print(f"✓ 历史窗口数据: {len(history_df)} 条")

        # 3. 词频分析
        print("\n🔍 执行文本分析...")
        current_keywords = self.text_analyzer.extract_keywords(current_df['clean_text'].tolist())

        # 计算历史24小时平均频率
        history_keywords_freq = {}
        for keyword, _ in current_keywords[:self.config['trending_keywords_count']]:
            keyword_history_df = history_df[history_df['clean_text'].str.contains(keyword, case=False, na=False)]
            total_intervals = 48
            history_avg_freq = len(keyword_history_df) / total_intervals
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
        history_data = self.history_analyzer.generate_history_data(df, top_keywords)

        # 7. 生成新闻流
        print("📰 生成新闻流...")
        news_feed = self.news_processor.generate_news_feed(df, top_keywords)

        # 8. 生成输出数据
        print("\n💾 生成输出数据...")
        output_data = self._generate_output_data(
            trending_keywords, word_cloud, history_data, news_feed
        )

        # 9. 保存到本地文件
        print(f"💾 保存到本地文件: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"✅ 本地文件保存完成")

        # 10. 发布到 Redis
        print("\n📤 发布到 Redis...")
        if self.redis_manager.publish_processed_data(output_file):
            print("✅ 数据已成功发布到 Redis")
        else:
            print("⚠️  数据发布到 Redis 失败")

        print("\n" + "="*60)
        print("✨ Processer 处理完成！")
        print("="*60)
        return True

    def _generate_trending_keywords(self, current_keywords: list, history_keywords_freq: dict,
                                    df: pd.DataFrame) -> list:
        """生成热词排行榜（保持原逻辑）"""
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
        """生成词云数据（保持原逻辑）"""
        return [
            {"text": keyword, "value": freq}
            for keyword, freq in keywords[:self.config['word_cloud_count']]
        ]

    def _generate_output_data(self, trending_keywords: list, word_cloud: list,
                              history_data: dict, news_feed: list) -> dict:
        """生成最终输出数据（保持原逻辑）"""
        return {
            "metadata": {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "update_interval": self.config['history_interval_minutes'],
                "data_version": "1.0"
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
```

---

## 验证清单

修改后，请按以下步骤验证：

```bash
# 1. 验证配置文件
cd processer/Analysis
python -c "from config import CONFIG; print(CONFIG['redis'])"

# 2. 测试数据加载
python -c "from data_loader import DataLoader; dl = DataLoader(); df = dl.load_data(); print(f'加载了 {len(df)} 条数据')"

# 3. 运行完整处理
python main.py

# 4. 验证 Redis 输出
redis-cli
> SELECT 0
> KEYS processed_data:*
> GET processed_data:metadata
```

---

## 常见问题排查

| 问题 | 症状 | 解决方案 |
|------|------|---------|
| Redis 连接失败 | "Redis 连接失败" 错误 | 检查 Redis 是否运行：`redis-cli ping` |
| 队列为空 | "Redis 队列为空" 警告 | 检查 Cleaner 是否正确输出数据 |
| 数据结构不匹配 | Visualization 读取不到数据 | 确认使用了 `redis.set()` 而非 `redis.hset()` |
| 文件模式回退 | 始终使用本地 CSV | 检查 Redis 和 Cleaner 模块状态 |

