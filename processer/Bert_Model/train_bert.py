import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import BertModel, BertTokenizer, BertForSequenceClassification, get_linear_schedule_with_warmup
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.utils.class_weight import compute_class_weight
import os
import time
import datetime
import random
import pickle


# 设置随机种子
def set_seed(seed_value=42):
    random.seed(seed_value)
    np.random.seed(seed_value)
    torch.manual_seed(seed_value)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed_value)


set_seed(42)

# 检查GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {device}")

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"当前目录: {current_dir}")

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

# 数据预处理和清洗
print("数据预处理...")
# 过滤掉文本为空的数据
df = df[df['text'].notna() & (df['text'] != '')]

# 分离有标签和无标签数据
labeled_data = df[df['sentiment'].notna()].copy()
print(f"原始有标签数据: {len(labeled_data)}条")

# 只保留 Bullish 和 Bearish 标签
valid_labels = ['Bullish', 'Bearish']
labeled_data = labeled_data[labeled_data['sentiment'].isin(valid_labels)].copy()

print(f"有效标签数据: {len(labeled_data)}条")
print(f"标签分布: {labeled_data['sentiment'].value_counts().to_dict()}")

# 检查是否有足够的数据
if len(labeled_data) < 10:
    print("错误: 数据量太少，无法训练模型")
    exit()

# 标签映射
label_map = {'Bullish': 0, 'Bearish': 1}
labeled_data['label'] = labeled_data['sentiment'].map(label_map)

# 检查是否有无效标签
if labeled_data['label'].isna().any():
    print("警告: 存在无效标签，正在过滤...")
    labeled_data = labeled_data[labeled_data['label'].notna()]

print(f"最终训练数据: {len(labeled_data)}条")

# 文本预处理
try:
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased', do_lower_case=True)
    print("BERT tokenizer 加载成功")
except Exception as e:
    print(f"加载 tokenizer 失败: {e}")
    exit()


# 创建数据集类
class SentimentDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=256):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

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
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'label': torch.tensor(label, dtype=torch.long)
        }


# 准备训练数据
texts = labeled_data['text'].values
labels = labeled_data['label'].values

# 分割训练集和验证集
try:
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )
    print(f"训练集: {len(train_texts)}条, 验证集: {len(val_texts)}条")
except ValueError as e:
    print(f"数据分割错误: {e}")
    # 如果数据太少无法分层抽样，使用普通分割
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42
    )
    print(f"训练集: {len(train_texts)}条, 验证集: {len(val_texts)}条")

# 创建数据加载器
BATCH_SIZE = 8
MAX_LEN = 256

train_dataset = SentimentDataset(train_texts, train_labels, tokenizer, MAX_LEN)
val_dataset = SentimentDataset(val_texts, val_labels, tokenizer, MAX_LEN)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

# 加载BERT模型
try:
    model = BertForSequenceClassification.from_pretrained(
        'bert-base-uncased',
        num_labels=2,
        output_attentions=False,
        output_hidden_states=False
    )
    model.to(device)
    print("BERT模型加载成功")
except Exception as e:
    print(f"加载BERT模型失败: {e}")
    exit()

# 优化器和调度器
EPOCHS = 10
LEARNING_RATE = 2e-5

optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, eps=1e-8)
total_steps = len(train_loader) * EPOCHS
scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=0,
    num_training_steps=total_steps
)

# 类别权重（处理不平衡）
try:
    class_weights = compute_class_weight('balanced', classes=np.unique(labels), y=labels)
    class_weights = torch.tensor(class_weights, dtype=torch.float).to(device)
    loss_fn = nn.CrossEntropyLoss(weight=class_weights)
    print("类别权重计算成功")
    print(f"类别权重: {class_weights}")
except Exception as e:
    print(f"计算类别权重失败: {e}")
    # 如果计算失败，使用默认损失函数
    loss_fn = nn.CrossEntropyLoss()
    print("使用默认损失函数（无类别权重）")


# 训练函数
def train_epoch(model, data_loader, loss_fn, optimizer, device, scheduler, n_examples):
    model = model.train()
    losses = []
    correct_predictions = 0

    for batch in data_loader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits

        _, preds = torch.max(logits, dim=1)
        loss = loss_fn(logits, labels)

        correct_predictions += torch.sum(preds == labels)
        losses.append(loss.item())

        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad()

    return correct_predictions.double() / n_examples, np.mean(losses)


# 评估函数
def eval_model(model, data_loader, loss_fn, device, n_examples):
    model = model.eval()
    losses = []
    correct_predictions = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in data_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits

            _, preds = torch.max(logits, dim=1)
            loss = loss_fn(logits, labels)

            correct_predictions += torch.sum(preds == labels)
            losses.append(loss.item())
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    return correct_predictions.double() / n_examples, np.mean(losses), all_preds, all_labels


# 训练模型
print("开始训练模型...")
history = []
best_f1 = 0

# 使用相对路径保存模型
best_model_filename = 'best_model.pth'
best_model_path = os.path.join(current_dir, best_model_filename)

for epoch in range(EPOCHS):
    print(f"\nEpoch {epoch + 1}/{EPOCHS}")
    print("-" * 10)

    try:
        train_acc, train_loss = train_epoch(
            model,
            train_loader,
            loss_fn,
            optimizer,
            device,
            scheduler,
            len(train_dataset)
        )

        print(f"训练准确率: {train_acc:.4f}, 训练损失: {train_loss:.4f}")

        val_acc, val_loss, val_preds, val_labels = eval_model(
            model,
            val_loader,
            loss_fn,
            device,
            len(val_dataset)
        )

        # 计算F1分数
        val_f1 = f1_score(val_labels, val_preds, average='weighted')

        print(f"验证准确率: {val_acc:.4f}, 验证损失: {val_loss:.4f}, 验证F1分数: {val_f1:.4f}")

        history.append({
            'epoch': epoch + 1,
            'train_acc': train_acc.item(),
            'train_loss': train_loss,
            'val_acc': val_acc.item(),
            'val_loss': val_loss,
            'val_f1': val_f1
        })

        # 保存最佳模型
        if val_f1 > best_f1:
            best_f1 = val_f1
            print(f"保存最佳模型 (F1: {best_f1:.4f})")

            # 保存模型状态字典和相关信息
            torch.save({
                'model_state_dict': model.state_dict(),
                'tokenizer': tokenizer,
                'label_map': label_map,
                'config': {
                    'num_labels': 2,
                    'max_len': MAX_LEN,
                    'device': device.type
                },
                'best_f1': best_f1,
                'epoch': epoch + 1
            }, best_model_path)

    except Exception as e:
        print(f"训练过程中出现错误: {e}")
        continue

# 输出最终的分类报告
if len(val_labels) > 0 and len(val_preds) > 0:
    print("\n最终验证集分类报告:")
    print(classification_report(val_labels, val_preds, target_names=list(label_map.keys())))
else:
    print("无法生成分类报告：验证集数据为空")

# 保存训练历史
try:
    training_history_path = os.path.join(current_dir, 'training_history.pkl')
    with open(training_history_path, 'wb') as f:
        pickle.dump(history, f)
    print("训练历史已保存")
except Exception as e:
    print(f"保存训练历史失败: {e}")

print(f"\n训练完成! 最佳模型保存在: {best_model_path}")
if best_f1 > 0:
    print(f"最佳F1分数: {best_f1:.4f}")

# 不再保存模型路径文件，直接使用相对路径
print("训练完成!")