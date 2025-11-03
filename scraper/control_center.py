"""
数据抓取控制中心
统一管理所有爬虫的启动、停止和配置
"""
import yaml
import sys
import time
import argparse
import redis
import json
from datetime import datetime, timedelta
from typing import Dict, List
from utils.logger import setup_logger
from utils.redis_client import RedisClient
from utils.data_exporter import DataExporter
from crawlers.reddit_crawler import RedditCrawler
from crawlers.rss_crawler import RSSCrawler
from crawlers.newsapi_crawler import NewsAPICrawler
from crawlers.stocktwits_crawler import StockTwitsCrawler
from crawlers.alphavantage_crawler import AlphaVantageCrawler  # ✅ 新增

logger = setup_logger('control_center')


class CrawlerControlCenter:
    """爬虫控制中心"""
    
    def __init__(self, config_file='config.yaml'):
        """
        初始化控制中心
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.redis_client = None
        self.crawlers = {}
        self.statistics = {
            'reddit': {'posts': 0, 'comments': 0, 'errors': 0},
            'newsapi': {'articles': 0, 'errors': 0},
            'rss': {'articles': 0, 'errors': 0},
            'stocktwits': {'messages': 0, 'errors': 0},
            'alphavantage': {'items': 0, 'errors': 0}  # ✅ 新增
        }
        
        # 记录上次运行时间（用于独立间隔控制）
        self.last_run_times = {
            'reddit': 0,
            'newsapi': 0,
            'rss': 0,
            'stocktwits': 0,
            'twitter': 0,
            'alphavantage': 0
        }
        
        logger.info("=" * 60)
        logger.info("控制中心初始化")
        logger.info("=" * 60)
        
        # 初始化 Redis 连接
        self._init_redis()
        
        # 初始化爬虫
        self._init_crawlers()
    
    def _load_config(self) -> dict:
        """
        加载配置文件
        
        Returns:
            dict: 配置字典
        """
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"配置文件加载成功: {self.config_file}")
            return config
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {self.config_file}")
            logger.error("请创建 config.yaml（可参考 README 配置说明）")
            sys.exit(1)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            sys.exit(1)
    
    def _init_redis(self):
        """初始化 Redis 连接"""
        try:
            redis_config = self.config.get('redis', {})
            self.redis_client = RedisClient(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                password=redis_config.get('password'),
                queue_name=redis_config.get('queue_name', 'financial_data'),
                storage_config=redis_config.get('storage_optimization', {}),
                source_quotas=redis_config.get('source_quotas', {}),
            )
            logger.info("✓ Redis 连接成功")
        except Exception as e:
            logger.error(f"✗ Redis 连接失败: {e}")
            sys.exit(1)
    
    def _init_crawlers(self):
        """初始化所有爬虫"""
        logger.info("\n" + "=" * 60)
        logger.info("初始化爬虫模块")
        logger.info("=" * 60)

        def is_enabled(section_name: str, default_if_present: bool = False) -> bool:
            conf = self.config.get(section_name, None)
            if conf is None:
                return False
            if 'enabled' in conf:
                return bool(conf.get('enabled'))
            # 如果配置段存在但未提供 enabled：reddit 默认启用，newsapi 默认禁用，其它遵循 default_if_present
            if section_name == 'reddit':
                return True
            if section_name == 'newsapi':
                return False
            return default_if_present
        
        # Reddit
        if is_enabled('reddit'):
            try:
                self.crawlers['reddit'] = RedditCrawler(
                    self.config.get('reddit', {}),
                    self.redis_client
                )
                logger.info("✓ Reddit 爬虫初始化成功")
            except Exception as e:
                logger.error(f"✗ Reddit 爬虫初始化失败: {e}")
        else:
            logger.info("○ Reddit 爬虫已禁用")
        
        # NewsAPI
        if is_enabled('newsapi'):
            try:
                self.crawlers['newsapi'] = NewsAPICrawler(
                    self.config.get('newsapi', {}),
                    self.redis_client
                )
                logger.info("✓ NewsAPI 爬虫初始化成功")
            except Exception as e:
                logger.error(f"✗ NewsAPI 爬虫初始化失败: {e}")
        else:
            logger.info("○ NewsAPI 爬虫已禁用")
        
        # RSS
        if is_enabled('rss', default_if_present=False):
            try:
                self.crawlers['rss'] = RSSCrawler(
                    self.config.get('rss', {}),
                    self.redis_client
                )
                logger.info("✓ RSS 爬虫初始化成功")
            except Exception as e:
                logger.error(f"✗ RSS 爬虫初始化失败: {e}")
        else:
            logger.info("○ RSS 爬虫已禁用")
        
        # StockTwits
        if is_enabled('stocktwits', default_if_present=False):
            try:
                self.crawlers['stocktwits'] = StockTwitsCrawler(
                    self.config.get('stocktwits', {}),
                    self.redis_client
                )
                logger.info("✓ StockTwits 爬虫初始化成功")
            except Exception as e:
                logger.error(f"✗ StockTwits 爬虫初始化失败: {e}")
        else:
            logger.info("○ StockTwits 爬虫已禁用")
        
        # Alpha Vantage
        if is_enabled('alphavantage', default_if_present=False):
            try:
                self.crawlers['alphavantage'] = AlphaVantageCrawler(
                    self.config.get('alphavantage', {}),
                    self.redis_client
                )
                logger.info("✓ Alpha Vantage 爬虫初始化成功")
            except Exception as e:
                logger.error(f"✗ Alpha Vantage 爬虫初始化失败: {e}")
        else:
            logger.info("○ Alpha Vantage 爬虫已禁用")
        
        logger.info(f"\n已启用爬虫数量: {len(self.crawlers)}/5")
    
    def run_crawler(self, name: str) -> Dict:
        """
        运行单个爬虫
        
        Args:
            name: 爬虫名称 (reddit/newsapi/rss/stocktwits/alphavantage)
        
        Returns:
            dict: 统计信息
        """
        if name not in self.crawlers:
            logger.warning(f"爬虫 {name} 未启用或不存在")
            return {}
        
        logger.info("\n" + "=" * 60)
        logger.info(f"运行 {name.upper()} 爬虫")
        logger.info("=" * 60)
        
        try:
            stats = self.crawlers[name].crawl()
            
            if name == 'reddit':
                self.statistics['reddit']['posts'] += stats.get('posts', 0)
                self.statistics['reddit']['comments'] += stats.get('comments', 0)
                self.statistics['reddit']['errors'] += stats.get('errors', 0)
            elif name == 'newsapi':
                self.statistics['newsapi']['articles'] += stats.get('articles', 0)
                self.statistics['newsapi']['errors'] += stats.get('errors', 0)
            elif name == 'rss':
                self.statistics['rss']['articles'] += stats.get('articles', 0)
                self.statistics['rss']['errors'] += stats.get('errors', 0)
            elif name == 'stocktwits':
                self.statistics['stocktwits']['messages'] += stats.get('messages', 0)
                self.statistics['stocktwits']['errors'] += stats.get('errors', 0)
            elif name == 'alphavantage':
                self.statistics['alphavantage']['items'] += stats.get('items', 0)
                self.statistics['alphavantage']['errors'] += stats.get('errors', 0)
            
            return stats
        except Exception as e:
            logger.error(f"{name} 爬虫运行失败: {e}")
            self.statistics[name]['errors'] += 1
            return {'errors': 1}
    
    def run_all_crawlers(self):
        """运行所有启用的爬虫（支持独立间隔控制）"""
        logger.info("\n" + "=" * 60)
        logger.info(f"开始执行抓取任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        current_time = time.time()
        crawler_control = self.config.get('crawler_control', {})
        individual_intervals = crawler_control.get('individual_intervals', {})
        
        for name in ['reddit', 'newsapi', 'rss', 'stocktwits', 'twitter', 'alphavantage']:
            # 检查是否启用了该爬虫
            if name not in self.crawlers:
                continue
            
            # 获取该爬虫的独立间隔
            crawler_interval = individual_intervals.get(name, 0)
            
            # 如果设置了独立间隔，检查是否到达运行时间
            if crawler_interval > 0:
                time_since_last_run = current_time - self.last_run_times[name]
                if time_since_last_run < crawler_interval:
                    logger.info(f"⏭️  {name.upper()} - 跳过（距上次运行 {time_since_last_run:.0f}秒，间隔 {crawler_interval}秒）")
                    continue
            
            # 运行爬虫
            self.run_crawler(name)
            self.last_run_times[name] = current_time
        
        # 数据导出（防止 Redis 内存占用过大）
        self._export_data()
        
        # 打印总体统计
        self._print_statistics()
        
        # 📢 注：不再在这里发送统一的通知，改为由各爬虫在完成后立即发送
        # 这样可以实现"每爬一次就清一次"的实时处理流程

    
    def _export_data(self):
        """根据阈值导出数据到文件"""
        try:
            data_cfg = self.config.get('data_management', {})
            redis_cfg = self.config.get('redis', {})

            # 使用 redis.storage_optimization.max_keep 作为保留上限
            max_keep = int((redis_cfg.get('storage_optimization') or {}).get('max_keep', 10000))

            auto_export = (data_cfg.get('auto_export') or {})
            queue_threshold = int(auto_export.get('queue_threshold', max_keep))
            memory_threshold_mb = int(auto_export.get('memory_threshold_mb', 0))

            logger.info("\n" + "=" * 60)
            logger.info("检查是否需要导出数据")
            logger.info("=" * 60)

            # 条件1：队列长度
            current_length = self.redis_client.get_queue_length()
            need_export = current_length > max(queue_threshold, max_keep)

            # 条件2：内存阈值
            if memory_threshold_mb > 0:
                mem = self.redis_client.get_memory_usage()
                if mem.get('used_memory_mb', 0) >= memory_threshold_mb:
                    logger.info(f"内存阈值触发：{mem.get('used_memory_mb',0):.2f}MB ≥ {memory_threshold_mb}MB")
                    need_export = True

            logger.info(f"当前 Redis 队列长度: {current_length}")

            if need_export:
                exporter = DataExporter(
                    self.redis_client,
                    export_dir=data_cfg.get('export_dir', 'data_exports'),
                )
                export_stats = exporter.export_and_trim(max_keep=max_keep)

                if export_stats.get('exported', 0) > 0:
                    logger.info(f"✓ 已导出 {export_stats['exported']} 条数据到 {export_stats['export_file']}")
                    logger.info(f"✓ Redis 队列已修剪至 {max_keep} 条")
            else:
                logger.info(f"○ 队列长度未超过阈值（queue:{queue_threshold} / keep:{max_keep}），跳过导出")
        except Exception as e:
            logger.error(f"✗ 数据导出失败: {e}")
    
    def _print_statistics(self):
        """打印统计信息"""
        logger.info("\n" + "=" * 60)
        logger.info("抓取任务统计")
        logger.info("=" * 60)
        
        total_items = 0
        total_errors = 0
        
        # Reddit
        reddit_total = self.statistics['reddit']['posts'] + self.statistics['reddit']['comments']
        total_items += reddit_total
        total_errors += self.statistics['reddit']['errors']
        logger.info(f"Reddit:      帖子 {self.statistics['reddit']['posts']}, "
                   f"评论 {self.statistics['reddit']['comments']}, "
                   f"错误 {self.statistics['reddit']['errors']}")
        
        # NewsAPI
        total_items += self.statistics['newsapi']['articles']
        total_errors += self.statistics['newsapi']['errors']
        logger.info(f"NewsAPI:     文章 {self.statistics['newsapi']['articles']}, "
                   f"错误 {self.statistics['newsapi']['errors']}")
        
        # RSS
        total_items += self.statistics['rss']['articles']
        total_errors += self.statistics['rss']['errors']
        logger.info(f"RSS:         文章 {self.statistics['rss']['articles']}, "
                   f"错误 {self.statistics['rss']['errors']}")
        
        # StockTwits
        total_items += self.statistics['stocktwits']['messages']
        total_errors += self.statistics['stocktwits']['errors']
        logger.info(f"StockTwits:  消息 {self.statistics['stocktwits']['messages']}, "
                   f"错误 {self.statistics['stocktwits']['errors']}")
        
        # Alpha Vantage
        total_items += self.statistics['alphavantage']['items']
        total_errors += self.statistics['alphavantage']['errors']
        logger.info(f"AlphaVantage: 数据 {self.statistics['alphavantage']['items']}, "
                   f"错误 {self.statistics['alphavantage']['errors']}")
        
        logger.info("-" * 60)
        logger.info(f"总计:        数据 {total_items}, 错误 {total_errors}")
        logger.info(f"队列长度:    {self.redis_client.get_queue_length()}")
        logger.info("=" * 60)
    
    def _clean_old_data(self, hours=24) -> dict:
        """
        清理超过指定小时数的旧数据
        
        Args:
            hours: 保留数据的小时数
            
        Returns:
            dict: 清理统计信息
        """
        redis_config = self.config.get('redis', {})
        host = redis_config.get('host', 'localhost')
        port = redis_config.get('port', 6379)
        db = redis_config.get('db', 0)
        queue_name = redis_config.get('queue', 'data_queue')
        
        try:
            r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            r.ping()
            
            # 计算截止时间
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_timestamp = int(cutoff_time.timestamp())
            
            total = r.llen(queue_name)
            removed = 0
            
            # 从队列尾部（最旧）开始检查
            while True:
                item = r.lindex(queue_name, -1)
                if not item:
                    break
                
                try:
                    data = json.loads(item)
                    item_timestamp = data.get('timestamp', 0)
                    
                    if item_timestamp < cutoff_timestamp:
                        r.rpop(queue_name)
                        removed += 1
                    else:
                        break
                except:
                    # 无法解析的数据，删除
                    r.rpop(queue_name)
                    removed += 1
            
            remaining = r.llen(queue_name)
            
            logger.info(f"✓ 清理完成: 删除 {removed} 条旧数据，保留 {remaining} 条")
            
            return {
                'removed': removed,
                'remaining': remaining
            }
            
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return {'removed': 0, 'remaining': 0, 'error': str(e)}
    
    def _send_completion_notification(self):
        """发送爬取完成通知（清理旧数据后）"""
        notification_config = self.config.get('redis', {}).get('notification', {})
        
        if not notification_config.get('enabled', False):
            return
        
        # 先清理超过 24 小时的旧数据
        logger.info("\n🧹 清理超过 24 小时的旧数据...")
        clean_result = self._clean_old_data()
        
        channel = notification_config.get('channel', 'crawler_complete')
        
        # 统计总数据量
        total_items = (
            self.statistics['reddit']['posts'] + 
            self.statistics['reddit']['comments'] +
            self.statistics['newsapi']['articles'] +
            self.statistics['rss']['articles'] +
            self.statistics['stocktwits']['messages'] +
            self.statistics['alphavantage']['items']
        )
        
        total_errors = sum(
            self.statistics[source]['errors'] 
            for source in ['reddit', 'newsapi', 'rss', 'stocktwits', 'alphavantage']
        )
        
        # 构建通知消息
        message = {
            'event': 'crawl_complete',
            'timestamp': datetime.now().isoformat(),
            'statistics': {
                'total_items': total_items,
                'total_errors': total_errors,
                'queue_length': self.redis_client.get_queue_length(),
                'by_source': {
                    'reddit': {
                        'posts': self.statistics['reddit']['posts'],
                        'comments': self.statistics['reddit']['comments'],
                        'errors': self.statistics['reddit']['errors']
                    },
                    'newsapi': {
                        'articles': self.statistics['newsapi']['articles'],
                        'errors': self.statistics['newsapi']['errors']
                    },
                    'rss': {
                        'articles': self.statistics['rss']['articles'],
                        'errors': self.statistics['rss']['errors']
                    },
                    'stocktwits': {
                        'messages': self.statistics['stocktwits']['messages'],
                        'errors': self.statistics['stocktwits']['errors']
                    },
                    'alphavantage': {
                        'items': self.statistics['alphavantage']['items'],
                        'errors': self.statistics['alphavantage']['errors']
                    }
                }
            }
        }
        
        # 发送通知
        self.redis_client.publish_notification(channel, message)
    
    def get_status(self) -> Dict:
        """
        获取控制中心状态
        
        Returns:
            dict: 状态信息
        """
        return {
            'enabled_crawlers': list(self.crawlers.keys()),
            'statistics': self.statistics,
            'redis_queue_length': self.redis_client.get_queue_length(),
            'timestamp': datetime.now().isoformat()
        }
    
    def close(self):
        """关闭所有连接"""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis 连接已关闭")


def main():
    """主函数 - 支持单次运行或循环模式"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='财经数据爬虫控制中心')
    parser.add_argument('--loop', action='store_true', help='循环运行模式')
    parser.add_argument('--interval', type=int, default=None, 
                        help='循环间隔（秒），默认使用配置文件中的 crawler_control.loop_interval')
    args = parser.parse_args()
    
    try:
        # 创建控制中心
        center = CrawlerControlCenter()
        
        if args.loop:
            # 获取循环间隔（优先使用命令行参数，其次使用配置文件）
            if args.interval is not None:
                interval = args.interval
            else:
                interval = center.config.get('crawler_control', {}).get('loop_interval', 300)
            
            # 循环模式
            logger.info("=" * 60)
            logger.info(f"启动循环模式 - 间隔: {interval} 秒 ({interval/60:.1f} 分钟)")
            
            # 显示各爬虫的独立间隔配置
            individual_intervals = center.config.get('crawler_control', {}).get('individual_intervals', {})
            if individual_intervals:
                logger.info("\n独立间隔控制:")
                for name, crawler_interval in individual_intervals.items():
                    if crawler_interval > 0 and name in center.crawlers:
                        logger.info(f"  {name:15s}: 每 {crawler_interval:4d} 秒 ({crawler_interval/60:.1f} 分钟)")
            
            logger.info("\n按 Ctrl+C 停止")
            logger.info("=" * 60)
            
            run_count = 0
            try:
                while True:
                    run_count += 1
                    logger.info(f"\n{'='*60}")
                    logger.info(f"第 {run_count} 次运行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"{'='*60}\n")
                    
                    # 运行所有爬虫
                    center.run_all_crawlers()
                    
                    # 计算下次运行时间
                    next_run = datetime.now() + timedelta(seconds=interval)
                    logger.info(f"\n{'='*60}")
                    logger.info(f"等待 {interval} 秒 ({interval/60:.1f} 分钟)")
                    logger.info(f"下次运行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"按 Ctrl+C 停止循环")
                    logger.info(f"{'='*60}\n")
                    
                    time.sleep(interval)
                    
            except KeyboardInterrupt:
                logger.info("\n\n" + "="*60)
                logger.info("收到停止信号 (Ctrl+C)")
                logger.info(f"总共运行了 {run_count} 次")
                logger.info("="*60)
        else:
            # 单次运行模式
            center.run_all_crawlers()
        
        # 关闭连接
        center.close()
        
    except KeyboardInterrupt:
        logger.info("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
