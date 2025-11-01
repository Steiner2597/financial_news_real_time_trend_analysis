"""
测试单次清洗器
验证单次清洗逻辑是否正常工作
"""
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

def test_single_pass_cleaner():
    """测试单次清洗器"""
    print("=" * 70)
    print("测试单次清洗器")
    print("=" * 70)
    
    try:
        from event_driven.single_pass_cleaner import SinglePassCleaner
        import yaml
        
        # 加载配置
        config_path = Path(__file__).parent / "config_processing.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        redis_config = config['redis']
        
        # 创建清洗器
        cleaner = SinglePassCleaner(
            redis_host=redis_config['host'],
            redis_port=redis_config['port'],
            db_in=redis_config['db_in'],
            db_out=redis_config['db_out'],
            queue_in=redis_config['data_queue'],
            queue_out=redis_config['clean_data_queue'],
            id_cache_key=redis_config['id_cache']
        )
        
        print("✓ SinglePassCleaner 创建成功")
        print(f"  - Redis: {redis_config['host']}:{redis_config['port']}")
        print(f"  - 输入队列: {redis_config['data_queue']} (DB{redis_config['db_in']})")
        print(f"  - 输出队列: {redis_config['clean_data_queue']} (DB{redis_config['db_out']})")
        
        # 执行单次清洗
        print("\n执行单次清洗...")
        stats = cleaner.clean_once()
        
        print("\n清洗结果:")
        print(f"  - 总处理: {stats['total_processed']}")
        print(f"  - 清洗成功: {stats['cleaned']}")
        print(f"  - 去重过滤: {stats['duplicates']}")
        print(f"  - 无效数据: {stats['invalid']}")
        
        # 导出文件
        if stats['cleaned'] > 0:
            print("\n导出到文件...")
            output_dir = Path(__file__).parent / "output"
            output_file = cleaner.export_to_file(output_dir)
            print(f"✓ 文件已导出: {output_file}")
        
        # 关闭清洗器
        cleaner.close()
        print("\n✓ 清洗器已关闭")
        
        print("\n" + "=" * 70)
        print("✅ 单次清洗器测试通过！")
        print("=" * 70)
        
    except FileNotFoundError as e:
        print(f"\n❌ 配置文件不存在: {e}")
        print("请确保 config_processing.yaml 在 cleaner 目录下")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_event_driven_cleaner():
    """测试事件驱动清洗器"""
    print("\n" + "=" * 70)
    print("测试事件驱动清洗器")
    print("=" * 70)
    
    try:
        from event_driven.cleaner import EventDrivenCleaner
        
        cleaner = EventDrivenCleaner()
        print("✓ EventDrivenCleaner 初始化成功")
        print(f"  - 监听频道: {cleaner.listen_channel}")
        print(f"  - 发送频道: {cleaner.send_channel}")
        print(f"  - 去重模式: {cleaner.dedup_config.get('mode', 'N/A')}")
        
        print("\n✓ 事件驱动清洗器测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("单次清洗逻辑测试")
    print("=" * 70 + "\n")
    
    # 测试单次清洗器
    test_single_pass_cleaner()
    
    # 测试事件驱动清洗器
    test_event_driven_cleaner()
    
    print("\n" + "=" * 70)
    print("所有测试完成！")
    print("=" * 70)
    print("\n现在可以运行:")
    print("  python data_cleaner_event_driven.py")
    print("  或: start_cleaner.bat")
    print("\n清洗器将:")
    print("  1. 等待爬虫完成通知")
    print("  2. 收到通知后执行单次清洗")
    print("  3. 清洗完成后发送通知给 Processor")
    print("  4. 继续待命等待下一次通知")
    print("  ✅ 不会阻塞在清洗循环中！")


if __name__ == "__main__":
    main()
