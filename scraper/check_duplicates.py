"""
Redis 数据查重脚本
检查 Redis 队列中是否存在重复数据
"""
import json
import yaml
from collections import defaultdict
from typing import Dict, List, Tuple
from utils.redis_client import RedisClient
from utils.logger import setup_logger

logger = setup_logger('check_duplicates')


class DuplicateChecker:
    """数据查重器"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.queue_name = redis_client.queue_name
    
    def check_duplicates(self) -> Dict:
        """
        检查队列中的重复数据
        
        Returns:
            dict: 查重统计结果
        """
        logger.info("=" * 70)
        logger.info("开始检查 Redis 队列数据重复情况...")
        logger.info("=" * 70)
        
        # 获取队列长度
        queue_length = self.redis_client.client.llen(self.queue_name)
        logger.info(f"📊 队列总长度: {queue_length} 条数据")
        
        if queue_length == 0:
            logger.warning("⚠️  队列为空，无数据可查")
            return {'total': 0, 'unique': 0, 'duplicates': 0}
        
        # 用于存储唯一标识
        seen_ids = defaultdict(list)  # {唯一ID: [索引列表]}
        seen_texts = defaultdict(list)  # {文本hash: [索引列表]}
        
        # 按来源统计
        source_count = defaultdict(int)
        source_duplicates = defaultdict(int)
        
        logger.info("🔍 正在扫描队列数据...")
        
        # 遍历队列（不删除数据）
        for i in range(queue_length):
            try:
                # 获取数据但不删除
                json_data = self.redis_client.client.lindex(self.queue_name, i)
                if not json_data:
                    continue
                
                data = json.loads(json_data)
                source = data.get('source', 'unknown')
                source_count[source] += 1
                
                # 生成唯一标识
                unique_id = self._generate_unique_id(data)
                text_hash = hash(data.get('text', ''))
                
                # 记录位置
                seen_ids[unique_id].append(i)
                seen_texts[text_hash].append(i)
                
                # 进度显示
                if (i + 1) % 1000 == 0:
                    logger.info(f"  已扫描: {i + 1}/{queue_length} ({(i+1)/queue_length*100:.1f}%)")
                    
            except Exception as e:
                logger.error(f"  ✗ 解析数据失败 (索引 {i}): {e}")
        
        logger.info(f"✓ 扫描完成: {queue_length} 条数据")
        print()
        
        # 统计重复情况
        duplicate_ids = {uid: indices for uid, indices in seen_ids.items() if len(indices) > 1}
        duplicate_texts = {th: indices for th, indices in seen_texts.items() if len(indices) > 1}
        
        # 计算统计数据
        total_items = queue_length
        unique_ids = len(seen_ids)
        duplicate_id_count = sum(len(indices) - 1 for indices in duplicate_ids.values())
        duplicate_text_count = sum(len(indices) - 1 for indices in duplicate_texts.values())
        
        # 输出统计结果
        self._print_statistics(
            total_items,
            unique_ids,
            duplicate_id_count,
            duplicate_text_count,
            source_count,
            duplicate_ids,
            duplicate_texts
        )
        
        return {
            'total': total_items,
            'unique_ids': unique_ids,
            'duplicate_ids': duplicate_id_count,
            'duplicate_texts': duplicate_text_count,
            'source_count': dict(source_count),
            'duplicate_details': {
                'by_id': len(duplicate_ids),
                'by_text': len(duplicate_texts)
            }
        }
    
    def _generate_unique_id(self, data: Dict) -> str:
        """
        生成数据唯一标识
        
        Args:
            data: 数据字典
        
        Returns:
            str: 唯一标识
        """
        source = data.get('source', '')
        
        # 根据来源使用不同的唯一标识策略
        if source == 'reddit_post':
            return f"reddit:post:{data.get('post_id', '')}"
        elif source == 'reddit_comment':
            return f"reddit:comment:{data.get('comment_id', '')}"
        elif source == 'newsapi':
            return f"newsapi:url:{data.get('url', '')}"
        elif source == 'rss':
            return f"rss:url:{data.get('url', '')}"
        elif source == 'stocktwits':
            return f"stocktwits:id:{data.get('message_id', '')}"
        elif source == 'twitter':
            return f"twitter:id:{data.get('tweet_id', '')}"
        else:
            # 使用 URL 或文本哈希作为备用
            url = data.get('url', '')
            if url:
                return f"{source}:url:{url}"
            return f"{source}:hash:{hash(data.get('text', ''))}"
    
    def _print_statistics(
        self,
        total: int,
        unique: int,
        dup_ids: int,
        dup_texts: int,
        source_count: Dict,
        duplicate_ids: Dict,
        duplicate_texts: Dict
    ):
        """打印统计结果"""
        
        print()
        logger.info("=" * 70)
        logger.info("📈 查重统计结果")
        logger.info("=" * 70)
        
        # 总体统计
        logger.info(f"📊 总数据量: {total} 条")
        logger.info(f"✓ 唯一ID数: {unique} 个")
        logger.info(f"✗ ID重复数: {dup_ids} 条 ({dup_ids/total*100:.2f}%)")
        logger.info(f"✗ 文本重复: {dup_texts} 条 ({dup_texts/total*100:.2f}%)")
        
        print()
        logger.info("-" * 70)
        logger.info("📑 按来源统计")
        logger.info("-" * 70)
        
        for source, count in sorted(source_count.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total * 100
            logger.info(f"  {source:20s}: {count:6d} 条 ({percentage:5.2f}%)")
        
        # 重复详情（显示前10个）
        if duplicate_ids:
            print()
            logger.info("-" * 70)
            logger.info(f"🔍 ID重复详情 (共 {len(duplicate_ids)} 组，显示前10组)")
            logger.info("-" * 70)
            
            for i, (uid, indices) in enumerate(list(duplicate_ids.items())[:10], 1):
                logger.info(f"  {i}. ID: {uid[:60]}...")
                logger.info(f"     重复 {len(indices)} 次，位置: {indices[:5]}{'...' if len(indices) > 5 else ''}")
        
        if duplicate_texts:
            print()
            logger.info("-" * 70)
            logger.info(f"🔍 文本重复详情 (共 {len(duplicate_texts)} 组，显示前5组)")
            logger.info("-" * 70)
            
            for i, (th, indices) in enumerate(list(duplicate_texts.items())[:5], 1):
                # 读取第一条数据查看内容
                try:
                    json_data = self.redis_client.client.lindex(self.queue_name, indices[0])
                    data = json.loads(json_data)
                    text_preview = data.get('text', '')[:80]
                    logger.info(f"  {i}. 文本预览: {text_preview}...")
                    logger.info(f"     重复 {len(indices)} 次，位置: {indices[:5]}{'...' if len(indices) > 5 else ''}")
                except:
                    pass
        
        print()
        logger.info("=" * 70)
        
        # 建议
        if dup_ids > 0 or dup_texts > 0:
            logger.warning("⚠️  发现重复数据！建议:")
            logger.warning("   1. 检查爬虫去重逻辑是否正常工作")
            logger.warning("   2. 可以运行 clean_duplicates.py 清理重复数据")
            logger.warning("   3. 确认 Redis 去重键是否设置了正确的过期时间")
        else:
            logger.info("✓ 未发现重复数据，数据质量良好！")
        
        logger.info("=" * 70)
    
    def get_duplicate_details(self, show_content: bool = False) -> List[Dict]:
        """
        获取重复数据的详细信息
        
        Args:
            show_content: 是否显示数据内容
        
        Returns:
            list: 重复数据列表
        """
        queue_length = self.redis_client.client.llen(self.queue_name)
        seen = defaultdict(list)
        
        for i in range(queue_length):
            try:
                json_data = self.redis_client.client.lindex(self.queue_name, i)
                data = json.loads(json_data)
                unique_id = self._generate_unique_id(data)
                seen[unique_id].append((i, data if show_content else None))
            except:
                pass
        
        duplicates = []
        for uid, items in seen.items():
            if len(items) > 1:
                duplicates.append({
                    'unique_id': uid,
                    'count': len(items),
                    'indices': [idx for idx, _ in items],
                    'data': [d for _, d in items] if show_content else None
                })
        
        return duplicates


def main():
    """主函数"""
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化 Redis 客户端
    redis_client = RedisClient(**config['redis'])
    
    # 创建查重器
    checker = DuplicateChecker(redis_client)
    
    # 执行查重
    result = checker.check_duplicates()
    
    print()
    logger.info("查重完成！")
    
    # 询问是否导出详情
    try:
        export = input("\n是否导出重复数据详情到文件？(y/n): ").strip().lower()
        if export == 'y':
            duplicates = checker.get_duplicate_details(show_content=True)
            
            output_file = 'duplicate_details.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(duplicates, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ 重复数据详情已导出到: {output_file}")
    except KeyboardInterrupt:
        print()
        logger.info("已取消")
    
    # 关闭连接
    redis_client.close()


if __name__ == '__main__':
    main()
