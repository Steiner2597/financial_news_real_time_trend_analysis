#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置同步工具
用于统一各模块的Redis配置
"""

import os
import yaml
import json
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent
CONFIG_FILE = ROOT_DIR / "config.yaml"

def load_unified_config():
    """加载统一配置文件"""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def update_scraper_config(unified_config):
    """更新Scraper模块配置"""
    scraper_config_path = ROOT_DIR / "scraper" / "config.yaml"
    
    if not scraper_config_path.exists():
        print(f"⚠️  Scraper配置文件不存在: {scraper_config_path}")
        return False
    
    try:
        with open(scraper_config_path, 'r', encoding='utf-8') as f:
            scraper_config = yaml.safe_load(f)
        
        # 更新Redis配置
        redis_config = unified_config['redis']
        scraper_config['redis']['host'] = redis_config['host']
        scraper_config['redis']['port'] = redis_config['port']
        scraper_config['redis']['password'] = redis_config['password']
        scraper_config['redis']['db'] = redis_config['databases']['scraper_output']
        
        with open(scraper_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(scraper_config, f, allow_unicode=True, default_flow_style=False)
        
        print(f"✅ Scraper配置已更新")
        return True
    except Exception as e:
        print(f"❌ 更新Scraper配置失败: {e}")
        return False

def update_cleaner_config(unified_config):
    """更新Cleaner模块配置"""
    cleaner_config_path = ROOT_DIR / "cleaner" / "config_processing_dl.yaml"
    
    if not cleaner_config_path.exists():
        print(f"⚠️  Cleaner配置文件不存在: {cleaner_config_path}")
        return False
    
    try:
        with open(cleaner_config_path, 'r', encoding='utf-8') as f:
            cleaner_config = yaml.safe_load(f)
        
        # 更新Redis配置
        redis_config = unified_config['redis']
        cleaner_config['redis']['host'] = redis_config['host']
        cleaner_config['redis']['port'] = redis_config['port']
        cleaner_config['redis']['db_in'] = redis_config['databases']['cleaner_input']
        cleaner_config['redis']['db_out'] = redis_config['databases']['cleaner_output']
        
        with open(cleaner_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(cleaner_config, f, allow_unicode=True, default_flow_style=False)
        
        print(f"✅ Cleaner配置已更新")
        return True
    except Exception as e:
        print(f"❌ 更新Cleaner配置失败: {e}")
        return False

def update_processor_config(unified_config):
    """更新Processor模块配置"""
    processor_config_path = ROOT_DIR / "processer" / "Analysis" / "config.py"
    
    if not processor_config_path.exists():
        print(f"⚠️  Processor配置文件不存在: {processor_config_path}")
        return False
    
    try:
        redis_config = unified_config['redis']
        
        # 读取现有配置
        with open(processor_config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 更新Redis配置（简单的字符串替换）
        # 注意：这是一个简化的实现，实际可能需要更复杂的解析
        print(f"ℹ️  Processor配置需要手动检查和更新")
        print(f"   配置文件: {processor_config_path}")
        print(f"   确保Redis配置为:")
        print(f"   host: {redis_config['host']}")
        print(f"   port: {redis_config['port']}")
        print(f"   db: {redis_config['databases']['processor_output']}")
        
        return True
    except Exception as e:
        print(f"❌ 检查Processor配置失败: {e}")
        return False

def update_visualization_config(unified_config):
    """更新Visualization模块配置"""
    viz_config_path = ROOT_DIR / "visualization" / "backend" / "app" / "config.py"
    
    if not viz_config_path.exists():
        print(f"⚠️  Visualization配置文件不存在: {viz_config_path}")
        return False
    
    try:
        redis_config = unified_config['redis']
        
        print(f"ℹ️  Visualization配置需要手动检查和更新")
        print(f"   配置文件: {viz_config_path}")
        print(f"   确保Redis配置为:")
        print(f"   REDIS_HOST: {redis_config['host']}")
        print(f"   REDIS_PORT: {redis_config['port']}")
        print(f"   REDIS_DB: {redis_config['databases']['visualization']}")
        
        return True
    except Exception as e:
        print(f"❌ 检查Visualization配置失败: {e}")
        return False

def display_unified_config(config):
    """显示统一配置"""
    print("\n" + "=" * 60)
    print("📋 统一配置信息")
    print("=" * 60)
    
    redis_config = config['redis']
    print(f"\n🔧 Redis配置:")
    print(f"  Host: {redis_config['host']}")
    print(f"  Port: {redis_config['port']}")
    print(f"  Password: {redis_config['password'] or '(无)'}")
    
    print(f"\n📊 数据库分配:")
    for db_name, db_num in redis_config['databases'].items():
        print(f"  {db_name}: DB{db_num}")
    
    print(f"\n🔑 键名规范:")
    for key_name, key_value in redis_config['keys'].items():
        print(f"  {key_name}: {key_value}")
    
    print(f"\n🐍 Python环境: {config['project']['python_env']}")
    print("=" * 60 + "\n")

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 配置同步工具")
    print("=" * 60)
    print()
    
    # 检查统一配置文件
    if not CONFIG_FILE.exists():
        print(f"❌ 统一配置文件不存在: {CONFIG_FILE}")
        return
    
    # 加载配置
    print(f"📖 读取统一配置: {CONFIG_FILE}")
    unified_config = load_unified_config()
    
    # 显示配置
    display_unified_config(unified_config)
    
    # 确认是否继续
    response = input("是否将此配置同步到各模块？(y/N): ")
    if response.lower() != 'y':
        print("❌ 已取消")
        return
    
    print("\n🔄 开始同步配置...\n")
    
    # 更新各模块配置
    results = {
        "Scraper": update_scraper_config(unified_config),
        "Cleaner": update_cleaner_config(unified_config),
        "Processor": update_processor_config(unified_config),
        "Visualization": update_visualization_config(unified_config)
    }
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 配置同步结果")
    print("=" * 60)
    
    for module, success in results.items():
        status = "✅ 成功" if success else "⚠️  需要手动检查"
        print(f"  {module}: {status}")
    
    print("\n" + "=" * 60)
    print("💡 提示:")
    print("  1. 对于需要手动检查的模块，请打开对应配置文件")
    print("  2. 确保所有模块的Redis配置一致")
    print("  3. 配置完成后运行 check_env.bat 验证环境")
    print("=" * 60)

if __name__ == "__main__":
    main()
