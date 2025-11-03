"""
Reddit 实时流式爬虫 - 真正的实时数据
使用 PRAW Stream API，延迟 < 1分钟
"""
import sys
import time
import praw
import prawcore
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import setup_logger
from utils.redis_client import RedisClient

logger = setup_logger('reddit_stream')


class RedditStreamCrawler:
    """
    Reddit 实时流式爬虫
    
    特点：
    - 真正实时（延迟 < 1分钟）
    - 持续监听，无需轮询
    - 适合关键词监控和热点追踪
    """
    
    def __init__(self, config: dict, redis_client: RedisClient):
        """
        初始化实时流式爬虫
        
        Args:
            config: Reddit 配置字典
            redis_client: Redis 客户端实例
        """
        self.config = config
        self.redis_client = redis_client
        
        try:
            self.reddit = praw.Reddit(
                client_id=config['client_id'],
                client_secret=config['client_secret'],
                user_agent=config['user_agent']
            )
            logger.info("Reddit Stream API 初始化成功")
        except Exception as e:
            logger.error(f"Reddit API 初始化失败: {e}")
            raise
        
        self.subreddits = config.get('subreddits', ['investing', 'finance'])
        self.keywords = config.get('search_keywords', [])
        self.post_filters = config.get('post_filters', {})
        
        # 已处理的帖子ID（内存缓存，避免重复处理）
        self.processed_ids: Set[str] = set()
        self.max_cache_size = 10000
    
    def stream_submissions(self, duration_seconds: int = None, stop_flag: callable = None):
        """
        实时流式监听新帖子（真正的实时，延迟 < 1分钟）
        
        Args:
            duration_seconds: 运行时长（秒），None=无限运行直到手动停止
            stop_flag: 停止标志回调函数，返回 True 时停止监听
        
        Returns:
            dict: 统计信息
        """
        stats = {'posts': 0, 'comments': 0, 'errors': 0}
        start_time = time.time()
        
        # 组合所有要监听的子版块
        subreddit_str = '+'.join(self.subreddits)
        logger.info(f"🔴 开始实时流式监听: r/{subreddit_str}")
        
        if duration_seconds:
            logger.info(f"⏱️  运行时长: {duration_seconds}秒 ({duration_seconds//60:.1f}分钟)")
        else:
            logger.info(f"⏱️  运行模式: 持续监听（按 Ctrl+C 停止）")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_str)
            
            # 🔥 核心：stream.submissions() 实时监听新帖子
            for submission in subreddit.stream.submissions(skip_existing=True):
                # 🔥 检查外部停止信号
                if stop_flag and stop_flag():
                    logger.info(f"🛑 收到停止信号，退出监听")
                    break
                
                # 检查是否超时（如果设置了时长限制）
                if duration_seconds and time.time() - start_time > duration_seconds:
                    logger.info(f"⏰ 达到运行时长限制，停止监听")
                    break
                
                try:
                    # 去重检查（内存 + Redis）
                    if submission.id in self.processed_ids:
                        continue
                    if self._is_post_processed(submission.id):
                        self.processed_ids.add(submission.id)
                        continue
                    
                    # 关键词过滤（可选）
                    if self.keywords and not self._contains_keywords(submission):
                        continue
                    
                    # 提取数据
                    post_data = self._extract_post_data(submission)
                    if not post_data:
                        continue
                    
                    # 应用过滤条件
                    if not self._apply_post_filters(post_data):
                        continue
                    
                    # 保存到 Redis
                    if self.redis_client.push_data(post_data):
                        stats['posts'] += 1
                        self.processed_ids.add(submission.id)
                        self._mark_post_processed(submission.id)
                        
                        # 🔥 用不同前缀区分实时流和批量爬虫
                        logger.info(
                            f"🔴 [实时流] r/{submission.subreddit.display_name} | "
                            f"{submission.title[:45]}... | "
                            f"👍{submission.score}"
                        )
                        
                        # 可选：立即抓取评论
                        # comments_count = self._crawl_comments(submission)
                        # stats['comments'] += comments_count
                    
                    # 清理缓存（防止内存溢出）
                    if len(self.processed_ids) > self.max_cache_size:
                        self.processed_ids.clear()
                        logger.info("🧹 清理内存缓存")
                
                except prawcore.ResponseException as e:
                    logger.error(f"Reddit API 错误: {e}")
                    stats['errors'] += 1
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"处理帖子时出错: {e}")
                    stats['errors'] += 1
        
        except KeyboardInterrupt:
            logger.info("⚠️  用户中断监听")
        except Exception as e:
            logger.error(f"流式监听失败: {e}")
            stats['errors'] += 1
        
        elapsed = time.time() - start_time
        hours = elapsed / 3600
        logger.info(
            f"📊 实时监听完成 - "
            f"运行时长: {elapsed:.0f}秒 ({hours:.2f}小时) | "
            f"新帖: {stats['posts']} | "
            f"错误: {stats['errors']}"
        )
        return stats
    
    def stream_comments(self, duration_seconds: int = 600):
        """
        实时流式监听新评论
        
        Args:
            duration_seconds: 运行时长（秒）
        
        Returns:
            dict: 统计信息
        """
        stats = {'comments': 0, 'errors': 0}
        start_time = time.time()
        
        subreddit_str = '+'.join(self.subreddits)
        logger.info(f"💬 开始实时流式监听评论: r/{subreddit_str}")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_str)
            
            # 🔥 实时监听新评论
            for comment in subreddit.stream.comments(skip_existing=True):
                if time.time() - start_time > duration_seconds:
                    break
                
                try:
                    # 去重检查
                    if comment.id in self.processed_ids:
                        continue
                    if self._is_comment_processed(comment.id):
                        self.processed_ids.add(comment.id)
                        continue
                    
                    # 关键词过滤
                    if self.keywords and not self._comment_contains_keywords(comment):
                        continue
                    
                    # 提取评论数据
                    comment_data = self._extract_comment_data(comment)
                    if not comment_data:
                        continue
                    
                    # 验证有效性
                    if not self._is_valid_comment(comment_data):
                        continue
                    
                    # 保存
                    if self.redis_client.push_data(comment_data):
                        stats['comments'] += 1
                        self.processed_ids.add(comment.id)
                        self._mark_comment_processed(comment.id)
                        
                        logger.info(
                            f"💬 实时评论: r/{comment.subreddit.display_name} | "
                            f"{comment.body[:50]}..."
                        )
                    
                    # 清理缓存
                    if len(self.processed_ids) > self.max_cache_size:
                        self.processed_ids.clear()
                
                except Exception as e:
                    logger.error(f"处理评论时出错: {e}")
                    stats['errors'] += 1
        
        except KeyboardInterrupt:
            logger.info("⚠️  用户中断监听")
        except Exception as e:
            logger.error(f"流式监听评论失败: {e}")
            stats['errors'] += 1
        
        logger.info(f"📊 评论监听完成 - 新评论: {stats['comments']}")
        return stats
    
    def _contains_keywords(self, submission) -> bool:
        """检查帖子是否包含关键词"""
        if not self.keywords:
            return True
        
        text = f"{submission.title} {submission.selftext}".lower()
        return any(kw.lower() in text for kw in self.keywords)
    
    def _comment_contains_keywords(self, comment) -> bool:
        """检查评论是否包含关键词"""
        if not self.keywords:
            return True
        
        text = comment.body.lower()
        return any(kw.lower() in text for kw in self.keywords)
    
    def _is_post_processed(self, post_id: str) -> bool:
        """检查帖子是否已处理"""
        try:
            key = f"reddit:post:{post_id}"
            return self.redis_client.client.exists(key) > 0
        except:
            return False
    
    def _mark_post_processed(self, post_id: str):
        """标记帖子为已处理"""
        try:
            key = f"reddit:post:{post_id}"
            self.redis_client.client.setex(key, 604800, "1")  # 7天
        except:
            pass
    
    def _is_comment_processed(self, comment_id: str) -> bool:
        """检查评论是否已处理"""
        try:
            key = f"reddit:comment:{comment_id}"
            return self.redis_client.client.exists(key) > 0
        except:
            return False
    
    def _mark_comment_processed(self, comment_id: str):
        """标记评论为已处理"""
        try:
            key = f"reddit:comment:{comment_id}"
            self.redis_client.client.setex(key, 604800, "1")  # 7天
        except:
            pass
    
    def _is_valid_comment(self, comment_data: Dict) -> bool:
        """验证评论有效性"""
        text = comment_data.get('text', '').strip()
        if text in ['[deleted]', '[removed]', '']:
            return False
        if len(text) < 3:
            return False
        return True
    
    def _apply_post_filters(self, post_data: Dict) -> bool:
        """应用帖子过滤条件"""
        min_upvotes = self.post_filters.get('min_upvotes', 0)
        min_comments = self.post_filters.get('min_comments', 0)
        
        if post_data['score'] < min_upvotes:
            return False
        if post_data['num_comments'] < min_comments:
            return False
        return True
    
    def _extract_post_data(self, submission) -> Dict[str, Any]:
        """提取帖子数据"""
        try:
            text = submission.title
            if submission.selftext:
                text += "\n\n" + submission.selftext
            
            return {
                'text': text,
                'source': 'reddit_stream',
                'timestamp': int(submission.created_utc),
                'url': f"https://www.reddit.com{submission.permalink}",
                'subreddit': submission.subreddit.display_name,
                'post_id': submission.id,
                'author': str(submission.author) if submission.author else '[deleted]',
                'score': submission.score,
                'upvote_ratio': getattr(submission, 'upvote_ratio', 0),
                'num_comments': submission.num_comments,
                'is_self': submission.is_self,
                'title': submission.title,
                'selftext': submission.selftext if submission.selftext else ''
            }
        except Exception as e:
            logger.error(f"提取帖子数据失败: {e}")
            return None
    
    def _extract_comment_data(self, comment) -> Dict[str, Any]:
        """提取评论数据"""
        try:
            return {
                'text': comment.body,
                'source': 'reddit_stream_comment',
                'timestamp': int(comment.created_utc),
                'url': f"https://www.reddit.com{comment.permalink}",
                'subreddit': comment.subreddit.display_name,
                'comment_id': comment.id,
                'author': str(comment.author) if comment.author else '[deleted]',
                'score': comment.score,
                'parent_id': comment.parent_id,
                'link_id': comment.link_id
            }
        except Exception as e:
            logger.error(f"提取评论数据失败: {e}")
            return None


def main():
    """测试实时流式爬虫"""
    import yaml
    import signal
    import sys
    
    # 确保在正确的目录
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    redis_client = RedisClient(**config['redis'])
    crawler = RedditStreamCrawler(config['reddit'], redis_client)
    
    # 🔥 设置停止标志
    stop_requested = False
    
    def signal_handler(sig, frame):
        nonlocal stop_requested
        logger.info("\n⚠️  收到停止信号 (Ctrl+C)")
        stop_requested = True
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # 🔥 无限运行直到按 Ctrl+C
    logger.info("🔴 启动实时监听（持续运行，按 Ctrl+C 停止）...")
    try:
        stats = crawler.stream_submissions(
            duration_seconds=None,  # None = 无限运行
            stop_flag=lambda: stop_requested  # 🔥 检查停止标志
        )
        logger.info(f"✅ 完成: {stats}")
    except Exception as e:
        logger.error(f"❌ 运行出错: {e}")
    finally:
        redis_client.close()
        logger.info("✅ 监听已停止")


if __name__ == '__main__':
    main()
