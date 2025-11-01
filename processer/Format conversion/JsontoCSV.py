import json
import pandas as pd
import sys
import os
from datetime import datetime


def jsonl_to_csv(input_file, output_file=None):
    """
    将 JSONL 文件转换为 CSV 格式

    Args:
        input_file (str): 输入的 JSONL 文件路径
        output_file (str): 输出的 CSV 文件路径，如果为 None 则自动生成
    """

    # 如果未指定输出文件，自动生成
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}.csv"

    print(f"开始转换: {input_file} -> {output_file}")

    # 读取 JSONL 文件
    data = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        item = json.loads(line)
                        data.append(item)
                    except json.JSONDecodeError as e:
                        print(f"警告: 第 {line_num} 行 JSON 解析错误: {e}")
                        continue

        print(f"成功读取 {len(data)} 条记录")

        if not data:
            print("错误: 没有读取到有效数据")
            return False

        # 转换为 DataFrame
        df = pd.DataFrame(data)

        # 重命名字段以符合你的数据格式说明
        column_mapping = {
            'id': 'id',
            'source': 'source',
            'created_at': 'created_at',
            'timestamp': 'timestamp',
            'title': 'title',
            'text': 'text',
            'author': 'author',
            'score': 'score',
            'comments': 'comments',
            'sentiment': 'sentiment',
            'tags': 'tags',
            'url': 'url',
            'subreddit': 'subreddit',
            'symbol': 'symbol',
            'symbols': 'symbols',
            'user_followers': 'user_followers'
        }

        # 只保留我们需要的列
        available_columns = [col for col in column_mapping.keys() if col in df.columns]
        df = df[available_columns]

        # 重命名列
        df = df.rename(columns=column_mapping)

        # 处理时间格式
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')

        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # 处理 tags 字段（如果是列表，转换为逗号分隔的字符串）
        if 'tags' in df.columns:
            df['tags'] = df['tags'].apply(
                lambda x: ', '.join(x) if isinstance(x, list) else x
            )

        # 处理 symbols 字段（如果是列表，转换为逗号分隔的字符串）
        if 'symbols' in df.columns:
            df['symbols'] = df['symbols'].apply(
                lambda x: ', '.join(x) if isinstance(x, list) else x
            )

        # 保存为 CSV
        df.to_csv(output_file, index=False, encoding='utf-8')

        print(f"转换完成！输出文件: {output_file}")
        print(f"数据统计:")
        print(f"  - 总记录数: {len(df)}")
        print(f"  - 列数: {len(df.columns)}")
        print(f"  - 列名: {', '.join(df.columns)}")

        # 显示数据预览
        print("\n数据预览:")
        print(df.head())

        return True

    except FileNotFoundError:
        print(f"错误: 输入文件 {input_file} 不存在")
        return False
    except Exception as e:
        print(f"错误: 转换过程中发生错误: {e}")
        return False


def main():
    """主函数"""
    # 支持命令行参数
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # 如果没有参数，使用默认文件名
        input_file = "../Format conversion/input_data.jsonl"
        output_file = "../Bert_Model/output_data.csv"

    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 输入文件 {input_file} 不存在")
        print("用法: python jsonl_to_csv.py <input.jsonl> [output.csv]")
        return

    # 执行转换
    success = jsonl_to_csv(input_file, output_file)

    if success:
        print("\n转换成功！")
    else:
        print("\n转换失败！")


if __name__ == "__main__":
    main()