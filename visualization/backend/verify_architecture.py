#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化后架构验证脚本
用于测试从 processed_data 命名空间读取数据
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.redis_client import RedisClient


def test_redis_connection():
    """测试Redis连接"""
    print("=" * 60)
    print("🧪 测试 Redis 连接")
    print("=" * 60)
    
    try:
        client = RedisClient()
        success = client.test_redis_connection()
        
        if success:
            print("\n✅ Redis 连接测试通过")
            return True
        else:
            print("\n❌ Redis 连接测试失败")
            return False
    except Exception as e:
        print(f"\n❌ Redis 连接失败: {e}")
        return False


def test_data_reading():
    """测试数据读取"""
    print("\n" + "=" * 60)
    print("🧪 测试从 processed_data 命名空间读取数据")
    print("=" * 60)
    
    try:
        client = RedisClient()
        
        # 检查 Redis 信息
        client.check_redis_info()
        
        # 测试数据检索
        print("\n" + "=" * 30)
        print("📋 数据检索测试")
        print("=" * 30)
        
        success = client.test_data_retrieval()
        
        if success:
            print("\n✅ 数据读取测试通过")
            return True
        else:
            print("\n❌ 数据读取测试失败")
            return False
            
    except Exception as e:
        print(f"\n❌ 数据读取失败: {e}")
        return False


def check_processed_data_keys():
    """检查 processed_data 命名空间的键"""
    print("\n" + "=" * 60)
    print("🔍 检查 processed_data 命名空间")
    print("=" * 60)
    
    try:
        client = RedisClient()
        
        # 获取所有 processed_data 键
        keys = client.redis_client.keys("processed_data:*")
        
        if not keys:
            print("⚠️  警告：processed_data 命名空间中没有数据")
            print("📝 请确保其他模块已经往 processed_data 写入数据")
            print("   或者使用测试数据加载工具")
            return False
        
        print(f"✅ 找到 {len(keys)} 个键：")
        for key in sorted(keys):
            # 获取键的类型和大小
            key_type = client.redis_client.type(key)
            
            if key_type == 'string':
                value = client.redis_client.get(key)
                size = len(value) if value else 0
                print(f"  📄 {key} ({key_type}, {size} bytes)")
            else:
                print(f"  📄 {key} ({key_type})")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("🚀 后端架构简化验证")
    print("=" * 60)
    print("📝 验证内容：")
    print("  1. Redis 连接")
    print("  2. processed_data 命名空间检查")
    print("  3. 数据读取功能")
    print("=" * 60)
    
    results = {
        "redis_connection": False,
        "data_keys_check": False,
        "data_reading": False
    }
    
    # 1. 测试 Redis 连接
    results["redis_connection"] = test_redis_connection()
    
    if not results["redis_connection"]:
        print("\n❌ Redis 连接失败，无法继续测试")
        return False
    
    # 2. 检查 processed_data 键
    results["data_keys_check"] = check_processed_data_keys()
    
    # 3. 测试数据读取
    results["data_reading"] = test_data_reading()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！后端架构简化成功！")
    else:
        print("⚠️  部分测试未通过，请检查配置")
        if not results["data_keys_check"]:
            print("\n💡 提示：")
            print("  - 确保其他模块正在运行并往 Redis 写入数据")
            print("  - 或者使用 data_loader.py 加载测试数据")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
