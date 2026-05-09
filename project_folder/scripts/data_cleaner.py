"""
自动化数据清洗脚本
用途：自动扫描 raw_data 文件夹下所有子文件夹里的所有 CSV，逐一清洗输出
作者：自动生成
"""

import pandas as pd
import numpy as np
import os
import sys
import re
from datetime import datetime
from sqlalchemy import create_engine, text


# ─────────────────────────────────────────────
# 配置区：按需修改
# ─────────────────────────────────────────────

# raw_data 根目录（包含多个子文件夹，每个子文件夹里有 CSV）
# 脚本会自动递归扫描该目录下所有 .csv 文件
RAW_DATA_DIR = r"C:\python\PYTHON\project_folder\raw_data"

# 输出目录（清洗后的文件统一存放在这里，保留子文件夹结构）
OUTPUT_DIR = r"C:\python\PYTHON\project_folder\cleaned_data"

# ── MySQL 连接设置 ──────────────────────────────
MYSQL_HOST     = "localhost"
MYSQL_PORT     = 3306
MYSQL_USER     = "root"
MYSQL_PASSWORD = "123456"
MYSQL_DATABASE = "parks_and_recreation"
# ───────────────────────────────────────────────

# 哪些字符串值应该被视为缺失值（在读取时自动识别）
NA_VALUES = ["na", "NA", "n/a", "N/A", "null", "NULL", "none", "None", "-", "", " "]

# 重复行处理策略："drop_all"（删除所有重复）或 "keep_first" 或 "keep_last"
DUPLICATE_STRATEGY = "keep_first"

# 缺失值处理策略（针对数值列）："report_only" 仅报告，不填充
#   之后你可以扩展为 "fill_mean" / "fill_median" / "fill_zero" 等
NUMERIC_MISSING_STRATEGY = "report_only"

# 字符串列是否自动去除首尾空格
STRIP_WHITESPACE = True

# 列名是否自动标准化（小写 + 去空格 → 下划线）
NORMALIZE_COLUMN_NAMES = True


# ─────────────────────────────────────────────
# 清洗函数
# ─────────────────────────────────────────────

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """将列名统一为小写下划线格式"""
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[\s\-]+", "_", regex=True)
        .str.replace(r"[^\w]", "", regex=True)
    )
    return df


def handle_duplicates(df: pd.DataFrame, strategy: str) -> tuple[pd.DataFrame, int]:
    """检测并处理重复行，返回清洗后的 df 和删除数量"""
    n_before = len(df)
    if strategy == "drop_all":
        df = df.drop_duplicates(keep=False)
    elif strategy == "keep_first":
        df = df.drop_duplicates(keep="first")
    elif strategy == "keep_last":
        df = df.drop_duplicates(keep="last")
    n_removed = n_before - len(df)
    return df, n_removed


def handle_missing(df: pd.DataFrame, strategy: str) -> tuple[pd.DataFrame, dict]:
    """检测缺失值，按策略处理，返回 df 和缺失情况摘要"""
    missing_summary = df.isnull().sum().to_dict()

    if strategy == "report_only":
        pass  # 只记录，不修改
    elif strategy == "fill_mean":
        num_cols = df.select_dtypes(include="number").columns
        for col in num_cols:
            if df[col].isnull().any():
                df[col] = df[col].fillna(df[col].mean())
    elif strategy == "fill_median":
        num_cols = df.select_dtypes(include="number").columns
        for col in num_cols:
            if df[col].isnull().any():
                df[col] = df[col].fillna(df[col].median())
    elif strategy == "fill_zero":
        num_cols = df.select_dtypes(include="number").columns
        df[num_cols] = df[num_cols].fillna(0)

    return df, missing_summary


def strip_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    """去除所有字符串列的首尾空白字符"""
    str_cols = df.select_dtypes(include="str").columns
    for col in str_cols:
        df[col] = df[col].str.strip()
    return df


