import os
import time
import subprocess
import sys
from main import MainProcessor
from redis_manager import RedisManager


class DataProcessor:
    def __init__(self):
        self.main_processor = MainProcessor()
        self.redis_manager = RedisManager()

        # 获取项目根目录
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.format_conversion_dir = os.path.join(self.base_dir, "Format conversion")
        self.bert_model_dir = os.path.join(self.base_dir, "Bert_Model")
        self.analysis_dir = os.path.join(self.base_dir, "Analysis")

    def run_jsontocsv(self):
        """运行JSON到CSV转换"""
        print("开始JSON到CSV格式转换...")

        try:
            # 构建JsontoCSV.py的路径
            json_to_csv_script = os.path.join(self.format_conversion_dir, "JsontoCSV.py")

            # 输入文件路径（从Redis获取的JSONL文件）
            input_jsonl = os.path.join(self.format_conversion_dir, "input_data.jsonl")
            # 输出文件路径（Bert_Model目录）
            output_csv = os.path.join(self.bert_model_dir, "output_data.csv")

            # 运行JsontoCSV.py
            result = subprocess.run([
                sys.executable, json_to_csv_script,
                input_jsonl, output_csv
            ], capture_output=True, text=True, cwd=self.base_dir)

            if result.returncode == 0:
                print("✅ JSON到CSV转换成功完成!")
                print(result.stdout)
                return True
            else:
                print("❌ JSON到CSV转换失败!")
                print("错误输出:", result.stderr)
                return False

        except Exception as e:
            print(f"❌ 运行JsontoCSV时出错: {e}")
            return False

    def run_bert_prediction(self):
        """运行BERT情感预测"""
        print("开始BERT情感预测...")

        try:
            # 构建predict_bert.py的路径
            predict_script = os.path.join(self.bert_model_dir, "predict_bert.py")
            model_path = os.path.join(self.bert_model_dir, "best_model.pth")

            # 运行predict_bert.py
            result = subprocess.run([
                sys.executable, predict_script, model_path
            ], capture_output=True, text=True, cwd=self.base_dir)

            if result.returncode == 0:
                print("✅ BERT情感预测成功完成!")
                print(result.stdout)
                return True
            else:
                print("❌ BERT情感预测失败!")
                print("错误输出:", result.stderr)
                return False

        except Exception as e:
            print(f"❌ 运行BERT预测时出错: {e}")
            return False

    def process_automatically(self, input_filename="raw_data_latest.json"):
        """完整的自动处理流程"""
        print("=" * 50)
        print("开始完整的数据处理流程...")
        print("=" * 50)

        # 步骤1: 从Redis获取最新数据并保存到本地
        print("\n📥 步骤1: 从Redis获取原始数据...")
        raw_data_path = self.redis_manager.save_raw_data_to_local(input_filename)

        if not raw_data_path:
            print("❌ 无法获取原始数据，流程终止")
            return False

        # 步骤2: 将JSON数据转换为CSV格式（Format conversion → Bert_Model）
        print("\n🔄 步骤2: 格式转换 (JSON → CSV)...")
        if not self.run_jsontocsv():
            print("❌ 格式转换失败，流程终止")
            return False

        # 步骤3: 运行BERT情感预测（生成Analysis/input_data.csv）
        print("\n🤖 步骤3: BERT情感分析预测...")
        if not self.run_bert_prediction():
            print("❌ BERT预测失败，流程终止")
            return False

        # 步骤4: 运行主分析流程（使用预测后的数据）
        print("\n📊 步骤4: 运行数据分析流程...")
        try:
            # 使用BERT预测后生成的数据作为输入
            input_data_path = os.path.join(self.analysis_dir, "input_data.csv")

            self.main_processor.process(
                input_file=input_data_path,
                output_file="output_data.json"
            )
        except Exception as e:
            print(f"❌ 数据分析失败: {e}")
            return False

        print("\n📤 步骤5: 发布结果到Redis哈希...")
        success = self.redis_manager.publish_processed_data()

        if success:
            print("🎉 完整流程执行成功!")
            print("✅ 数据已存储为Redis哈希格式")

            # 验证数据存储
            redis_info = self.redis_manager.get_redis_info()
            if redis_info:
                print(f"✅ processed_data字段数: {redis_info.get('processed_data_fields', 0)}")
                print(f"✅ history_data字段数: {redis_info.get('history_data_fields', 0)}")
        else:
            print("⚠️  流程完成，但发布到Redis失败")

        return success

    def run_periodically(self, interval=300):
        """定期运行完整处理流程"""
        print(f"开始定期处理，间隔: {interval}秒")

        try:
            while True:
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始新一轮完整处理...")
                self.process_automatically()
                print(f"等待 {interval} 秒后继续...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("定期处理已停止")


if __name__ == "__main__":
    processor = DataProcessor()

    # 运行一次完整流程
    success = processor.process_automatically()

    if success:
        print("\n" + "=" * 50)
        print("🎯 完整流程总结:")
        print("  1. 📥 从Redis获取原始JSON数据")
        print("  2. 🔄 Format conversion: JSON → CSV转换")
        print("  3. 🤖 Bert_Model: 情感分析预测")
        print("  4. 📊 Analysis: 词频统计和趋势分析")
        print("  5. 📤 发布分析结果到Redis")
        print("=" * 50)
    else:
        print("\n❌ 完整流程执行失败")

    # 或者运行定期处理（取消注释下面的行）
    # processor.run_periodically(interval=300)  # 5分钟间隔