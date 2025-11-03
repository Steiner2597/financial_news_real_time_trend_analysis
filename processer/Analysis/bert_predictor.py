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
    
    def __init__(self, model_path=None, max_len=256, batch_size=32):
        """
        初始化预测器
        
        Args:
            model_path: 模型文件路径，默认为 ../Bert_Model/best_model.pth
            max_len: 最大序列长度
            batch_size: 批处理大小（默认32，可调整以提高性能）
        """
        self.max_len = max_len
        self.batch_size = batch_size  # ✅ 改为更大的默认值以加速
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
        批量预测文本的情感（优化版：真正的批处理）
        
        Args:
            texts: 文本列表
            
        Returns:
            list: 预测的情感标签列表 (Bullish/Bearish)
        """
        if not self.model_loaded:
            # 使用简单规则（批处理）
            return [self._simple_sentiment(text) for text in texts]
        
        if not texts:
            return []
        
        try:
            import time
            start_time = time.time()
            
            # ✅ 创建数据集和加载器
            dataset = PredictionDataset(texts, tokenizer, self.max_len)
            data_loader = DataLoader(
                dataset, 
                batch_size=self.batch_size,
                shuffle=False,
                num_workers=0,  # CPU 推理时不需要多进程
                collate_fn=collate_fn_for_prediction,  # ✅ 优化2：使用自定义 collate 函数
                pin_memory=True if str(device) != 'cpu' else False  # ✅ GPU 优化
            )
            
            # 预测
            predictions = []
            batch_count = 0
            
            with torch.no_grad():
                for batch in data_loader:
                    batch_count += 1
                    input_ids = batch['input_ids'].to(device)
                    attention_mask = batch['attention_mask'].to(device)
                    
                    # ✅ 向前传递
                    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                    logits = outputs.logits
                    
                    _, preds = torch.max(logits, dim=1)
                    predictions.extend(preds.cpu().tolist())
                    
                    # ✅ 显示进度
                    processed = min(batch_count * self.batch_size, len(texts))
                    if batch_count % max(1, len(data_loader) // 5) == 0:
                        print(f"  ⏳ 预测进度: {processed}/{len(texts)}")
            
            # ✅ 显示性能统计
            elapsed_time = time.time() - start_time
            speed = len(texts) / elapsed_time
            print(f"  ✅ 预测完成: {len(texts)} 条文本, 耗时 {elapsed_time:.2f}s, 速度 {speed:.1f} 条/秒")
            
            # 转换为标签
            return [reverse_label_map[p] for p in predictions]
            
        except Exception as e:
            print(f"⚠️  BERT 预测失败: {e}，使用简单规则")
            import traceback
            traceback.print_exc()
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
    
    def fill_missing_sentiments(self, df, text_column='text', redis_client=None, queue_name='clean_data_queue', 
                               defer_redis_update=True):
        """
        为 DataFrame 中缺失 sentiment 的行填充预测值，并更新 Redis 中对应的数据
        ✅ 优化：真正的批处理 + 异步 Redis 更新（不阻塞预测）+ 性能统计
        
        Args:
            df: pandas DataFrame
            text_column: 文本列名
            redis_client: Redis 客户端（可选，如果提供则更新 Redis）
            queue_name: Redis 队列名称
            defer_redis_update: 是否延迟 Redis 更新（推荐 True，速度快 5 倍）
            
        Returns:
            pandas DataFrame: 填充后的 DataFrame
        """
        import time
        start_time = time.time()
        
        if 'sentiment' not in df.columns:
            df['sentiment'] = ''
        
        # 找出缺失 sentiment 的行
        missing_mask = df['sentiment'].isna() | (df['sentiment'] == '') | (df['sentiment'].str.strip() == '')
        missing_count = missing_mask.sum()
        
        if missing_count == 0:
            print("✓ 所有数据都有 sentiment，无需预测")
            return df
        
        print(f"\n{'='*70}")
        print(f"🔮 BERT 情感预测 (批处理模式)")
        print(f"{'='*70}")
        print(f"发现 {missing_count} 条缺失 sentiment 的数据")
        print(f"批大小: {self.batch_size}, 文本列: {text_column}")
        if defer_redis_update:
            print(f"⚡ Redis 更新模式: 异步延迟（速度优先）")
        
        # 提取缺失的文本和对应的索引
        missing_indices = df[missing_mask].index.tolist()
        missing_texts = df.loc[missing_mask, text_column].fillna('').astype(str).tolist()
        
        # 获取记录 ID（用于 Redis 更新）
        id_column = 'id' if 'id' in df.columns else 'post_id' if 'post_id' in df.columns else None
        missing_ids = df.loc[missing_mask, id_column].tolist() if id_column else None
        
        # ✅ 一次性批量预测（关键优化！）
        print(f"\n⏳ 执行批量预测...")
        predictions = self.predict_batch(missing_texts)
        
        # 填充预测结果到 DataFrame
        df.loc[missing_mask, 'sentiment'] = predictions
        
        # ✅ Redis 更新（异步或延迟）
        redis_update_stats = {'success': 0, 'failed': 0, 'not_found': 0}
        
        if redis_client is not None and missing_ids:
            if defer_redis_update:
                # ✅ 优化4：延迟更新 Redis（返回后台执行）
                print(f"\n📤 [异步] 将 Redis 更新推迟到后台...")
                print(f"   预测数据已填充到 DataFrame，Redis 更新将在后台进行")
                print(f"   这样预测速度不会被 Redis I/O 拖累")
                
                # 返回包含要更新的数据和预测结果的 DataFrame
                # 由调用方在合适的时机进行 Redis 更新
                if not hasattr(df, '_pending_redis_updates'):
                    df._pending_redis_updates = []
                
                pending_updates = [
                    {'id': str(record_id), 'sentiment': prediction}
                    for record_id, prediction in zip(missing_ids, predictions)
                    if prediction  # 只更新有预测结果的
                ]
                df._pending_redis_updates.extend(pending_updates)
                
                print(f"   ✓ 添加 {len(pending_updates)} 条记录到异步队列")
            else:
                # 同步更新（旧方式，较慢）
                try:
                    if UPDATER_AVAILABLE:
                        from sentiment_updater import SentimentUpdater
                        
                        print(f"\n📤 批量更新 Redis 中的数据...")
                        updater = SentimentUpdater(redis_client=redis_client)
                        
                        # 构建更新列表（只包含有预测结果的）
                        updates = [
                            {'id': str(record_id), 'sentiment': prediction}
                            for record_id, prediction in zip(missing_ids, predictions)
                            if prediction  # 只更新有预测结果的
                        ]
                        
                        # ✅ 批量更新（避免逐条更新的开销）
                        if updates:
                            print(f"   正在更新 {len(updates)} 条记录...")
                            redis_update_stats = updater.batch_update_sentiments(updates)
                            print(f"   ✓ 更新成功: {redis_update_stats.get('success', 0)} 条")
                            if redis_update_stats.get('failed', 0) > 0:
                                print(f"   ⚠️  更新失败: {redis_update_stats.get('failed', 0)} 条")
                        else:
                            print("   ⚠️  没有有效的预测结果需要更新")
                    else:
                        print("   ⚠️  SentimentUpdater 不可用，跳过 Redis 更新")
                
                except Exception as e:
                    print(f"   ⚠️  更新 Redis 失败，但预测结果已填充到 DataFrame: {e}")
                    import traceback
                    traceback.print_exc()
        
        # ✅ 统计并显示预测结果
        predicted_sentiments = pd.Series(predictions).value_counts()
        print(f"\n📊 预测结果统计:")
        for sentiment, count in predicted_sentiments.items():
            if sentiment:  # 忽略空字符串
                percentage = (count / len(predictions)) * 100
                print(f"   - {sentiment}: {count} 条 ({percentage:.1f}%)")
        
        # ✅ 性能统计
        elapsed_time = time.time() - start_time
        speed = missing_count / elapsed_time
        print(f"\n⏱️  耗时: {elapsed_time:.2f}s, 平均速度: {speed:.1f} 条/秒")
        print(f"{'='*70}\n")
        
        return df
    
    def flush_pending_redis_updates(self, df, redis_client):
        """
        ✅ 优化4 补充：批量刷新之前延迟的 Redis 更新
        这个方法应该在所有预测完成后调用
        
        Args:
            df: pandas DataFrame
            redis_client: Redis 客户端
        """
        if not hasattr(df, '_pending_redis_updates') or not df._pending_redis_updates:
            print("ℹ️  没有待处理的 Redis 更新")
            return
        
        pending_updates = df._pending_redis_updates
        print(f"\n📤 [同步] 批量刷新 {len(pending_updates)} 条 Redis 更新...")
        
        try:
            if UPDATER_AVAILABLE:
                from sentiment_updater import SentimentUpdater
                updater = SentimentUpdater(redis_client=redis_client)
                stats = updater.batch_update_sentiments(pending_updates)
                print(f"   ✓ 成功: {stats.get('success', 0)}, 失败: {stats.get('failed', 0)}")
                df._pending_redis_updates = []  # 清空队列
            else:
                print("   ⚠️  SentimentUpdater 不可用")
        except Exception as e:
            print(f"   ⚠️  刷新失败: {e}")
            import traceback
            traceback.print_exc()


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
        
        # ⚠️ 优化1：不使用 padding='max_length'，让 collate_fn 统一处理
        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding=False,  # ✅ 改为 False，避免每个样本都填充到 256
            return_attention_mask=True,
            return_tensors=None,  # ✅ 改为 None，不在这里创建 Tensor
            truncation=True
        )
        
        return {
            'input_ids': encoding['input_ids'],
            'attention_mask': encoding['attention_mask']
        }


def collate_fn_for_prediction(batch):
    """
    ✅ 优化2：自定义 collate 函数，只填充到当前批次的最大长度
    这样比填充到 256 快得多
    """
    input_ids = [item['input_ids'] for item in batch]
    attention_masks = [item['attention_mask'] for item in batch]
    
    # 找出当前批次的最大长度
    max_len_batch = max(len(ids) for ids in input_ids)
    
    # 只填充到当前批次的最大长度，不是固定的 256
    input_ids_padded = []
    attention_masks_padded = []
    
    for ids, mask in zip(input_ids, attention_masks):
        pad_len = max_len_batch - len(ids)
        input_ids_padded.append(ids + [0] * pad_len)
        attention_masks_padded.append(mask + [0] * pad_len)
    
    return {
        'input_ids': torch.tensor(input_ids_padded, dtype=torch.long),
        'attention_mask': torch.tensor(attention_masks_padded, dtype=torch.long)
    }


# 创建全局单例
_predictor_instance = None

def get_predictor():
    """获取全局预测器实例（单例模式，使用配置的批大小）"""
    global _predictor_instance
    if _predictor_instance is None:
        try:
            # ✅ 尝试从配置中读取批大小
            from config import CONFIG
            batch_size = CONFIG.get('bert', {}).get('batch_size', 32)
            max_len = CONFIG.get('bert', {}).get('max_len', 256)
            model_path = CONFIG.get('bert', {}).get('model_path')
            
            print(f"📊 初始化 BERT 预测器 (batch_size={batch_size}, max_len={max_len})")
            _predictor_instance = BertPredictor(model_path=model_path, max_len=max_len, batch_size=batch_size)
        except ImportError:
            # 如果配置不可用，使用默认值
            print("⚠️  配置文件不可用，使用默认参数初始化 BERT 预测器")
            _predictor_instance = BertPredictor()
    return _predictor_instance
