#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
xmind2csv_new_template 包
- 保持解析业务逻辑不变（基于 xmind2testcase）
- 仅重构导出模板结构与字段定义
"""

from .converter import convert_to_csv, build_rows_from_xmind

__all__ = ["convert_to_csv", "build_rows_from_xmind"]