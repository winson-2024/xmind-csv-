# XMind -> CSV 新模板转换工具

保持原有业务逻辑不变（沿用 xmind2testcase 的用例解析结果），仅按照新模板要求导出 CSV，并合并同一用例的多步骤为一条记录。

## 模板字段（顺序固定）
1. 用例名称：用例标题（清洗零宽字符与多余空白）
2. 所属模块：Suite/模块路径（中文括号（）统一为英文括号()）
3. Priority等级：严格沿用原优先级评定体系（importance 1-5 -> P0-P4，兼容字符串'1'-'5'）
4. 用例类型：固定为“功能测试”
5. 前置条件：原用例的前置条件
6. 用例步骤：同一用例内多个步骤以“1. 2. 3.”编号并按换行分隔
7. 预期结果：与步骤一一对应、相同编号并按换行分隔

## 合并规则
- 以“用例名称 + 所属模块”为唯一键，将同一用例的多个步骤合并为一条 CSV 记录（不再拆分多条）。
- 仅当步骤或预期存在内容时才写入对应编号行。

## 优先级规则
- importance: 1/2/3/4/5 -> Priority: P0/P1/P2/P3/P4（兼容 '1'-'5'）
- 完全沿用既有标准，不改变评定体系。

## 安装
```bash
pip install -r xmind2csv_new_template/requirements.txt
```

## 命令行使用
```bash
# 方式1：模块执行（推荐）
python -m xmind2csv_new_template.main input.xmind -o output.csv

# 方式2：脚本执行
python xmind2csv_new_template/main.py input.xmind -o output.csv
```
说明：
- 输出使用 UTF-8 BOM（utf-8-sig）编码，Excel 可直接打开显示中文。
- 未指定 -o 时，将写入系统临时目录并返回绝对路径。

## 作为库调用
```python
from xmind2csv_new_template import convert_to_csv, build_rows_from_xmind

csv_path = convert_to_csv("input.xmind", "output.csv")
rows = build_rows_from_xmind("input.xmind")  # 返回包含表头的二维数组
```

## 设计说明
- 解析来源：xmind2testcase（保持原有业务逻辑与提取规则）
- 导出策略：仅重构表头与合并步骤的输出结构，字段定义清晰、无歧义
- 可无侵入集成到现有系统，或独立命令行使用