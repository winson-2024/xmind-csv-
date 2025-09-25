#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
命令行入口：将 XMind 转换为符合新模板的 CSV

示例：
# 模块执行（推荐）
python -m xmind2csv_new_template.main input.xmind -o output.csv

# 脚本执行
python xmind2csv_new_template/main.py input.xmind -o output.csv
"""

import argparse
import os
import sys

from converter import convert_to_csv


def parse_args():
    parser = argparse.ArgumentParser(
        description="XMind -> CSV 新模板转换（保持原业务逻辑，重构导出模板，支持解析器自动择优）"
    )
    parser.add_argument("xmind_file", help="输入的 .xmind 文件路径")
    parser.add_argument(
        "-o", "--output",
        help="输出 CSV 文件路径（可选，不提供则写入临时目录）",
        default=None
    )
    parser.add_argument(
        "--parser",
        choices=["auto", "xmind2", "xmindlib"],
        default="auto",
        help="选择解析器：auto(默认，自动择优) / xmind2(仅 xmind2testcase) / xmindlib(仅 xmind 库)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    xmind_file = os.path.abspath(args.xmind_file)
    if not os.path.exists(xmind_file):
        print(f"输入文件不存在：{xmind_file}")
        sys.exit(1)

    try:
        csv_path = convert_to_csv(xmind_file, args.output, parser=args.parser)
        print(f"已生成 CSV：{csv_path}")
    except Exception as e:
        print(f"转换失败：{e}")
        sys.exit(2)


if __name__ == "__main__":
    main()