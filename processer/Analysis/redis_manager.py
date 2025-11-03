import json
import redis
import os
from datetime import datetime
from config import CONFIG


class RedisManager:
    def __init__(self):
        # Redis连接配置
        self.redis_host = CONFIG["redis"]["host"]
        self.redis_port = CONFIG["redis"]["port"]
        self.redis_password = CONFIG["redis"]["password"]
        self.output_prefix = CONFIG["redis"]["output_prefix"]
        self.key_ttl = CONFIG["redis"]["key_ttl_seconds"]
        
        # 输入数据库配置（从 Cleaner 读取）
        self.input_db = CONFIG["redis"]["input_db"]  # DB1
        # 输出数据库配置（写入处理结果）
        self.output_db = CONFIG["redis"]["output_db"]  # DB2

        # 连接两个数据库
        self.r_input = self._connect_redis(self.input_db, "输入")  # 从 DB1 读取
        self.r = self._connect_redis(self.output_db, "输出")  # 写入 DB2（保持兼容性）

    def _connect_redis(self, db, db_name=""):
        """连接 Redis 数据库"""
        try:
            r = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=db,
                password=self.redis_password,
                decode_responses=True
            )
            r.ping()
            print(f"✅ Redis {db_name}连接成功 (DB{db})")
            return r
        except redis.ConnectionError as e:
            print(f"❌ Redis {db_name}连接失败: {e}")
            return None

    def save_raw_data_to_local(self, filename=None):
        """从Redis获取原始数据并保存到本地format_conversion文件夹"""
        if not self.r:
            print("Redis未连接，无法获取数据")
            return False

        try:
            # 这里假设原始数据存储在一个特定的键中
            # 您可能需要根据实际情况调整这个键名
            raw_data_key = "raw_financial_data"
            raw_data = self.r.get(raw_data_key)

            if not raw_data:
                print(f"Redis中没有找到原始数据键: {raw_data_key}")
                return False

            # 解析JSON数据
            data = json.loads(raw_data)

            # 创建format_conversion文件夹（如果不存在）
            conversion_dir = "Format conversion"
            if not os.path.exists(conversion_dir):
                os.makedirs(conversion_dir)

            # 生成文件名
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"input_data_{timestamp}.jsonl"
            else:
                # 确保是jsonl格式
                if not filename.endswith('.jsonl'):
                    filename = filename.replace('.json', '.jsonl')

            filepath = os.path.join(conversion_dir, filename)

            # 保存到本地文件
            with open(filepath, 'w', encoding='utf-8') as f:
                # 如果是列表，逐行写入
                if isinstance(data, list):
                    for item in data:
                        f.write(json.dumps(item, ensure_ascii=False) + '\n')
                else:
                    # 如果是单个对象，直接写入
                    f.write(json.dumps(data, ensure_ascii=False))

            print(f"原始数据已保存到: {filepath}")
            return filepath

        except Exception as e:
            print(f"保存原始数据时出错: {e}")
            return False

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

            # 添加发布时间戳 - ✅ ISO 8601 格式，带 UTC 时区标记
            processed_data['metadata']['redis_publish_time'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

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
                print(f"✅ Redis 已连接 (输出DB{self.output_db})")
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
        if not self.r:
            return {}
        
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


# 使用示例
if __name__ == "__main__":
    import time

    redis_manager = RedisManager()

    # 获取Redis信息
    info = redis_manager.get_redis_info()
    if info:
        print("Redis服务器信息:")
        for key, value in info.items():
            print(f"  {key}: {value}")

    # 保存原始数据到本地
    redis_manager.save_raw_data_to_local()

    # 发布处理后的数据
    redis_manager.publish_processed_data()

    # 获取处理后的数据（测试）
    processed_data = redis_manager.get_processed_data()
    if processed_data:
        print("成功从Redis获取处理数据")
        print(f"热门关键词数量: {len(processed_data['trending_keywords'])}")
        print(f"历史数据关键词数量: {len(processed_data['history_data'])}")