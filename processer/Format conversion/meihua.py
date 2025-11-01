import pandas as pd
import os


def pretty_display_csv(csv_file, max_rows=50, max_colwidth=50):
    """
    美化显示 CSV 文件内容

    Args:
        csv_file (str): CSV 文件路径
        max_rows (int): 最大显示行数
        max_colwidth (int): 列最大宽度
    """
    try:
        # 读取 CSV 文件
        df = pd.read_csv(csv_file)

        print(f"文件: {csv_file}")
        print(f"形状: {df.shape[0]} 行 × {df.shape[1]} 列")
        print("=" * 80)

        # 设置显示选项
        pd.set_option('display.max_rows', max_rows)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', max_colwidth)
        pd.set_option('display.expand_frame_repr', False)

        # 显示数据
        print(df)

        print("\n" + "=" * 80)
        print("列信息:")
        for i, col in enumerate(df.columns):
            non_null_count = df[col].count()
            null_count = df[col].isnull().sum()
            dtype = df[col].dtype
            print(f"  {i + 1:2d}. {col:<20} | 非空: {non_null_count:>4} | 空值: {null_count:>4} | 类型: {dtype}")

    except Exception as e:
        print(f"错误: {e}")


def create_preview_csv(csv_file, output_file=None, max_rows=100):
    """
    创建格式化的预览文件

    Args:
        csv_file (str): 原始 CSV 文件路径
        output_file (str): 输出文件路径
        max_rows (int): 最大行数
    """
    if output_file is None:
        base_name = os.path.splitext(csv_file)[0]
        output_file = f"{base_name}_preview.txt"

    try:
        df = pd.read_csv(csv_file)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"CSV 文件预览: {csv_file}\n")
            f.write(f"数据形状: {df.shape[0]} 行 × {df.shape[1]} 列\n")
            f.write("=" * 100 + "\n")

            # 写入列名
            columns_line = " | ".join([f"{col:<25}" for col in df.columns])
            f.write(columns_line + "\n")
            f.write("-" * len(columns_line) + "\n")

            # 写入数据行
            for idx, row in df.head(max_rows).iterrows():
                row_line = " | ".join([f"{str(val)[:23]:<25}" for val in row])
                f.write(row_line + "\n")

            if len(df) > max_rows:
                f.write(f"... 还有 {len(df) - max_rows} 行未显示\n")

        print(f"预览文件已生成: {output_file}")

    except Exception as e:
        print(f"错误: {e}")


# 使用示例
if __name__ == "__main__":
    import sys

    current_dir = os.path.dirname(os.path.abspath(__file__))
    analysis_dir = os.path.join(current_dir, '..', 'Analysis')
    os.makedirs(analysis_dir, exist_ok=True)
    output_file = os.path.join(analysis_dir, 'input_data.csv')
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = output_file  # 默认文件

    if os.path.exists(csv_file):
        # 在控制台美化显示
        pretty_display_csv(csv_file)

        # 创建格式化的预览文件
        create_preview_csv(csv_file)
    else:
        print(f"文件 {csv_file} 不存在")
        print("用法: python csv_viewer.py <csv_file>")