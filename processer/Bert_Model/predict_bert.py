import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification
import os
import pickle
import sys

# 检查GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {device}")

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"当前目录: {current_dir}")


# 模型路径查找策略
def find_model_path():
    """查找模型文件的多种策略"""
    # 1. 检查命令行参数
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
        if os.path.exists(model_path):
            print(f"使用命令行参数指定的模型路径: {model_path}")
            return model_path

    # 2. 检查当前目录
    current_dir_model = os.path.join(current_dir, 'best_model.pth')
    if os.path.exists(current_dir_model):
        print(f"使用当前目录下的模型: {current_dir_model}")
        return current_dir_model

    # 3. 检查上级目录
    parent_dir_model = os.path.join(current_dir, '..', 'best_model.pth')
    if os.path.exists(parent_dir_model):
        print(f"使用上级目录下的模型: {parent_dir_model}")
        return parent_dir_model

    # 4. 检查 best_model_path.txt
    model_path_file = os.path.join(current_dir, 'best_model_path.txt')
    if os.path.exists(model_path_file):
        with open(model_path_file, 'r') as f:
            model_path = f.read().strip()
            if os.path.exists(model_path):
                print(f"使用 best_model_path.txt 中指定的模型: {model_path}")
                return model_path

    return None


# 查找模型路径
model_path = find_model_path()
if model_path is None:
    print("错误: 找不到模型文件，请确保 best_model.pth 文件存在")
    print("可以尝试以下方法:")
    print("1. 将模型文件放在当前目录下")
    print("2. 使用命令行参数指定模型路径: python predict_bert.py /path/to/best_model.pth")
    exit(1)

print(f"加载模型: {model_path}")

# 加载模型和相关信息
try:
    # 加载保存的检查点 - 修复：添加 weights_only=False
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)

    # 加载tokenizer和标签映射
    tokenizer = checkpoint['tokenizer']
    label_map = checkpoint['label_map']
    config = checkpoint['config']

    # 创建模型并加载状态字典
    model = BertForSequenceClassification.from_pretrained(
        'bert-base-uncased',
        num_labels=config['num_labels'],
        output_attentions=False,
        output_hidden_states=False
    )
    model.load_state_dict(checkpoint['model_state_dict'])

    reverse_label_map = {v: k for k, v in label_map.items()}
    print(f"加载模型成功! 标签映射: {label_map}")
    print(f"最佳F1分数: {checkpoint.get('best_f1', 'N/A')}")
    print(f"训练轮次: {checkpoint.get('epoch', 'N/A')}")
except Exception as e:
    print(f"加载模型失败: {e}")
    print("如果仍然失败，请确保模型文件来源可信")
    exit(1)

model.to(device)
model.eval()

# 加载数据
print("加载数据...")

# 尝试多种可能的CSV文件路径
possible_csv_paths = [
    'output_data.csv',
    os.path.join(current_dir, 'output_data.csv'),
    '../output_data.csv'
]

df = None
for csv_path in possible_csv_paths:
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        print(f"成功加载数据: {csv_path}")
        break

if df is None:
    print("错误: 找不到 output_data.csv 文件")
    exit()

# 分离有标签和无标签数据
labeled_data = df[df['sentiment'].notna()].copy()
unlabeled_data = df[df['sentiment'].isna()].copy()

print(f"有标签数据: {len(labeled_data)}条")
print(f"无标签数据: {len(unlabeled_data)}条")


# 创建预测数据集类
class PredictionDataset(Dataset):
    def __init__(self, texts, ids, tokenizer, max_len=256):
        self.texts = texts
        self.ids = ids
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        id = self.ids[idx]

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding='max_length',
            return_attention_mask=True,
            return_tensors='pt',
            truncation=True
        )

        return {
            'text': text,
            'id': id,
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten()
        }


