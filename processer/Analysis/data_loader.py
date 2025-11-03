import json
import redis
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config import CONFIG

# 导入 BERT 预测器（延迟加载，避免启动失败）
try:
    from bert_predictor import get_predictor
    BERT_PREDICTOR_AVAILABLE = True
except Exception as e:
    print(f"⚠️  BERT 预测器导入失败: {e}")
    BERT_PREDICTOR_AVAILABLE = False


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
            
            if initial_queue_len == 0:
                print(f"⚠️  警告：Redis 队列 '{queue_name}' 为空")
                return pd.DataFrame()
            
            # 批量读取队列中的所有数据（非消费模式，保留历史数据）
            # 使用 LRANGE 读取全部数据，不删除
            raw_data = self.redis_client.lrange(queue_name, 0, -1)
            
            if not raw_data:
                print(f"⚠️  警告：Redis 队列 '{queue_name}' 为空")
                return pd.DataFrame()
            
            # 解析 JSON 数据
            for item_json in raw_data:
                try:
                    item_data = json.loads(item_json)
                    data_list.append(item_data)
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON 解析错误，跳过该数据: {e}")
                    continue
            
            if data_list:
                print(f"✅ 成功从 Redis 队列读取 {len(data_list)} 条数据（历史数据保留）")
                df = pd.DataFrame(data_list)
                return df
            else:
                print(f"⚠️  警告：Redis 队列 '{queue_name}' 读取结果为空")
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

    def load_data(self, file_path: str = None) -> pd.DataFrame:
        """
        加载数据（优先 Redis，回退本地文件）
        
        Args:
            file_path: 本地 CSV 文件路径（可选）
            
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
        csv_path = file_path or self.config.get("input_file", "input_data.csv")
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
        # 优先使用 Cleaner 提供的 created_at（ISO格式），如果不存在则使用 timestamp
        if 'created_at' in df.columns:
            # Cleaner 提供了 created_at（ISO 格式字符串），转换为 datetime
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            # 如果没有 timestamp，从 created_at 创建
            if 'timestamp' not in df.columns:
                df['timestamp'] = df['created_at']
            else:
                # 如果 timestamp 是 Unix 时间戳，转换它
                if df['timestamp'].dtype in ['int64', 'float64']:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
                else:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        else:
            # Cleaner 没有提供 created_at，使用 timestamp
            if 'timestamp' not in df.columns:
                print("⚠️  警告：数据缺少 'timestamp' 和 'created_at' 字段，使用当前时间")
                df['timestamp'] = datetime.now()
                df['created_at'] = df['timestamp']
            else:
                # 转换 timestamp（Unix时间戳 → datetime对象）
                if df['timestamp'].dtype in ['int64', 'float64']:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
                else:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                # 创建 created_at = timestamp
                df['created_at'] = df['timestamp']

        # 清理文本数据（提前做，因为 BERT 预测需要）
        if 'text' in df.columns:
            df['clean_text'] = df['text'].fillna('').apply(self._clean_text)
        elif 'content' in df.columns:
            df['clean_text'] = df['content'].fillna('').apply(self._clean_text)
        else:
            df['clean_text'] = ''

        # === 🤖 BERT 情感预测集成 ===
        # 确保 sentiment 列存在
        if 'sentiment' not in df.columns:
            df['sentiment'] = ''
        
        # 标准化已有的情感标签
        sentiment_mapping = {
            '正面': 'Bullish',
            '中性': 'neutral',
            '负面': 'Bearish',
            'Bullish': 'Bullish',
            'neutral': 'neutral',
            'Bearish': 'Bearish',
        }
        df['sentiment'] = df['sentiment'].map(sentiment_mapping).fillna(df['sentiment'])
        
        # 使用 BERT 预测器为缺失 sentiment 的数据填充
        if BERT_PREDICTOR_AVAILABLE:
            try:
                predictor = get_predictor()
                # 使用原始 text 列进行预测（比 clean_text 保留更多信息）
                text_col = 'text' if 'text' in df.columns else 'content' if 'content' in df.columns else 'clean_text'
                df = predictor.fill_missing_sentiments(df, text_column=text_col)
            except Exception as e:
                print(f"⚠️  BERT 预测失败，使用默认值: {e}")
                # 填充空值为 neutral
                df['sentiment'] = df['sentiment'].fillna('neutral')
                df['sentiment'] = df['sentiment'].replace('', 'neutral')
        else:
            # 如果 BERT 不可用，填充为 neutral
            print("ℹ️  BERT 预测器不可用，使用默认 neutral 填充")
            df['sentiment'] = df['sentiment'].fillna('neutral')
            df['sentiment'] = df['sentiment'].replace('', 'neutral')

        return df

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not isinstance(text, str):
            return ""

        # 移除URL
        import re
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
        """获取时间窗口 - 智能适应实际数据跨度"""
        if df.empty or 'timestamp' not in df.columns:
            # 返回默认时间窗口
            now = datetime.now()
            current_window_minutes = self.config.get("current_window_minutes", 60)
            history_hours = self.config.get("history_hours", 24)
            return {
                'latest_time': now,
                'current_window_start': now - timedelta(minutes=current_window_minutes),
                'history_window_start': now - timedelta(hours=history_hours)
            }

        # 使用 timestamp 字段（已转换为 datetime）
        latest_time = df['timestamp'].max()
        earliest_time = df['timestamp'].min()
        
        # 读取配置中的时间窗口设置
        current_window_minutes = self.config.get("current_window_minutes", 60)
        history_hours = self.config.get("history_hours", 24)
        
        # 计算时间窗口
        current_window_start = latest_time - timedelta(minutes=current_window_minutes)
        history_window_start = latest_time - timedelta(hours=history_hours)
        
        # 检查历史窗口是否超出实际数据范围
        if history_window_start < earliest_time:
            history_window_start = earliest_time
            actual_hours = (latest_time - earliest_time).total_seconds() / 3600
            print(f"ℹ️  实际数据跨度 {actual_hours:.1f} 小时 < 配置的 {history_hours} 小时")
            print(f"   历史窗口已调整为: {earliest_time.isoformat()}")

        return {
            'latest_time': latest_time,
            'current_window_start': current_window_start,
            'history_window_start': history_window_start
        }