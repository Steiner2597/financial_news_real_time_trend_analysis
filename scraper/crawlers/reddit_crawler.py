"""
Reddit 爬虫模块 - 优化版（优先爬最新内容）
抓取财经相关子版块的帖子和评论
"""
import time
import praw
import prawcore
from datetime import datetime
from typing import List, Dict, Any
from utils.logger import setup_logger
from utils.redis_client import RedisClient

logger = setup_logger('reddit_crawler')


class RedditCrawler:
    """Reddit 爬虫类（已优化实时性）"""
    
    def __init__(self, config: dict, redis_client: RedisClient):
        """
        初始化 Reddit 爬虫
        
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
            logger.info("Reddit API 初始化成功")
        except Exception as e:
            logger.error(f"Reddit API 初始化失败: {e}")
            raise
        
        self.subreddits = config.get('subreddits', ['investing', 'finance'])
        self.posts_limit = config.get('posts_limit', 50)
        self.comments_limit = config.get('comments_limit', 30)
        self.post_filters = config.get('post_filters', {})
    
    def crawl(self) -> Dict[str, int]:
        """
        执行抓取任务（已优化实时性）
        
        Returns:
            dict: 抓取统计信息 {'posts': 数量, 'comments': 数量, 'errors': 数量}
        """
        stats = {'posts': 0, 'comments': 0, 'errors': 0}
        
        logger.info("开始抓取 Reddit 数据（实时优先）...")
        
        # 1. 优先抓取关键词搜索（最新内容）
        if self.config.get('search_enabled', False):
            search_stats = self._crawl_search_keywords()
            stats['posts'] += search_stats.get('posts', 0)
            stats['comments'] += search_stats.get('comments', 0)
            stats['errors'] += search_stats.get('errors', 0)
        
        # 2. 抓取子版块最新内容
        for subreddit_name in self.subreddits:
            sub_posts = 0
            sub_comments = 0
            
            try:
                logger.info(f"正在抓取子版块: r/{subreddit_name}（最新内容）")
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # 抓取新帖子
                post_index = 0
                for submission in subreddit.new(limit=self.posts_limit):
                    post_index += 1
                    
                    # 2.1 去重检查（Redis）
                    if self._is_post_processed(submission.id):
                        logger.debug(f"  ⏭️ 跳过已抓取帖子: {submission.id}")
                        continue
                    
                    # 显示正在处理的帖子
                    logger.info(f"  [{post_index}/{self.posts_limit}] 抓取帖子: {submission.title[:60]}...")
                    
                    # 2.2 提取帖子信息
                    post_data = self._extract_post_data(submission, subreddit_name)
                    if not post_data:
                        continue
                    
                    # 2.3 应用过滤条件（关键优化！）
                    if not self._apply_post_filters(post_data):
                        continue
                    
                    # 2.4 保存到 Redis
                    if self.redis_client.push_data(post_data):
                        stats['posts'] += 1
                        sub_posts += 1
                        # 标记为已处理（7天有效期）
                        self._mark_post_processed(submission.id)
                        logger.debug(f"    ✓ 新帖保存 (ID: {submission.id}, upvotes: {post_data['score']})")
                    
                    # 2.5 抓取评论
                    logger.info(f"    → 正在抓取评论 (目标: {self.comments_limit} 条)...")
                    comments_count = self._crawl_comments(submission, subreddit_name)
                    stats['comments'] += comments_count
                    sub_comments += comments_count
                    logger.info(f"    ✓ 评论抓取完成: {comments_count} 条")
                    
                    # 避免请求过快
                    time.sleep(0.5)
                
                logger.info(
                    f"✓ 子版块 r/{subreddit_name} 抓取完成 - "
                    f"新帖: {sub_posts}, 评论: {sub_comments}"
                )
                
            except prawcore.ResponseException as e:
                if e.response.status_code == 429:
                    logger.warning(f"Reddit API 速率限制: {e}, 等待60秒后重试...")
                    time.sleep(60)
                else:
                    logger.error(f"Reddit API 响应错误 ({e.response.status_code}): {e}")
                stats['errors'] += 1
                
            except Exception as e:
                logger.error(f"抓取子版块 r/{subreddit_name} 时出错: {e}")
                stats['errors'] += 1
        
        logger.info(f"抓取完成 - 新帖: {stats['posts']}, 评论: {stats['comments']}, 错误: {stats['errors']}")
        return stats
    
    def _crawl_search_keywords(self) -> Dict[str, int]:
        """
        抓取关键词搜索（最新内容）
        
        Returns:
            dict: 搜索统计信息
        """
        stats = {'posts': 0, 'comments': 0, 'errors': 0}
        keywords = self.config.get('search_keywords', [])
        search_settings = self.config.get('search_settings', {})
        time_filter = search_settings.get('time_filter', 'day')
        sort = search_settings.get('sort', 'new')
        posts_per_kw = search_settings.get('posts_per_keyword', 15)
        
        logger.info(f"🔍 开始关键词实时监控（{len(keywords)} 个关键词，{time_filter}内最新内容）")
        
        for kw in keywords:
            try:
                logger.info(f"  ├─ 搜索关键词: '{kw}' (time={time_filter}, sort={sort})")
                submissions = self.reddit.subreddit('all').search(
                    query=kw,
                    sort=sort,
                    time_filter=time_filter,
                    limit=posts_per_kw
                )
                
                count = 0
                for submission in submissions:
                    # 去重检查
                    if self._is_post_processed(submission.id):
                        continue
                    
                    post_data = self._extract_post_data(submission, 'search')
                    if not post_data or not self._apply_post_filters(post_data):
                        continue
                    
                    if self.redis_client.push_data(post_data):
                        count += 1
                        stats['posts'] += 1
                        self._mark_post_processed(submission.id)
                        
                        # 抓取搜索结果的评论
                        comments_count = self._crawl_comments(submission, 'search')
                        stats['comments'] += comments_count
                    
                    time.sleep(0.3)  # 搜索请求更敏感
                
                logger.info(f"  └─ ✓ 关键词 '{kw}' 抓取 {count} 条新帖")
                
            except Exception as e:
                logger.error(f"  ✗ 关键词 '{kw}' 搜索失败: {e}")
                stats['errors'] += 1
        
        return stats
    
    def _is_post_processed(self, post_id: str) -> bool:
        """
        检查帖子是否已处理
        
        Args:
            post_id: Reddit 帖子ID
        
        Returns:
            bool: 是否已处理
        """
        try:
            key = f"reddit:post:{post_id}"
            return self.redis_client.client.exists(key) > 0
        except Exception as e:
            logger.warning(f"检查帖子去重状态失败: {e}")
            return False
    
    def _mark_post_processed(self, post_id: str):
        """
        标记帖子为已处理
        
        Args:
            post_id: Reddit 帖子ID
        """
        try:
            key = f"reddit:post:{post_id}"
            # 7天有效期（604800秒）
            self.redis_client.client.setex(key, 604800, "1")
        except Exception as e:
            logger.warning(f"标记帖子已处理失败: {e}")
    
    def _is_comment_processed(self, comment_id: str) -> bool:
        """
        检查评论是否已处理
        
        Args:
            comment_id: Reddit 评论ID
        
        Returns:
            bool: 是否已处理
        """
        try:
            key = f"reddit:comment:{comment_id}"
            return self.redis_client.client.exists(key) > 0
        except Exception as e:
            logger.warning(f"检查评论去重状态失败: {e}")
            return False
    
    def _mark_comment_processed(self, comment_id: str):
        """
        标记评论为已处理
        
        Args:
            comment_id: Reddit 评论ID
        """
        try:
            key = f"reddit:comment:{comment_id}"
            # 7天有效期（604800秒）
            self.redis_client.client.setex(key, 604800, "1")
        except Exception as e:
            logger.warning(f"标记评论已处理失败: {e}")
    
    def _is_valid_comment(self, comment_data: Dict) -> bool:
        """
        检查评论是否有效（过滤删除/移除的评论和无意义内容）
        
        Args:
            comment_data: 评论数据
        
        Returns:
            bool: 是否有效
        """
        text = comment_data.get('text', '').strip()
        
        # 过滤已删除/移除的评论
        if text in ['[deleted]', '[removed]']:
            logger.debug(f"        ⏭️ 跳过已删除评论")
            return False
        
        # 过滤过短的评论（少于3个字符）
        if len(text) < 3:
            logger.debug(f"        ⏭️ 跳过过短评论: {text}")
            return False
        
        # 可选：过滤纯表情或符号的评论
        if text in ['Lol', 'lol', 'LOL', '...', '???', '!!!', '👍', '😂']:
            logger.debug(f"        ⏭️ 跳过无意义评论: {text}")
            return False
        
        return True
    
    def _apply_post_filters(self, post_data: Dict) -> bool:
        """
        应用过滤条件（新帖需放宽）
        
        Args:
            post_data: 帖子数据
        
        Returns:
            bool: 是否通过过滤
        """
        min_upvotes = self.post_filters.get('min_upvotes', 0)
        min_comments = self.post_filters.get('min_comments', 0)
        
        if post_data['score'] < min_upvotes or post_data['num_comments'] < min_comments:
            logger.debug(
                f"  ⏭️ 跳过低热度帖子 (upvotes={post_data['score']}, "
                f"comments={post_data['num_comments']})"
            )
            return False
        return True
    
    def _extract_post_data(self, submission, subreddit_name: str) -> Dict[str, Any]:
        """
        提取帖子数据 - 尽可能完整的信息
        
        Args:
            submission: PRAW submission 对象
            subreddit_name: 子版块名称
        
        Returns:
            dict: 帖子数据
        """
        try:
            # 组合标题和正文
            text = submission.title
            if submission.selftext:
                text += "\n\n" + submission.selftext
            
            # 转换 created_utc (Unix 时间戳) 为 ISO 8601 格式字符串
            from datetime import datetime
            created_dt = datetime.utcfromtimestamp(submission.created_utc)
            created_at_iso = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            data = {
                # 基础字段
                'text': text,
                'source': 'reddit_post',
                'created_at': created_at_iso,  # ← ISO 8601 格式字符串
                'url': f"https://www.reddit.com{submission.permalink}",
                
                # Reddit 特有字段
                'subreddit': subreddit_name,
                'post_id': submission.id,
                'author': str(submission.author) if submission.author else '[deleted]',
                
                # 互动数据（用于趋势分析）
                'score': submission.score,
                'upvote_ratio': getattr(submission, 'upvote_ratio', 0),
                'num_comments': submission.num_comments,
                
                # 内容类型
                'is_self': submission.is_self,
                'is_video': submission.is_video,
                'link_flair_text': submission.link_flair_text,
                
                # 其他元数据
                'gilded': submission.gilded,
                'distinguished': submission.distinguished,
                'stickied': submission.stickied,
                'over_18': submission.over_18,
                'spoiler': submission.spoiler,
                
                # 标题单独保留（用于关键词提取）
                'title': submission.title,
                'selftext': submission.selftext if submission.selftext else ''
            }
            return data
        except Exception as e:
            logger.error(f"提取帖子数据失败: {e}")
            return None
    
    def _crawl_comments(self, submission, subreddit_name: str) -> int:
        """
        抓取帖子的评论（已添加去重和过滤）
        
        Args:
            submission: PRAW submission 对象
            subreddit_name: 子版块名称
        
        Returns:
            int: 成功抓取的评论数量
        """
        count = 0
        try:
            # 展开所有评论（限制数量以避免过多请求）
            submission.comments.replace_more(limit=0)
            
            # 获取评论列表
            all_comments = submission.comments.list()
            
            # 按评分排序，取前N条（保留原逻辑）
            sorted_comments = sorted(
                all_comments, 
                key=lambda c: c.score if hasattr(c, 'score') else 0, 
                reverse=True
            )[:self.comments_limit]
            
            for idx, comment in enumerate(sorted_comments, 1):
                try:
                    # 🔥 新增：评论去重检查
                    if self._is_comment_processed(comment.id):
                        logger.debug(f"        ⏭️ 跳过已抓取评论: {comment.id}")
                        continue
                    
                    comment_data = self._extract_comment_data(comment, subreddit_name)
                    
                    # 🔥 新增：过滤无效评论
                    if not comment_data or not self._is_valid_comment(comment_data):
                        continue
                    
                    if self.redis_client.push_data(comment_data):
                        count += 1
                        # 🔥 新增：标记评论为已处理
                        self._mark_comment_processed(comment.id)
                except Exception as e:
                    logger.warning(f"        ✗ 保存评论失败: {e}")
            
        except prawcore.ResponseException as e:
            logger.error(
                f"      ✗ Reddit API 错误 (帖子: {submission.id}): "
                f"{e.response.status_code} - {e.response.reason}"
            )
        except Exception as e:
            logger.error(f"      ✗ 抓取评论时出错: {e}")
        
        return count
    
    def _extract_comment_data(self, comment, subreddit_name: str) -> Dict[str, Any]:
        """
        提取评论数据 - 完整信息（用于情感分析）（保持原逻辑）
        
        Args:
            comment: PRAW comment 对象
            subreddit_name: 子版块名称
        
        Returns:
            dict: 评论数据
        """
        try:
            data = {
                # 基础字段
                'text': comment.body,
                'source': 'reddit_comment',
                'timestamp': int(comment.created_utc),
                'url': f"https://www.reddit.com{comment.permalink}",
                
                # Reddit 特有字段
                'subreddit': subreddit_name,
                'comment_id': comment.id,
                'author': str(comment.author) if comment.author else '[deleted]',
                
                # 互动数据（用于情感分析权重）
                'score': comment.score,
                'gilded': comment.gilded,
                'distinguished': comment.distinguished,
                'stickied': comment.stickied,
                
                # 评论上下文
                'is_submitter': comment.is_submitter,  # 是否是帖子作者
                'parent_id': comment.parent_id,
                'link_id': comment.link_id
            }
            return data
        except Exception as e:
            logger.error(f"提取评论数据失败: {e}")
            return None


def main():
    """测试函数"""
    import yaml
    
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化 Redis 客户端
    redis_client = RedisClient(**config['redis'])
    
    # 初始化并运行爬虫
    crawler = RedditCrawler(config['reddit'], redis_client)
    stats = crawler.crawl()
    
    print(f"抓取完成: {stats}")
    
    # 关闭连接
    redis_client.close()


if __name__ == '__main__':
    main()