# 预测函数
def predict(model, data_loader, device):
    model = model.eval()
    predictions = []
    probabilities = []
    ids = []

    with torch.no_grad():
        for batch in data_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            batch_ids = batch['id']

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits

            # 获取预测标签和概率
            _, preds = torch.max(logits, dim=1)
            probs = torch.softmax(logits, dim=1)

            predictions.extend(preds.cpu().tolist())
            probabilities.extend(probs.cpu().tolist())
            ids.extend(batch_ids)

    return ids, predictions, probabilities


# 对无标签数据进行预测
if len(unlabeled_data) > 0:
    print("开始预测无标签数据...")

    # 准备数据
    texts = unlabeled_data['text'].values
    ids = unlabeled_data['id'].values

    # 创建数据加载器
    BATCH_SIZE = 16
    MAX_LEN = 256

    dataset = PredictionDataset(texts, ids, tokenizer, MAX_LEN)
    data_loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False)

    # 预测
    ids, predictions, probabilities = predict(model, data_loader, device)

    # 创建预测结果DataFrame
    pred_df = pd.DataFrame({
        'id': ids,
        'predicted_sentiment': [reverse_label_map[p] for p in predictions],
        'sentiment_probability': [max(prob) for prob in probabilities],
        'bullish_probability': [prob[0] for prob in probabilities],
        'bearish_probability': [prob[1] for prob in probabilities]
    })

    print(f"预测完成! 预测结果分布:")
    print(pred_df['predicted_sentiment'].value_counts())

    # 将预测结果合并到原始数据
    print("合并预测结果...")

    # 创建一个副本避免修改原始数据
    result_df = df.copy()

    # 为有标签数据添加预测相关列（保持原有标签）
    result_df.loc[result_df['sentiment'].notna(), 'predicted_sentiment'] = result_df['sentiment']
    result_df.loc[result_df['sentiment'].notna(), 'sentiment_probability'] = 1.0
    result_df.loc[result_df['sentiment'] == 'Bullish', 'bullish_probability'] = 1.0
    result_df.loc[result_df['sentiment'] == 'Bullish', 'bearish_probability'] = 0.0
    result_df.loc[result_df['sentiment'] == 'Bearish', 'bullish_probability'] = 0.0
    result_df.loc[result_df['sentiment'] == 'Bearish', 'bearish_probability'] = 1.0

    # 为无标签数据添加预测结果
    for _, row in pred_df.iterrows():
        mask = result_df['id'] == row['id']
        result_df.loc[mask, 'sentiment'] = row['predicted_sentiment']
        result_df.loc[mask, 'predicted_sentiment'] = row['predicted_sentiment']
        result_df.loc[mask, 'sentiment_probability'] = row['sentiment_probability']
        result_df.loc[mask, 'bullish_probability'] = row['bullish_probability']
        result_df.loc[mask, 'bearish_probability'] = row['bearish_probability']

    # 保存结果到 Analysis/input_data.csv
    analysis_dir = os.path.join(current_dir, '..', 'Analysis')
    os.makedirs(analysis_dir, exist_ok=True)
    output_file = os.path.join(analysis_dir, 'input_data.csv')
    result_df.to_csv(output_file, index=False)
    print(f"结果已保存到 {output_file}")

    # 统计最终结果
    print(f"\n最终情感分布:")
    print(result_df['sentiment'].value_counts())

    print(f"\n预测结果统计:")
    print(f"高置信度预测 (>=0.8): {len(result_df[result_df['sentiment_probability'] >= 0.8])}")
    print(
        f"中等置信度预测 (0.5-0.8): {len(result_df[(result_df['sentiment_probability'] >= 0.5) & (result_df['sentiment_probability'] < 0.8)])}")
    print(f"低置信度预测 (<0.5): {len(result_df[result_df['sentiment_probability'] < 0.5])}")

else:
    print("没有无标签数据需要预测")
    # 如果没有无标签数据，直接保存原始数据到 Analysis/input_data.csv
    analysis_dir = os.path.join(current_dir, '..', 'Analysis')
    os.makedirs(analysis_dir, exist_ok=True)
    output_file = os.path.join(analysis_dir, 'input_data.csv')
    df.to_csv(output_file, index=False)
    print(f"数据已保存到 {output_file}")

print("预测过程完成!")