#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试脚本：验证 24 小时历史数据生成是否正确
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加 Analysis 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import DataLoader
from history_analyzer import HistoryAnalyzer
from text_analyzer import TextAnalyzer

def test_24hour_history():
    """测试 24 小时历史数据生成"""
    
    print("\n" + "="*70)
    print("🧪 测试：24 小时历史数据生成")
    print("="*70)
    
    # 1. 加载数据
    print("\n📥 加载数据...")
    data_loader = DataLoader()
    raw_data = data_loader.load_data()
    
    if raw_data.empty:
        print("❌ 没有数据可以测试")
        return False
    
    # 2. 预处理数据
    print("🔄 预处理数据...")
    df = data_loader.preprocess_data(raw_data)
    
    # 3. 获取时间窗口
    print("📅 获取时间窗口...")
    time_windows = data_loader.get_time_windows(df)
    
    # 4. 验证时间窗口
    print("\n🔍 验证时间窗口:")
    print(f"  历史窗口起点: {time_windows['history_window_start'].isoformat()}")
    print(f"  历史窗口终点: {time_windows['latest_time'].isoformat()}")
    
    hours_diff = (time_windows['latest_time'] - time_windows['history_window_start']).total_seconds() / 3600
    print(f"  时间跨度: {hours_diff:.1f} 小时（应为 25.0 小时，生成 24 个整点数据点）")
    
    # ✅ 修改：应该检查是否为 25 小时（生成 24 个时间槽）
    if abs(hours_diff - 25.0) > 0.1:
        print("❌ 时间跨度不正确！应该是 25 小时")
        return False
    
    # 5. 生成历史数据
    print("\n📊 生成历史数据...")
    text_analyzer = TextAnalyzer()
    keywords = text_analyzer.extract_keywords(df['clean_text'].tolist())
    # ✅ 修改：只取频率最高的 20 个词
    top_keywords = [kw for kw, _ in keywords[:20]]
    
    print(f"  测试关键词: {top_keywords[:5]}...（共 {len(top_keywords)} 个）")
    
    history_analyzer = HistoryAnalyzer()
    history_data = history_analyzer.generate_history_data(df, top_keywords, time_windows)
    
    # 6. 验证历史数据
    print("\n✅ 验证历史数据:")
    
    all_correct = True
    for keyword, data_points in history_data.items():
        print(f"\n  关键词: {keyword}")
        print(f"    数据点数: {len(data_points)} 个")
        
        if len(data_points) != 24:
            print(f"    ❌ 错误：应该有 24 个数据点，但有 {len(data_points)} 个")
            all_correct = False
        else:
            print(f"    ✅ 正确：24 个数据点")
        
        # 显示第一个和最后一个数据点
        if data_points:
            first = data_points[0]
            last = data_points[-1]
            print(f"    第1个: {first['timestamp']} - 频率: {first['frequency']}")
            print(f"    第24个: {last['timestamp']} - 频率: {last['frequency']}")
            
            # 验证时间顺序
            first_dt = datetime.fromisoformat(first['timestamp'].replace('Z', '+00:00'))
            last_dt = datetime.fromisoformat(last['timestamp'].replace('Z', '+00:00'))
            time_span = (last_dt - first_dt).total_seconds() / 3600
            
            if abs(time_span - 23.0) > 0.1:  # 应该相差 23 小时（24 个整点，第 1 到第 24）
                print(f"    ❌ 错误：时间跨度为 {time_span:.1f} 小时，应为 23.0 小时")
                all_correct = False
            else:
                print(f"    ✅ 时间顺序正确")
        
        # 显示所有数据点（便于检查）
        print(f"    所有数据点:")
        total_freq = 0
        for i, point in enumerate(data_points, 1):
            total_freq += point['frequency']
            print(f"      {i:2d}. {point['timestamp']} - {point['frequency']:4d}")
        print(f"    总频率: {total_freq}")
    
    print("\n" + "="*70)
    if all_correct:
        print("✅ 所有测试通过！24 小时历史数据生成正确")
        return True
    else:
        print("❌ 测试失败！请检查历史数据生成逻辑")
        return False
    print("="*70)

if __name__ == "__main__":
    success = test_24hour_history()
    sys.exit(0 if success else 1)
