# backend/app/services/redis_client.py
import json
import redis
from typing import Dict, List, Any
from ..config import settings


class RedisClient:
    """Redis客户端 - 直接从processed_data命名空间读取数据"""

    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,  # 使用配置的DB（DB2）
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            print(f"✅ Redis客户端连接成功! (DB{settings.REDIS_DB})")

        except redis.ConnectionError as e:
            print(f"❌ Redis客户端连接失败: {e}")
            raise

    def get_trend_data(self) -> Dict[str, Any]:
        """从processed_data命名空间获取完整的趋势数据"""
        try:
            metadata_json = self.redis_client.get("processed_data:metadata")
            trending_json = self.redis_client.get("processed_data:trending_keywords")
            word_cloud_json = self.redis_client.get("processed_data:word_cloud")
            news_feed_json = self.redis_client.get("processed_data:news_feed")

            history_data = {}
            history_keys = self.redis_client.keys("processed_data:history_data:*")
            for key in history_keys:
                keyword = key.replace("processed_data:history_data:", "")
                history_json = self.redis_client.get(key)
                if history_json:
                    history_data[keyword] = json.loads(history_json)

            data = {
                "metadata": json.loads(metadata_json) if metadata_json else self._get_default_metadata(),
                "trending_keywords": json.loads(trending_json) if trending_json else [],
                "word_cloud": json.loads(word_cloud_json) if word_cloud_json else [],
                "history_data": history_data,
                "news_feed": json.loads(news_feed_json) if news_feed_json else []
            }

            print("✅ 成功从processed_data命名空间获取数据")
            return data

        except Exception as e:
            print(f"❌ 获取processed_data数据失败: {e}")
            return self.get_empty_data_structure()

    def _get_default_metadata(self) -> Dict[str, Any]:
        """返回默认的元数据"""
        return {
            "timestamp": "2025-01-20 00:00:00",
            "update_interval": 30,
            "data_version": "1.0"
        }

    def get_empty_data_structure(self) -> Dict[str, Any]:
        """返回空的数据结构"""
        return {
            "metadata": self._get_default_metadata(),
            "trending_keywords": [],
            "word_cloud": [],
            "history_data": {},
            "news_feed": []
        }

    def get_metadata(self) -> Dict[str, Any]:
        """获取元数据"""
        try:
            metadata_json = self.redis_client.get("processed_data:metadata")
            return json.loads(metadata_json) if metadata_json else self._get_default_metadata()
        except Exception as e:
            print(f"❌ 获取metadata失败: {e}")
            return self._get_default_metadata()

    def get_trending_keywords(self) -> List[Dict[str, Any]]:
        """获取热词数据"""
        try:
            trending_json = self.redis_client.get("processed_data:trending_keywords")
            return json.loads(trending_json) if trending_json else []
        except Exception as e:
            print(f"❌ 获取trending_keywords失败: {e}")
            return []

    def get_word_cloud(self) -> List[Dict[str, Any]]:
        """获取词云数据"""
        try:
            word_cloud_json = self.redis_client.get("processed_data:word_cloud")
            return json.loads(word_cloud_json) if word_cloud_json else []
        except Exception as e:
            print(f"❌ 获取word_cloud失败: {e}")
            return []

    def get_history_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取历史数据"""
        try:
            history_data = {}
            history_keys = self.redis_client.keys("processed_data:history_data:*")
            for key in history_keys:
                keyword = key.replace("processed_data:history_data:", "")
                history_json = self.redis_client.get(key)
                if history_json:
                    history_data[keyword] = json.loads(history_json)
            return history_data
        except Exception as e:
            print(f"❌ 获取history_data失败: {e}")
            return {}

    def get_news_feed(self) -> List[Dict[str, Any]]:
        """获取新闻数据"""
        try:
            news_feed_json = self.redis_client.get("processed_data:news_feed")
            return json.loads(news_feed_json) if news_feed_json else []
        except Exception as e:
            print(f"❌ 获取news_feed失败: {e}")
            return []

    def test_redis_connection(self) -> bool:
        """测试Redis连接"""
        try:
            self.redis_client.ping()
            print("✅ Redis客户端连接测试通过")
            return True
        except Exception as e:
            print(f"❌ Redis客户端连接测试失败: {e}")
            return False

    def test_data_retrieval(self) -> bool:
        """测试数据检索"""
        try:
            data = self.get_trend_data()

            print("\n📊 processed_data数据检索测试结果:")
            print(f"✅ 元数据: {data['metadata']}")
            print(f"✅ 热词数量: {len(data['trending_keywords'])}")
            print(f"✅ 词云词汇数量: {len(data['word_cloud'])}")
            print(f"✅ 历史数据关键词数量: {len(data['history_data'])}")
            print(f"✅ 新闻数量: {len(data['news_feed'])}")

            # 显示前3个热词
            if data['trending_keywords']:
                print("\n🔥 前3个热词:")
                for i, keyword in enumerate(data['trending_keywords'][:3]):
                    print(f"  {i + 1}. {keyword['keyword']} (+{keyword['growth_rate']}%)")

            # 显示前2条新闻
            if data['news_feed']:
                print("\n📰 前2条新闻:")
                for i, news in enumerate(data['news_feed'][:2]):
                    print(f"  {i + 1}. {news['title']}")
                    print(f"     来源: {news['source']}, 情绪: {news['sentiment']['positive']}%积极")

            return True

        except Exception as e:
            print(f"❌ 数据检索测试失败: {e}")
            return False

    def check_redis_info(self):
        """检查Redis服务器信息"""
        try:
            info = self.redis_client.info()
            print("\n🔧 Redis服务器信息:")
            print(f"✅ Redis版本: {info['redis_version']}")
            print(f"✅ 运行时间: {info['uptime_in_days']}天")
            print(f"✅ 内存使用: {info['used_memory_human']}")
            print(f"✅ 连接客户端: {info['connected_clients']}")

            # 检查键信息
            key_count = self.redis_client.dbsize()
            print(f"✅ 数据库键数量: {key_count}")

            # 显示processed_data键
            processed_data_keys = self.redis_client.keys("processed_data:*")
            print(f"✅ processed_data键数量: {len(processed_data_keys)}")

        except Exception as e:
            print(f"❌ 获取Redis信息失败: {e}")


def run_redis_test():
    """运行完整的Redis测试"""
    print("=" * 50)
    print("🧪 Redis客户端测试开始")
    print("=" * 50)

    try:
        # 创建Redis客户端实例
        client = RedisClient()

        # 检查Redis服务器信息
        client.check_redis_info()

        # 测试数据检索
        print("\n" + "=" * 30)
        print("📋 数据检索测试")
        print("=" * 30)

        success = client.test_data_retrieval()

        if success:
            print("\n🎉 所有测试通过！")
        else:
            print("\n❌ 部分测试失败")

        return success

    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        return False


# 独立测试脚本
if __name__ == "__main__":
    print("🚀 启动Redis数据测试...")

    # 运行测试
    success = run_redis_test()

    print("\n" + "=" * 50)
    if success:
        print("✅ Redis测试完成 - 系统就绪！")
    else:
        print("❌ Redis测试完成 - 发现问题，请检查配置")
    print("=" * 50)
