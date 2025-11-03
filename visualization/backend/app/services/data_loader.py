# backend/visualization_app/services/data_loader.py
import json
import redis
import os
import sys

# 使用相对导入
from ..config import settings
from .mock_data_generator import MockDataGenerator
from .scheduler import get_scheduler


class DataLoader:
    """数据加载器 - 支持单次加载和定时发布两种模式"""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,  # 使用配置的DB（DB2）
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.generator = MockDataGenerator()
        self.scheduler = get_scheduler()

    def load_mock_data_to_redis(self):
        """单次模式：将模拟数据存储到发布者命名空间"""
        try:
            mock_data = self.generator.generate_complete_data()

            # 使用新的发布者方法
            success = self.redis_client.update_publisher_data(mock_data)

            if success:
                print("✅ 模拟数据已成功加载到发布者命名空间!")
                print(f"📊 数据版本: {mock_data['metadata']['data_version']}")
                print(f"🔑 发布者结构: processed_data_publisher:*")
                print(f"🔔 订阅者结构: processed_data:* (通过发布订阅同步)")
                print(f"📈 热词数量: {len(mock_data['trending_keywords'])}")
                print(f"📰 新闻数量: {len(mock_data['news_feed'])}")

                # 立即同步一次
                self.redis_client.sync_to_processed_data()
                print("✅ 数据已同步到订阅者命名空间")

            return success

        except Exception as e:
            print(f"❌ 加载数据到Redis失败: {e}")
            return False

    def start_pipeline_mode(self):
        """启动管道模式：定时发布数据"""
        print("🚀 启动数据管道模式...")
        return self.scheduler.start(initial_push=True)

    def stop_pipeline_mode(self):
        """停止管道模式"""
        return self.scheduler.stop()

    def get_pipeline_status(self):
        """获取管道模式状态"""
        return self.scheduler.get_status()

    def trigger_manual_update(self):
        """手动触发数据更新"""
        return self.scheduler.trigger_manual_update()

    def get_redis_info(self):
        """获取Redis信息"""
        try:
            # 检查主要键是否存在
            main_keys = [
                "processed_data:metadata",
                "processed_data:trending_keywords",
                "processed_data:word_cloud",
                "processed_data:news_feed"
            ]
            existing_keys = []

            for key in main_keys:
                if self.redis_client.exists(key):
                    existing_keys.append(key)

            # 检查history_data子键
            history_keys = []
            all_keys = self.redis_client.keys("processed_data:history_data:*")
            for key in all_keys:
                if self.redis_client.exists(key):
                    history_keys.append(key)

            if existing_keys:
                print("📊 Redis DB0中的数据信息:")
                print(f"  processed_data子键: {[key.replace('processed_data:', '') for key in existing_keys]}")
                print(f"  history_data子键数量: {len(history_keys)}")

                # 显示metadata信息
                if "processed_data:metadata" in existing_keys:
                    metadata_json = self.redis_client.get("processed_data:metadata")
                    if metadata_json:
                        metadata = json.loads(metadata_json)
                        print(f"  最后更新时间: {metadata['timestamp']}")
                        print(f"  更新间隔: {metadata['update_interval']}分钟")
                        print(f"  数据版本: {metadata['data_version']}")

                # 显示热词数量
                if "processed_data:trending_keywords" in existing_keys:
                    trending_json = self.redis_client.get("processed_data:trending_keywords")
                    if trending_json:
                        trending = json.loads(trending_json)
                        print(f"  热词数量: {len(trending)}")

                # 显示新闻数量
                if "processed_data:news_feed" in existing_keys:
                    news_json = self.redis_client.get("processed_data:news_feed")
                    if news_json:
                        news = json.loads(news_json)
                        print(f"  新闻数量: {len(news)}")
            else:
                print("⚠️ Redis DB0中没有找到数据")
        except Exception as e:
            print(f"❌ 获取Redis信息失败: {e}")


# 使用示例
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='数据加载器')
    parser.add_argument('--mode', choices=['once', 'pipeline'], default='once',
                        help='运行模式: once(单次) 或 pipeline(管道模式)')

    args = parser.parse_args()

    loader = DataLoader()

    if args.mode == 'once':
        # 单次模式
        print("🎯 单次数据加载模式")
        loader.load_mock_data_to_redis()
        loader.get_redis_info()
    else:
        # 管道模式
        print("🔄 数据管道模式")
        loader.start_pipeline_mode()

        try:
            # 保持程序运行
            import time

            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 停止数据管道...")
            loader.stop_pipeline_mode()