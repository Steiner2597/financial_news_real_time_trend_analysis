"""
手动触发 Processor 执行脚本
向 Redis 发送清洗完成通知，让 Processor 立即执行一次处理
"""
import redis
import json
from datetime import datetime
from config import CONFIG


def trigger_processor():
    """触发 Processor 执行"""
    print("=" * 70)
    print("🚀 手动触发 Processor 执行")
    print("=" * 70)
    
    # 使用本地配置
    redis_config = CONFIG['redis']
    
    # 连接 Redis
    try:
        r = redis.Redis(
            host=redis_config['host'],
            port=redis_config['port'],
            db=redis_config['input_db'],  # DB1 (从 Cleaner 读取)
            decode_responses=True
        )
        r.ping()
        print(f"✓ Redis 连接成功: {redis_config['host']}:{redis_config['port']}/DB{redis_config['input_db']}")
    except Exception as e:
        print(f"✗ Redis 连接失败: {e}")
        return False
    
    # 构造通知消息
    notification = {
        "event": "cleaner_complete",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_count": "N/A",
        "source": "manual_trigger",
        "message": "手动触发 Processor 执行"
    }
    
    # 发送通知
    channel = redis_config['notification']['channel']  # 从配置读取频道名
    try:
        result = r.publish(channel, json.dumps(notification, ensure_ascii=False))
        print(f"\n✓ 通知已发送到频道: {channel}")
        print(f"✓ 订阅者数量: {result}")
        
        if result == 0:
            print("\n⚠️  警告: 当前没有订阅者在监听此频道")
            print("   请确保 Processor 正在运行并且处于事件驱动模式")
        else:
            print("\n✅ 触发成功!")
            print("   Processor 应该会立即开始执行处理任务")
        
        # 显示通知内容
        print("\n📤 发送的通知内容:")
        print(json.dumps(notification, indent=2, ensure_ascii=False))
        
        return True
        
    except Exception as e:
        print(f"\n✗ 发送通知失败: {e}")
        return False


if __name__ == "__main__":
    try:
        trigger_processor()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
