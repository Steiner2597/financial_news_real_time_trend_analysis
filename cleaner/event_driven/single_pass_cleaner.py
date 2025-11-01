"""
单次清洗处理器
提供一次性清洗数据的功能，不阻塞主循环
"""
import redis
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class SinglePassCleaner:
    """单次清洗处理器"""
    
    def __init__(self, redis_host: str, redis_port: int, db_in: int, db_out: int,
                 queue_in: str, queue_out: str, id_cache_key: str):
        """
        初始化单次清洗处理器
        
        Args:
            redis_host: Redis 主机
            redis_port: Redis 端口
            db_in: 输入数据库
            db_out: 输出数据库
            queue_in: 输入队列
            queue_out: 输出队列
            id_cache_key: ID 缓存键
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.db_in = db_in
        self.db_out = db_out
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.id_cache_key = id_cache_key
        
        # 连接 Redis
        self.r_in = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=db_in,
            decode_responses=True
        )
        
        self.r_out = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=db_out,
            decode_responses=True
        )
    
    def clean_once(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        执行一次清洗操作
        
        Args:
            batch_size: 每批处理的数量
            
        Returns:
            清洗结果统计
        """
        import json
        import time
        from datetime import datetime
        
        logger.info("\n🧹 开始单次清洗...")
        
        stats = {
            'total_processed': 0,
            'cleaned': 0,
            'duplicates': 0,
            'invalid': 0,
            'start_time': datetime.now().isoformat()
        }
        
        try:
            # 获取队列当前长度（只处理这些数据，不等待新数据）
            queue_length = self.r_in.llen(self.queue_in)
            logger.info(f"📊 待清洗数据量: {queue_length}")
            
            if queue_length == 0:
                logger.info("ℹ️  队列为空，无需清洗")
                stats['end_time'] = datetime.now().isoformat()
                return stats
            
            # 批量处理（使用 LRANGE 读取，不删除原始数据）
            processed = 0
            while processed < queue_length:
                # 计算本批次大小
                current_batch = min(batch_size, queue_length - processed)
                
                # 批量读取数据（不删除）
                start_index = processed
                end_index = processed + current_batch - 1
                batch_data = self.r_in.lrange(self.queue_in, start_index, end_index)
                
                # 处理批次数据
                for data_str in batch_data:
                    try:
                        # 解析数据
                        data = json.loads(data_str)
                        
                        # 检查必要字段
                        if not self._validate_data(data):
                            stats['invalid'] += 1
                            continue
                        
                        # 检查去重
                        item_id = self._get_item_id(data)
                        if self._is_duplicate(item_id):
                            stats['duplicates'] += 1
                            continue
                        
                        # 清洗数据
                        cleaned_data = self._clean_data(data)
                        
                        # 推送到输出队列
                        self.r_out.lpush(self.queue_out, json.dumps(cleaned_data, ensure_ascii=False))
                        
                        # 添加到缓存
                        self._add_to_cache(item_id)
                        
                        stats['cleaned'] += 1
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON 解析失败: {e}")
                        stats['invalid'] += 1
                    except Exception as e:
                        logger.error(f"处理数据时出错: {e}")
                        stats['invalid'] += 1
                
                processed += len(batch_data)
                stats['total_processed'] = processed
                
                # 显示进度
                if processed % 100 == 0 or processed >= queue_length:
                    logger.info(f"进度: {processed}/{queue_length} "
                               f"(清洗: {stats['cleaned']}, 去重: {stats['duplicates']}, 无效: {stats['invalid']})")
            
            stats['end_time'] = datetime.now().isoformat()
            
            logger.info("\n✨ 单次清洗完成")
            logger.info(f"总处理: {stats['total_processed']}")
            logger.info(f"清洗成功: {stats['cleaned']}")
            logger.info(f"去重过滤: {stats['duplicates']}")
            logger.info(f"无效数据: {stats['invalid']}")
            
            return stats
            
        except Exception as e:
            logger.error(f"清洗过程出错: {e}")
            import traceback
            traceback.print_exc()
            stats['error'] = str(e)
            stats['end_time'] = datetime.now().isoformat()
            return stats
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """
        验证数据是否有效
        
        Args:
            data: 数据字典
            
        Returns:
            是否有效
        """
        # 检查必要字段：source 必须有，文本字段至少有一个
        if 'source' not in data or not data['source']:
            return False
        
        # 文本字段：text、content、title 至少有一个且非空
        has_text = any(
            field in data and data[field] and str(data[field]).strip()
            for field in ['text', 'content', 'title']
        )
        
        return has_text
    
    def _get_item_id(self, data: Dict[str, Any]) -> str:
        """
        获取数据的唯一标识
        
        Args:
            data: 数据字典
            
        Returns:
            唯一标识
        """
        # 使用 ID 或生成哈希
        if 'id' in data:
            return str(data['id'])
        
        # 使用标题和来源的组合
        import hashlib
        content = f"{data.get('title', '')}_{data.get('source', '')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_duplicate(self, item_id: str) -> bool:
        """
        检查是否重复
        
        Args:
            item_id: 数据ID
            
        Returns:
            是否重复
        """
        import time
        
        # 检查缓存类型
        cache_type = self.r_out.type(self.id_cache_key)
        
        if cache_type == 'set':
            # SET 类型（永久模式）
            return self.r_out.sismember(self.id_cache_key, item_id)
        
        elif cache_type == 'zset':
            # ZSET 类型（时间窗口模式）
            score = self.r_out.zscore(self.id_cache_key, item_id)
            if score is None:
                return False
            
            # 检查是否在时间窗口内
            current_time = time.time()
            return score > (current_time - 86400)  # 24小时窗口
        
        else:
            # 缓存不存在或其他类型
            return False
    
    def _add_to_cache(self, item_id: str):
        """
        添加到缓存
        
        Args:
            item_id: 数据ID
        """
        import time
        
        # 检查缓存类型
        cache_type = self.r_out.type(self.id_cache_key)
        
        if cache_type == 'none' or cache_type == 'zset':
            # 使用 ZSET（时间窗口模式）
            current_time = time.time()
            self.r_out.zadd(self.id_cache_key, {item_id: current_time})
            
            # 清理过期数据
            expiry_time = current_time - 86400  # 24小时前
            self.r_out.zremrangebyscore(self.id_cache_key, 0, expiry_time)
        else:
            # 使用 SET（永久模式）
            self.r_out.sadd(self.id_cache_key, item_id)
    
    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清洗数据
        
        Args:
            data: 原始数据
            
        Returns:
            清洗后的数据
        """
        import re
        from datetime import datetime
        
        cleaned = {}
        
        # 1. 提取 id 字段（从多个可能的字段名中提取）
        id_value = (data.get("id") or data.get("post_id") or data.get("comment_id") or 
                    data.get("tweet_id") or data.get("guid") or data.get("message_id"))
        if id_value:
            cleaned['id'] = str(id_value)
        elif data.get('url'):
            # 如果没有 id，使用 URL 作为唯一标识
            cleaned['id'] = data['url']
        else:
            # 最后使用时间戳作为 id
            import time
            cleaned['id'] = f"generated_{int(time.time() * 1000)}"
        
        # 2. 提取 created_at 字段（新闻/评论的发布时间）
        created_at = None
        for field in ["created_at", "created_utc", "published", "published_at",
                      "timestamp", "time", "datetime", "date"]:
            if field in data and data[field]:
                created_at = self._parse_time_field(data[field])
                if created_at:
                    break
        
        if created_at:
            cleaned['created_at'] = created_at
        else:
            # 如果没有找到时间字段，使用当前时间
            cleaned['created_at'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # 3. 清洗文本字段（处理 text、title、content）
        for text_field in ['text', 'title', 'content']:
            if text_field in data and data[text_field]:
                text = str(data[text_field]).strip()
                # 移除多余空格
                text = re.sub(r'\s+', ' ', text)
                # 移除HTML标签（如果有）
                text = re.sub(r'<[^>]+>', '', text)
                cleaned[text_field] = text
        
        # 4. 保留其他重要字段
        for key in ['source', 'url', 'author', 'score', 'comments', 
                    'sentiment', 'tags', 'subreddit', 'symbol', 'symbols']:
            if key in data:
                cleaned[key] = data[key]
        
        # 5. 添加清洗时间戳
        cleaned['cleaned_at'] = datetime.now().isoformat()
        
        return cleaned
    
    def _parse_time_field(self, value) -> str:
        """
        解析时间字段，转换为统一的 ISO 格式字符串
        
        Args:
            value: 时间值（可能是 Unix 时间戳、字符串等）
            
        Returns:
            str: ISO 格式时间字符串，如 "2024-01-01T12:00:00Z"
        """
        from datetime import datetime
        
        if value is None:
            return None
        
        try:
            # 1. 如果是 Unix 时间戳（整数或浮点数）
            if isinstance(value, (int, float)):
                dt = datetime.utcfromtimestamp(float(value))
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # 2. 如果是数字字符串
            if isinstance(value, str) and value.strip().replace('.', '').isdigit():
                dt = datetime.utcfromtimestamp(float(value))
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # 3. 如果是 ISO 格式字符串
            s = str(value).strip()
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except:
                pass
            
            # 4. 尝试常见格式
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except:
                    continue
            
            return None
        except Exception as e:
            logger.warning(f"时间解析失败: {value}, 错误: {e}")
            return None
    
    def export_to_file(self, output_dir: Path) -> str:
        """
        导出清洗结果到文件
        
        Args:
            output_dir: 输出目录
            
        Returns:
            输出文件路径
        """
        import json
        from datetime import datetime
        
        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y-%m-%d")
        output_file = output_dir / f"cleaned_{timestamp}.jsonl"
        
        # 获取队列中的所有数据
        queue_length = self.r_out.llen(self.queue_out)
        
        if queue_length == 0:
            logger.info("ℹ️  输出队列为空，无数据导出")
            return str(output_file)
        
        logger.info(f"📦 导出 {queue_length} 条数据到文件...")
        
        # 导出数据
        with open(output_file, 'w', encoding='utf-8') as f:
            # 使用 LRANGE 读取所有数据（不删除）
            data_list = self.r_out.lrange(self.queue_out, 0, -1)
            
            for data_str in data_list:
                try:
                    data = json.loads(data_str)
                    f.write(json.dumps(data, ensure_ascii=False) + '\n')
                except:
                    pass
        
        logger.info(f"✅ 数据已导出到: {output_file}")
        return str(output_file)
    
    def close(self):
        """关闭连接"""
        try:
            self.r_in.close()
            self.r_out.close()
        except:
            pass
