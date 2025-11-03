"""
Alpha Vantage 爬虫模块
抓取股票价格、技术指标、财务数据
API 文档: https://www.alphavantage.co/documentation/
免费套餐: 25 次/天 (推荐配置)
"""
import time
import requests
import yaml
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from utils.logger import setup_logger
from utils.redis_client import RedisClient

logger = setup_logger('alphavantage_crawler')


class AlphaVantageCrawler:
    """Alpha Vantage 爬虫类"""
    
    def __init__(self, config: dict, redis_client: RedisClient):
        """
        初始化 Alpha Vantage 爬虫
        
        Args:
            config: Alpha Vantage 配置字典
            redis_client: Redis 客户端实例
        """
        self.config = config
        self.redis_client = redis_client
        self.enabled = config.get('enabled', False)
        self.api_key = config.get('api_key', '')
        self.base_url = 'https://www.alphavantage.co/query'
        
        # 读取配置
        self.symbols = config.get('symbols', ['AAPL', 'MSFT', 'GOOGL'])
        self.data_types = config.get('data_types', ['quote', 'news'])
        
        # 速率限制配置
        self.rate_limits = config.get('rate_limits', {})
        self.max_requests_per_day = self.rate_limits.get('max_requests_per_day', 25)
        self.requests_per_run = self.rate_limits.get('requests_per_run', 5)
        self.delay_between_requests = self.rate_limits.get('delay_between_requests', 12)
        
        if not self.enabled:
            logger.info("Alpha Vantage 爬虫已禁用")
            return
        
        if not self.api_key or self.api_key == 'YOUR_API_KEY_HERE':
            logger.warning("Alpha Vantage 未配置 API Key")
            self.enabled = False
            return
        
        logger.info(f"✓ Alpha Vantage 爬虫初始化成功，监控股票: {', '.join(self.symbols[:3])}...")
    
    def crawl(self) -> Dict[str, int]:
        """
        执行抓取任务
        
        Returns:
            dict: 抓取统计信息 {'items': 数量, 'errors': 数量}
        """
        stats = {'items': 0, 'errors': 0}
        
        if not self.enabled:
            logger.warning("Alpha Vantage 爬虫未启用，跳过")
            return stats
        
        # 检查每日配额
        if not self._check_daily_quota():
            logger.warning("⚠️ 今日配额已用完，跳过抓取")
            return stats
        
        logger.info("开始抓取 Alpha Vantage 数据...")
        
        # 限制处理的股票数量（避免超出配额）
        symbols_to_process = self.symbols[:self.requests_per_run]
        requests_used = 0
        
        for symbol in symbols_to_process:
            try:
                logger.info(f"正在抓取股票: {symbol}")
                
                # 抓取不同类型的数据
                for data_type in self.data_types:
                    try:
                        if data_type == 'quote':
                            # 实时报价
                            data = self._fetch_global_quote(symbol)
                            if data:
                                stats['items'] += 1
                                requests_used += 1
                        
                        elif data_type == 'news':
                            # 新闻
                            news_items = self._fetch_news_sentiment(symbol)
                            stats['items'] += len(news_items)
                            requests_used += 1
                        
                        elif data_type == 'overview':
                            # 公司概况
                            data = self._fetch_company_overview(symbol)
                            if data:
                                stats['items'] += 1
                                requests_used += 1
                        
                        elif data_type == 'earnings':
                            # 财报数据
                            data = self._fetch_earnings(symbol)
                            if data:
                                stats['items'] += 1
                                requests_used += 1
                        
                        # API 限速：免费版 5 次/分钟
                        time.sleep(self.delay_between_requests)
                        
                    except Exception as e:
                        logger.error(f"  ✗ 抓取 {symbol} 的 {data_type} 数据失败: {e}")
                        stats['errors'] += 1
                
                logger.info(f"✓ 股票 {symbol} 抓取完成")
                
            except Exception as e:
                logger.error(f"抓取股票 {symbol} 时出错: {e}")
                stats['errors'] += 1
        
        # 更新配额
        self._update_quota(requests_used)
        
        logger.info(f"Alpha Vantage 抓取完成 - 数据: {stats['items']}, 错误: {stats['errors']}")
        logger.info(f"本次使用: {requests_used} 次, 今日累计: {self._get_current_day_usage()} 次")
        
        # 📢 立即发送通知给 Cleaner 进行清洗（如果爬取了数据）
        if stats['items'] > 0:
            self._send_crawl_notification(stats)
        
        return stats
    
    def _fetch_global_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        抓取实时报价 (GLOBAL_QUOTE)
        
        Args:
            symbol: 股票代码
        
        Returns:
            dict: 报价数据（统一格式）
        """
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查错误
            if 'Error Message' in data:
                logger.error(f"  ✗ API 错误: {data['Error Message']}")
                return None
            
            if 'Note' in data:
                logger.warning(f"  ⚠️ API 限速: {data['Note']}")
                return None
            
            quote = data.get('Global Quote', {})
            if not quote:
                logger.warning(f"  ⚠️ {symbol} 未返回报价数据")
                return None
            
            # ✅ 统一格式：只保留核心字段
            price = quote.get('05. price', 'N/A')
            change_percent = quote.get('10. change percent', 'N/A')
            volume = quote.get('06. volume', 'N/A')
            
            quote_data = {
                # 核心字段（必需）
                'text': f"${symbol} Stock Quote - Price: ${price}, Change: {change_percent}, Volume: {volume}",
                'source': 'alphavantage',
                'timestamp': int(datetime.now().timestamp()),
                'url': f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}',
                
                # Alpha Vantage 特有字段（可选，用于后续分析）
                'symbol': symbol,
                'price': price,
                'change_percent': change_percent,
                'volume': volume,
                'trading_day': quote.get('07. latest trading day', '')
            }
            
            # 推送到 Redis
            if self.redis_client.push_data(quote_data):
                logger.info(f"  ✓ 报价: ${price} ({change_percent})")
                return quote_data
            
            return None
            
        except Exception as e:
            logger.error(f"获取 {symbol} 报价失败: {e}")
            return None
    
    def _fetch_news_sentiment(self, symbol: str) -> List[Dict[str, Any]]:
        """
        抓取新闻 (NEWS_SENTIMENT)
        
        Args:
            symbol: 股票代码
        
        Returns:
            list: 新闻列表（统一格式）
        """
        try:
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': symbol,
                'apikey': self.api_key,
                'limit': 10  # 限制返回数量
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查错误
            if 'Error Message' in data:
                logger.error(f"  ✗ API 错误: {data['Error Message']}")
                return []
            
            if 'Note' in data:
                logger.warning(f"  ⚠️ API 限速: {data['Note']}")
                return []
            
            feed = data.get('feed', [])
            if not feed:
                logger.warning(f"  ⚠️ {symbol} 未返回新闻数据")
                return []
            
            news_items = []
            for article in feed[:10]:  # 只取前 10 条
                # ✅ 统一格式：text = 标题 + 摘要
                title = article.get('title', '')
                summary = article.get('summary', '')[:300]  # 限制摘要长度
                
                # 组合 text（类似 NewsAPI 格式）
                text = title
                if summary:
                    text += f"\n\n{summary}"
                
                news_data = {
                    # 核心字段（必需）
                    'text': text,
                    'source': 'alphavantage',
                    'timestamp': self._parse_time(article.get('time_published', '')),
                    'url': article.get('url', ''),
                    
                    # Alpha Vantage 特有字段（可选）
                    'symbol': symbol,
                    'title': title,
                    'summary': summary,
                    'source_domain': article.get('source_domain', ''),
                    'authors': ', '.join(article.get('authors', [])),
                    'published_at': article.get('time_published', '')
                }
                
                if self.redis_client.push_data(news_data):
                    news_items.append(news_data)
            
            logger.info(f"  ✓ 新闻: {len(news_items)} 条")
            return news_items
            
        except Exception as e:
            logger.error(f"获取 {symbol} 新闻失败: {e}")
            return []
    
    def _fetch_company_overview(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        抓取公司概况 (OVERVIEW)
        
        Args:
            symbol: 股票代码
        
        Returns:
            dict: 公司数据（统一格式）
        """
        try:
            params = {
                'function': 'OVERVIEW',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查错误
            if 'Error Message' in data:
                logger.error(f"  ✗ API 错误: {data['Error Message']}")
                return None
            
            if not data or 'Symbol' not in data:
                logger.warning(f"  ⚠️ {symbol} 未返回公司数据")
                return None
            
            # ✅ 统一格式：text = 公司简介
            name = data.get('Name', symbol)
            sector = data.get('Sector', 'N/A')
            industry = data.get('Industry', 'N/A')
            description = data.get('Description', '')[:500]  # 限制长度
            market_cap = data.get('MarketCapitalization', '0')
            
            text = f"{name} - {sector} / {industry}\n\n"
            text += f"Market Cap: ${int(market_cap):,}\n"
            if description:
                text += f"\n{description}"
            
            overview_data = {
                # 核心字段（必需）
                'text': text,
                'source': 'alphavantage',
                'timestamp': int(datetime.now().timestamp()),
                'url': f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}',
                
                # Alpha Vantage 特有字段（可选）
                'symbol': symbol,
                'name': name,
                'sector': sector,
                'industry': industry,
                'market_cap': market_cap,
                'description': description
            }
            
            if self.redis_client.push_data(overview_data):
                logger.info(f"  ✓ 公司概况: {name} (市值: ${int(market_cap):,})")
                return overview_data
            
            return None
            
        except Exception as e:
            logger.error(f"获取 {symbol} 公司概况失败: {e}")
            return None
    
    def _fetch_earnings(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        抓取财报数据 (EARNINGS)
        
        Args:
            symbol: 股票代码
        
        Returns:
            dict: 财报数据（统一格式）
        """
        try:
            params = {
                'function': 'EARNINGS',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查错误
            if 'Error Message' in data:
                logger.error(f"  ✗ API 错误: {data['Error Message']}")
                return None
            
            quarterly = data.get('quarterlyEarnings', [])
            if not quarterly:
                logger.warning(f"  ⚠️ {symbol} 未返回财报数据")
                return None
            
            # 取最新一期财报
            latest = quarterly[0]
            
            # ✅ 统一格式：text = 财报摘要
            fiscal_date = latest.get('fiscalDateEnding', '')
            reported_eps = latest.get('reportedEPS', 'N/A')
            estimated_eps = latest.get('estimatedEPS', 'N/A')
            surprise_pct = latest.get('surprisePercentage', 'N/A')
            
            text = f"${symbol} Earnings Report ({fiscal_date})\n\n"
            text += f"Reported EPS: ${reported_eps}\n"
            text += f"Estimated EPS: ${estimated_eps}\n"
            text += f"Surprise: {surprise_pct}%"
            
            earnings_data = {
                # 核心字段（必需）
                'text': text,
                'source': 'alphavantage',
                'timestamp': int(datetime.now().timestamp()),
                'url': f'https://www.alphavantage.co/query?function=EARNINGS&symbol={symbol}',
                
                # Alpha Vantage 特有字段（可选）
                'symbol': symbol,
                'fiscal_date_ending': fiscal_date,
                'reported_eps': reported_eps,
                'estimated_eps': estimated_eps,
                'surprise_percent': surprise_pct
            }
            
            if self.redis_client.push_data(earnings_data):
                logger.info(f"  ✓ 财报: EPS ${reported_eps} (惊喜: {surprise_pct}%)")
                return earnings_data
            
            return None
            
        except Exception as e:
            logger.error(f"获取 {symbol} 财报失败: {e}")
            return None
    
    def _parse_time(self, time_str: str) -> int:
        """
        解析时间字符串为 Unix 时间戳
        
        Args:
            time_str: 时间字符串 (格式: 20231020T153045)
        
        Returns:
            int: Unix 时间戳
        """
        try:
            dt = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
            return int(dt.timestamp())
        except:
            return int(datetime.now().timestamp())
    
    def _check_daily_quota(self) -> bool:
        """检查每日配额是否可用"""
        current_usage = self._get_current_day_usage()
        
        # 检查是否需要重置计数器
        self._reset_counter_if_needed()
        
        if current_usage >= self.max_requests_per_day:
            logger.warning(f"⚠️ 今日配额已用完: {current_usage}/{self.max_requests_per_day}")
            return False
        
        remaining = self.max_requests_per_day - current_usage
        logger.info(f"✓ 今日配额检查通过: 剩余 {remaining}/{self.max_requests_per_day}")
        return True
    
    def _get_current_day_usage(self) -> int:
        """获取今日已使用的请求数量"""
        return self.rate_limits.get('current_day_requests', 0)
    
    def _update_quota(self, requests_used: int):
        """更新配额计数"""
        current = self.rate_limits.get('current_day_requests', 0)
        new_total = current + requests_used
        
        # 更新配置文件中的计数器
        self._save_quota_to_config(new_total)
        
        logger.info(f"✓ 配额已更新: {current} → {new_total}")
    
    def _reset_counter_if_needed(self):
        """检查并重置每日计数器"""
        last_reset = self.rate_limits.get('last_reset_date')
        today = str(date.today())
        
        if last_reset != today:
            logger.info(f"🔄 重置每日计数器: {last_reset} → {today}")
            self.rate_limits['current_day_requests'] = 0
            self.rate_limits['last_reset_date'] = today
            self._save_quota_to_config(0)
    
    def _save_quota_to_config(self, new_total: int):
        """将配额计数保存到 config.yaml"""
        try:
            import yaml
            
            # 读取配置
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 更新计数
            if 'alphavantage' not in config:
                config['alphavantage'] = {}
            if 'rate_limits' not in config['alphavantage']:
                config['alphavantage']['rate_limits'] = {}
            
            config['alphavantage']['rate_limits']['current_day_requests'] = new_total
            config['alphavantage']['rate_limits']['last_reset_date'] = str(date.today())
            
            # 写回配置
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
        except Exception as e:
            logger.error(f"保存配额失败: {e}")
    
    def _send_crawl_notification(self, stats: Dict[str, int]):
        """
        发送爬取完成通知给 Cleaner（每爬一次就发一次，不等待整轮完成）
        
        Args:
            stats: 爬取统计信息
        """
        try:
            message = {
                'event': 'alphavantage_crawl_complete',
                'timestamp': datetime.now().isoformat(),
                'source': 'alphavantage',
                'statistics': {
                    'items': stats['items'],
                    'errors': stats['errors'],
                    'total_items': stats['items']
                }
            }
            
            # 使用 redis_client 发送通知
            channel = 'crawler_complete'  # 与 cleaner 配置的频道一致
            self.redis_client.publish_notification(channel, message)
            
            logger.info(f"📢 AlphaVantage 爬取完成通知已发送 (数据: {stats['items']})")
            
        except Exception as e:
            logger.error(f"发送 AlphaVantage 爬取通知失败: {e}")


def main():
    """测试函数"""
    import yaml
    
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化 Redis 客户端
    redis_client = RedisClient(**config['redis'])
    
    # 初始化并运行爬虫
    crawler = AlphaVantageCrawler(config.get('alphavantage', {}), redis_client)
    stats = crawler.crawl()
    
    print(f"抓取完成: {stats}")
    
    # 关闭连接
    redis_client.close()


if __name__ == '__main__':
    main()