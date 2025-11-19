"""
测试 BERT 预测器集成
验证 BERT 模型是否能正常加载和预测
"""
import sys
from pathlib import Path
import pandas as pd

# 添加 Analysis 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from bert_predictor import get_predictor

def test_bert_predictor():
    """测试 BERT 预测器"""
    print("=" * 70)
    print("🧪 测试 BERT 预测器")
    print("=" * 70)
    
    # 获取预测器
    predictor = get_predictor()
    
    # 测试数据
    test_texts = [
        "Bitcoin surges to new all-time high! Buy now!",
        "Market crash incoming, sell everything!",
        "Ethereum price stable, holding support levels",
        "$ETH.X to the moon! 🚀",
        "Bear market continues, heavy losses expected"
    ]
    
    print("\n📝 测试文本:")
    for i, text in enumerate(test_texts, 1):
        print(f"  {i}. {text}")
    
    # 批量预测
    print("\n🔮 执行预测...")
    predictions = predictor.predict_batch(test_texts)
    
    # 显示结果
    print("\n✅ 预测结果:")
    for text, pred in zip(test_texts, predictions):
        print(f"  '{text[:50]}...' → {pred}")
    
    # 测试 DataFrame 填充
    print("\n" + "=" * 70)
    print("🧪 测试 DataFrame 填充")
    print("=" * 70)
    
    test_df = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'text': test_texts,
        'sentiment': ['', '', 'Bullish', '', '']  # 部分缺失
    })
    
    print("\n原始数据:")
    print(test_df[['text', 'sentiment']])
    
    result_df = predictor.fill_missing_sentiments(test_df, text_column='text')
    
    print("\n填充后:")
    print(result_df[['text', 'sentiment']])
    
    print("\n" + "=" * 70)
    print("✨ 测试完成!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_bert_predictor()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
