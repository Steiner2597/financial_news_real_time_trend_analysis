"""
BERT 情感预测器
为缺失 sentiment 的数据提供自动预测
"""
import os
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np

# 标记是否可用
BERT_AVAILABLE = False
model = None
tokenizer = None
device = None
reverse_label_map = None

try:
    import torch
    from torch.utils.data import Dataset, DataLoader
    from transformers import BertTokenizer, BertForSequenceClassification
    BERT_AVAILABLE = True
except ImportError:
    print("⚠️  警告: PyTorch/Transformers 未安装，BERT 预测功能不可用")
    print("   将使用简单规则进行 sentiment 填充")

# 延迟导入，避免循环依赖
try:
    from sentiment_updater import SentimentUpdater
    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False


class BertPredictor:
    """BERT 情感预测器"""
    
    def __init__(self, model_path=None, max_len=256, batch_size=16):
        """
        初始化预测器
        
        Args:
            model_path: 模型文件路径，默认为 ../Bert_Model/best_model.pth
            max_len: 最大序列长度
            batch_size: 批处理大小
        """
        self.max_len = max_len
        self.batch_size = batch_size
        self.model_loaded = False
        
        if not BERT_AVAILABLE:
            print("⚠️  BERT 依赖不可用，预测器将使用简单规则")
            return
        
        # 查找模型路径
        if model_path is None:
            model_path = self._find_model_path()
        
        if model_path is None or not os.path.exists(model_path):
            print(f"⚠️  警告: 找不到 BERT 模型文件，将使用简单规则")
            print(f"   期望路径: {model_path}")
            return
        
        # 加载模型
        try:
            self._load_model(model_path)
            self.model_loaded = True
            print(f"✅ BERT 模型加载成功: {model_path}")
        except Exception as e:
            print(f"⚠️  警告: BERT 模型加载失败: {e}")
            print("   将使用简单规则进行 sentiment 填充")
    
    def _find_model_path(self):
        """查找模型文件"""
        current_dir = Path(__file__).parent
        
        # 尝试多个可能的路径
        possible_paths = [
            current_dir / '..' / 'Bert_Model' / 'best_model.pth',
            current_dir / '..' / '..' / 'Bert_Model' / 'best_model.pth',
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path.resolve())
        
        return None
    
    def _load_model(self, model_path):
        """加载模型"""
        global model, tokenizer, device, reverse_label_map
        
        # 设备选择
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 加载检查点
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        
        # 加载 tokenizer 和标签映射
        tokenizer = checkpoint['tokenizer']
        label_map = checkpoint['label_map']
        config = checkpoint['config']
        
        # 创建模型
        model = BertForSequenceClassification.from_pretrained(
            'bert-base-uncased',
            num_labels=config['num_labels'],
            output_attentions=False,
            output_hidden_states=False
        )
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(device)
        model.eval()
        
        # 反向标签映射
        reverse_label_map = {v: k for k, v in label_map.items()}
    
    def predict_batch(self, texts):
        """
        批量预测文本的情感
        
        Args:
            texts: 文本列表
            
        Returns:
            list: 预测的情感标签列表 (Bullish/Bearish)
        """
        if not self.model_loaded:
            # 使用简单规则
            return [self._simple_sentiment(text) for text in texts]
        
        try:
            # 创建数据集和加载器
            dataset = PredictionDataset(texts, tokenizer, self.max_len)
            data_loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=False)
            
            # 预测
            predictions = []
            with torch.no_grad():
                for batch in data_loader:
                    input_ids = batch['input_ids'].to(device)
                    attention_mask = batch['attention_mask'].to(device)
                    
                    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                    logits = outputs.logits
                    
                    _, preds = torch.max(logits, dim=1)
                    predictions.extend(preds.cpu().tolist())
            
            # 转换为标签
            return [reverse_label_map[p] for p in predictions]
            
        except Exception as e:
            print(f"⚠️  BERT 预测失败: {e}，使用简单规则")
            return [self._simple_sentiment(text) for text in texts]
    
    def _simple_sentiment(self, text):
        """
        简单的启发式情感判断（后备方案）
        
        Args:
            text: 输入文本
            
        Returns:
            str: 'Bullish' 或 'Bearish' 或 ''
        """
        if not text or not isinstance(text, str):
            return ""
        
        text_lower = text.lower()
        
        # 看涨关键词
        bullish_words = ['bull', 'bullish', 'long', 'rally', 'up', 'moon', 'buy', 'gain', 'rise', 'win']
        # 看跌关键词
        bearish_words = ['bear', 'bearish', 'short', 'dump', 'down', 'sell', 'loss', 'fall', 'crash']
        
        bullish_count = sum(1 for word in bullish_words if word in text_lower)
        bearish_count = sum(1 for word in bearish_words if word in text_lower)
        
        if bullish_count > bearish_count and bullish_count > 0:
            return "Bullish"
        elif bearish_count > bullish_count and bearish_count > 0:
            return "Bearish"
        else:
            return ""  # 中性或无法判断
    
    def fill_missing_sentiments(self, df, text_column='text', redis_client=None, queue_name='clean_data_queue'):
        """
        为 DataFrame 中缺失 sentiment 的行填充预测值，并更新 Redis 中对应的数据
        
        Args:
            df: pandas DataFrame
            text_column: 文本列名
            redis_client: Redis 客户端（可选，如果提供则更新 Redis）
            queue_name: Redis 队列名称
            
        Returns:
            pandas DataFrame: 填充后的 DataFrame
        """
        if 'sentiment' not in df.columns:
            df['sentiment'] = ''
        
        # 找出缺失 sentiment 的行
        missing_mask = df['sentiment'].isna() | (df['sentiment'] == '') | (df['sentiment'].str.strip() == '')
        missing_count = missing_mask.sum()
        
        if missing_count == 0:
            print("✓ 所有数据都有 sentiment，无需预测")
            return df
        
        print(f"🔮 发现 {missing_count} 条缺失 sentiment 的数据，开始预测...")
        
        # 提取缺失的文本和对应的索引
        missing_indices = df[missing_mask].index.tolist()
        missing_texts = df.loc[missing_mask, text_column].fillna('').astype(str).tolist()
        
        # 获取记录 ID（用于 Redis 更新）
        id_column = 'id' if 'id' in df.columns else 'post_id' if 'post_id' in df.columns else None
        missing_ids = df.loc[missing_mask, id_column].tolist() if id_column else None
        
        # 批量预测
        predictions = self.predict_batch(missing_texts)
        
        # 填充预测结果
        df.loc[missing_mask, 'sentiment'] = predictions
        
        # ✅ 如果提供了 Redis 客户端，实时更新队列中的数据
        if redis_client is not None and missing_ids and UPDATER_AVAILABLE:
            try:
                from sentiment_updater import SentimentUpdater
                
                print(f"\n📤 正在更新 Redis 中的数据...")
                updater = SentimentUpdater(redis_client=redis_client)
                
                # 构建更新列表
                updates = [
                    {'id': str(record_id), 'sentiment': prediction}
                    for record_id, prediction in zip(missing_ids, predictions)
                    if prediction  # 只更新有预测结果的
                ]
                
                # 批量更新
                if updates:
                    stats = updater.batch_update_sentiments(updates)
                else:
                    print("⚠️  没有有效的预测结果需要更新")
                    stats = {'success': 0, 'failed': 0, 'not_found': 0}
            
            except Exception as e:
                print(f"⚠️  更新 Redis 失败，但预测结果已填充到 DataFrame: {e}")
        
        # 统计预测结果
        predicted_sentiments = pd.Series(predictions).value_counts()
        print(f"\n✓ 预测完成:")
        for sentiment, count in predicted_sentiments.items():
            if sentiment:  # 忽略空字符串
                print(f"  - {sentiment}: {count} 条")
        
        return df


class PredictionDataset(Dataset):
    """预测数据集"""
    
    def __init__(self, texts, tokenizer, max_len=256):
        self.texts = texts
        self.tokenizer = tokenizer
        self.max_len = max_len
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        
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
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten()
        }


# 创建全局单例
_predictor_instance = None

def get_predictor():
    """获取全局预测器实例（单例模式）"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = BertPredictor()
    return _predictor_instance