def infer_and_cast_types(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    尝试将 object 列转换为数值类型。
    无法转换的保留为字符串，转换情况记录在 cast_log 里。
    """
    cast_log = {}
    for col in df.select_dtypes(include=["object", "str"]).columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        # 只有当转换后非空值数量 ≥ 原来非空值数量的 80% 时才接受转换
        original_non_null = df[col].notna().sum()
        converted_non_null = converted.notna().sum()
        if original_non_null > 0 and (converted_non_null / original_non_null) >= 0.8:
            df[col] = converted
            cast_log[col] = f"object → numeric (转换率 {converted_non_null}/{original_non_null})"
    return df, cast_log


def generate_report(filename: str, original_shape: tuple, cleaned_shape: tuple,
                    n_dup_removed: int, missing_summary: dict,
                    cast_log: dict) -> str:
    """生成清洗报告字符串"""
    lines = [
        f"{'='*60}",
        f"文件：{filename}",
        f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"{'='*60}",
        f"原始行数：{original_shape[0]}  →  清洗后：{cleaned_shape[0]}",
        f"列数：{original_shape[1]}",
        f"",
        f"【重复行】删除了 {n_dup_removed} 行（策略：{DUPLICATE_STRATEGY}）",
        f"",
        f"【缺失值（清洗前）】",
    ]
    has_missing = False
    for col, count in missing_summary.items():
        if count > 0:
            lines.append(f"  {col}: {count} 个缺失值")
            has_missing = True
    if not has_missing:
        lines.append("  无缺失值")

    lines += ["", "【类型转换】"]
    if cast_log:
        for col, info in cast_log.items():
            lines.append(f"  {col}: {info}")
    else:
        lines.append("  无需转换")

    lines.append(f"{'='*60}\n")
    return "\n".join(lines)


def get_mysql_engine():
    """建立 MySQL 连接，返回 SQLAlchemy engine"""
    url = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        f"?charset=utf8mb4"
    )
    engine = create_engine(url, echo=False)
    return engine


def csv_filename_to_table_name(filename: str) -> str:
    """
    把 CSV 文件名转换为合法的 MySQL 表名。
    例：annual-value-and-property-tax-by-property-type.csv
        → annual_value_and_property_tax_by_property_type
    """
    name = os.path.splitext(filename)[0]          # 去掉 .csv
    name = re.sub(r"[\s\-]+", "_", name)           # 空格/横线 → 下划线
    name = re.sub(r"[^\w]", "", name)              # 去掉其他非法字符
    name = name.lower()
    name = name[:64]                               # MySQL 表名最长 64 字符
    return name


def upload_to_mysql(df: pd.DataFrame, table_name: str, engine) -> None:
    """将 DataFrame 写入 MySQL，表不存在则自动创建（if_exists='replace'）"""
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",   # 已有同名表则先删除再建新表
        index=False,
        chunksize=500,
    )
    print(f"  🗄️  已写入 MySQL 表：{MYSQL_DATABASE}.{table_name}")


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────

def scan_csv_files(root_dir: str) -> list[str]:
    """递归扫描 root_dir 下所有 .csv 文件，返回绝对路径列表"""
    csv_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.lower().endswith(".csv"):
                csv_files.append(os.path.join(dirpath, fname))
    return sorted(csv_files)


def clean_file(filepath: str, engine) -> None:
    filename = os.path.basename(filepath)

    # 计算相对于 RAW_DATA_DIR 的子路径，用于镜像输出目录结构
    rel_path = os.path.relpath(filepath, RAW_DATA_DIR)
    out_path = os.path.join(OUTPUT_DIR, rel_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    print(f"\n处理中：{rel_path}")

    # 1. 读取 CSV，把常见 na 字符串识别为 NaN
    # keep_default_na=False：只用我们自定义的 NA_VALUES，避免 pandas 默认列表
    # 把 "na" 小写等字符串漏掉不识别
    try:
        df = pd.read_csv(filepath, na_values=NA_VALUES, keep_default_na=False)
    except Exception as e:
        print(f"  ❌ 读取失败：{e}")
        return

    original_shape = df.shape

    # 2. 标准化列名
    if NORMALIZE_COLUMN_NAMES:
        df = normalize_columns(df)

    # 3. 去除字符串列首尾空白
    if STRIP_WHITESPACE:
        df = strip_string_columns(df)

    # 4. 类型推断与转换（把误存为字符串的数字列转回数值）
    df, cast_log = infer_and_cast_types(df)

    # 5. 处理缺失值（记录 + 按策略处理）
    df, missing_summary = handle_missing(df, NUMERIC_MISSING_STRATEGY)

    # 6. 处理重复行
    df, n_dup_removed = handle_duplicates(df, DUPLICATE_STRATEGY)

    cleaned_shape = df.shape

    # 7. 生成报告
    report = generate_report(
        filename=filename,
        original_shape=original_shape,
        cleaned_shape=cleaned_shape,
        n_dup_removed=n_dup_removed,
        missing_summary=missing_summary,
        cast_log=cast_log,
    )
    print(report)

    # 8. 输出清洗后的 CSV（保留原文件名，放在镜像子文件夹里）
    df.to_csv(out_path, index=False)
    print(f"  ✅ 已保存 CSV：{out_path}")

    # 9. 写入 MySQL
    table_name = csv_filename_to_table_name(filename)
    try:
        upload_to_mysql(df, table_name, engine)
    except Exception as e:
        print(f"  ❌ MySQL 写入失败：{e}")


def main():
    # 检查 raw_data 目录是否存在
    if not os.path.isdir(RAW_DATA_DIR):
        print(f"❌ 找不到 raw_data 目录：{RAW_DATA_DIR}")
        print("   请检查 RAW_DATA_DIR 配置是否正确。")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 自动扫描所有 CSV
    csv_files = scan_csv_files(RAW_DATA_DIR)
    if not csv_files:
        print(f"⚠️  在 {RAW_DATA_DIR} 下未找到任何 CSV 文件。")
        sys.exit(0)

    # 建立 MySQL 连接（整个脚本只连接一次）
    print("正在连接 MySQL...")
    try:
        engine = get_mysql_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"✅ MySQL 连接成功：{MYSQL_HOST}/{MYSQL_DATABASE}\n")
    except Exception as e:
        print(f"❌ MySQL 连接失败：{e}")
        print("   请检查 MySQL 是否已启动，以及配置区的帐号密码是否正确。")
        sys.exit(1)

    print(f"=== 自动化数据清洗开始 ===")
    print(f"共发现 {len(csv_files)} 个 CSV 文件\n")

    for filepath in csv_files:
        clean_file(filepath, engine)

    engine.dispose()
    print(f"\n=== 全部完成，清洗结果已保存至：{OUTPUT_DIR} ===")


if __name__ == "__main__":
    main()
