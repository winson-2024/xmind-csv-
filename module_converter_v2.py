#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
XMind -> 模块化用例CSV 转换器 V2 - 优化版本

修复问题：
1. 正确提取XMind一级主标题作为模块名
2. 去除文件名中的UUID前缀
3. 格式化步骤文本：去除引号，添加序号
4. 修复XMind解析中的类型错误

CSV格式：
模块,自定义分级模块,用例名称,priority,前置条件,用例步骤,预期结果
"""

import csv
import os
import re
import tempfile
import uuid
import datetime
from typing import Dict, List, Tuple, Optional, Any

import xmind
from xmind2testcase.utils import get_xmind_testcase_list


def _sanitize_text(text: str) -> str:
    """基础清洗：去除 None、零宽字符、所有空白符合并为一个空格"""
    if not text:
        return ""
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", str(text))
    text = re.sub(r"\s+", " ", text.strip())
    return text


def _sanitize_multiline_text(text: str) -> str:
    """多行文本清洗：保留换行符，但清理每行的多余空白"""
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    lines = text.split('\n')
    processed_lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in lines]
    processed_lines = [line for line in processed_lines if line]
    return "\n".join(processed_lines)


def _normalize_priority(value) -> str:
    """
    将多种优先级表示统一为P0-P4格式
    支持：1-5, P0-P4, 高中低, High/Medium/Low等
    """
    if value is None:
        return "P2"
    
    v = str(value).strip().upper()
    
    # 直接是 P0-4
    if re.fullmatch(r"P[0-4]", v):
        return v
    
    # 纯数字 1-5
    if re.fullmatch(r"[1-5]", v):
        priority_map = {"1": "P0", "2": "P1", "3": "P2", "4": "P3", "5": "P4"}
        return priority_map.get(v, "P2")
    
    # 可能是整数
    try:
        iv = int(v)
        if 1 <= iv <= 5:
            priority_map = {1: "P0", 2: "P1", 3: "P2", 4: "P3", 5: "P4"}
            return priority_map.get(iv, "P2")
    except Exception:
        pass
    
    # 处理"优先级X"格式
    priority_match = re.search(r'优先级[：:\s]*([1-5])', v)
    if priority_match:
        priority_map = {"1": "P0", "2": "P1", "3": "P2", "4": "P3", "5": "P4"}
        return priority_map.get(priority_match.group(1), "P2")
    
    # 处理中文描述
    if "高" in v or "严重" in v or "紧急" in v:
        return "P0"
    if "较高" in v or "重要" in v:
        return "P1"
    if "中" in v or "普通" in v:
        return "P2"
    if "较低" in v or "次要" in v:
        return "P3"
    if "低" in v or "微小" in v or "提示" in v:
        return "P4"
    
    # 处理英文描述
    if "CRITICAL" in v or "HIGH" in v:
        return "P0"
    if "MAJOR" in v:
        return "P1"
    if "MEDIUM" in v or "NORMAL" in v:
        return "P2"
    if "MINOR" in v:
        return "P3"
    if "LOW" in v or "TRIVIAL" in v:
        return "P4"
    
    return "P2"


def _extract_module_name(xmind_file: str) -> str:
    """
    规则1：模块字段提取
    优先使用XMind一级主标题，如果获取失败则使用文件名
    """
    try:
        # 尝试从XMind文件中提取一级主标题
        workbook = xmind.load(xmind_file)
        sheet = workbook.getPrimarySheet()
        if sheet:
            root = sheet.getRootTopic()
            if root:
                root_title = root.getTitle()
                if root_title and root_title.strip():
                    return _sanitize_text(root_title.strip())
    except Exception:
        # 如果提取失败，使用文件名
        pass
    
    # 备用方案：使用文件名（去掉UUID前缀和扩展名）
    filename = os.path.basename(xmind_file)
    # 去掉UUID前缀（如果存在）
    if '_' in filename:
        parts = filename.split('_')
        if len(parts) > 1 and len(parts[0]) == 36:  # UUID长度为36
            filename = '_'.join(parts[1:])
    
    module_name = filename.replace('.xmind', '').replace('.xml', '')
    return _sanitize_text(module_name)


def _extract_priority_from_topic(topic) -> str:
    """从XMind主题中提取优先级信息 - 修复版本"""
    # 1. 检查标题中的优先级标记
    title = topic.getTitle() or ""
    priority_match = re.search(r'\b(P[0-4]|[1-5])\b', title)
    if priority_match:
        return _normalize_priority(priority_match.group(1))
    
    # 2. 检查标签(markers)中的优先级 - 修复类型错误
    try:
        markers = topic.getMarkers() or []
        for marker in markers:
            try:
                # 安全获取marker ID
                if hasattr(marker, 'getMarkerId'):
                    marker_id = str(marker.getMarkerId())
                else:
                    marker_id = str(marker)
                
                # 检查优先级相关标记
                if marker_id and ('priority' in marker_id.lower() or 'importance' in marker_id.lower()):
                    num_match = re.search(r'(\d+)', marker_id)
                    if num_match:
                        return _normalize_priority(num_match.group(1))
            except Exception:
                # 忽略单个marker的错误，继续处理下一个
                continue
    except Exception:
        # 忽略markers处理错误
        pass
    
    # 3. 检查备注中的优先级信息
    try:
        notes = topic.getNotes() or ""
        priority_in_notes = re.search(r'\b(P[0-4]|优先级[：:]\s*([1-5]))\b', str(notes))
        if priority_in_notes:
            if priority_in_notes.group(1).startswith('P'):
                return _normalize_priority(priority_in_notes.group(1))
            else:
                return _normalize_priority(priority_in_notes.group(2))
    except Exception:
        pass
    
    return "P2"


def _extract_custom_module_path(topic, path_list: List[str]) -> str:
    """
    规则2：自定义分级模块提取
    构建层级路径，用"/"分隔符连接
    """
    if not path_list:
        return ""
    return "/".join(path_list)


def _format_step_text(text: str) -> str:
    """
    格式化步骤文本：去除前后引号，为每个标题添加序号（如果没有的话）
    
    处理规则：
    1. 去除前后引号
    2. 为每个步骤添加序号，若已有序号则保留
    3. 支持多行步骤处理
    """
    if not text:
        return ""
    
    # 去除前后引号
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    if text.startswith("'") and text.endswith("'"):
        text = text[1:-1]
    
    # 按换行符分割成多行
    lines = text.split('\n')
    formatted_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # 检查是否已经有序号（数字+点号开头）
        if re.match(r'^\d+[\.\、]\s*', line):
            # 已有序号，保留原样
            formatted_lines.append(line)
        else:
            # 没有序号，添加序号
            formatted_lines.append(f"{i+1}.{line}")
    
    return '\n'.join(formatted_lines)


def _parse_module_cases_from_xmind(xmind_file: str) -> List[Dict[str, Any]]:
    """
    使用xmind库解析XMind文件，按照模块化用例规则提取数据
    """
    try:
        workbook = xmind.load(xmind_file)
        sheet = workbook.getPrimarySheet()
        if sheet is None:
            return []
        root = sheet.getRootTopic()
        
        module_name = _extract_module_name(xmind_file)
        all_cases = []
        
        def extract_cases(topic, module_path_list: List[str]):
            if not topic:
                return
                
            raw_title = topic.getTitle() or ""
            title = _sanitize_text(raw_title)
            if not title:
                return
            
            sub_topics = topic.getSubTopics() or []
            
            # 判断是否为测试用例节点
            # 启发式规则：如果子节点主要是步骤类型（简单节点），则当前节点是测试用例
            is_testcase = False
            if sub_topics:
                simple_children_count = 0
                for st in sub_topics:
                    if st and st.getTitle():
                        grandchildren = st.getSubTopics() or []
                        if not grandchildren or all(not gc.getSubTopics() for gc in grandchildren):
                            simple_children_count += 1
                
                if len(sub_topics) > 0 and simple_children_count / len(sub_topics) > 0.6:
                    is_testcase = True
            
            if is_testcase:
                # 当前节点是测试用例
                custom_module_path = _extract_custom_module_path(topic, module_path_list)
                
                # 提取前置条件
                preconditions = ""
                topic_notes = topic.getNotes()
                if topic_notes:
                    preconditions = _sanitize_multiline_text(topic_notes)
                
                # 提取步骤和预期结果
                steps_data = []
                for child_topic in sub_topics:
                    child_title = _sanitize_multiline_text(child_topic.getTitle() or "")
                    
                    # 特殊处理前置条件节点
                    if child_title.lower().strip() in ["前置条件", "preconditions", "前置"]:
                        if preconditions:
                            preconditions += "\n" + _sanitize_multiline_text(child_topic.getNotes() or "")
                        else:
                            preconditions = _sanitize_multiline_text(child_topic.getNotes() or "")
                        
                        if not preconditions and child_topic.getSubTopics():
                            first_grandchild = child_topic.getSubTopics()[0]
                            if first_grandchild:
                                preconditions = _sanitize_multiline_text(first_grandchild.getTitle() or "")
                        continue
                    
                    # 处理步骤节点
                    action = child_title
                    expected_results = []
                    for gc in (child_topic.getSubTopics() or []):
                        if gc and not gc.getSubTopics():
                            expected_results.append(_sanitize_multiline_text(gc.getTitle() or ""))
                    
                    expected = "\n".join(expected_results)
                    if action or expected:
                        steps_data.append((action, expected))
                
                # 提取优先级
                priority = _extract_priority_from_topic(topic)
                
                all_cases.append({
                    "module": module_name,
                    "custom_module": custom_module_path,
                    "title": title,
                    "priority": priority,
                    "preconditions": preconditions if preconditions else "",
                    "steps": steps_data
                })
            else:
                # 当前节点是模块节点，继续递归
                new_module_path = module_path_list + [title]
                for st in sub_topics:
                    extract_cases(st, new_module_path)
        
        # 从根节点的子节点开始遍历
        for topic in (root.getSubTopics() or []):
            extract_cases(topic, [])
        
        return all_cases
        
    except Exception as e:
        print(f"解析XMind文件时出错: {str(e)}")
        return []


def _parse_module_cases_from_xmind2testcase(xmind_file: str) -> List[Dict[str, Any]]:
    """
    使用xmind2testcase解析，转换为模块化用例格式
    作为备用解析方案
    """
    try:
        testcases = get_xmind_testcase_list(xmind_file)
        module_name = _extract_module_name(xmind_file)
        all_cases = []
        
        for tc in testcases:
            steps = []
            for step in (tc.get("steps", []) or []):
                action = _sanitize_multiline_text(step.get("actions", "") or "")
                expected = _sanitize_multiline_text(step.get("expectedresults", "") or "")
                if action or expected:
                    steps.append((action, expected))
            
            # 从suite字段提取自定义模块路径
            suite = tc.get("suite", "") or ""
            custom_module = _sanitize_text(suite) if suite != "/" else ""
            
            all_cases.append({
                "module": module_name,
                "custom_module": custom_module,
                "title": _sanitize_text(tc.get("name", "") or ""),
                "priority": _normalize_priority(tc.get("importance")),
                "preconditions": _sanitize_multiline_text(tc.get("preconditions", "") or ""),
                "steps": steps
            })
        
        return all_cases
        
    except Exception as e:
        print(f"使用xmind2testcase解析时出错: {str(e)}")
        return []


def get_module_cases(xmind_file: str, parser: str = "auto") -> List[Dict[str, Any]]:
    """
    获取模块化用例数据
    parser: "auto", "xmind", "xmind2testcase"
    """
    if parser == "xmind":
        return _parse_module_cases_from_xmind(xmind_file)
    elif parser == "xmind2testcase":
        return _parse_module_cases_from_xmind2testcase(xmind_file)
    else:
        # auto模式：优先使用xmind库，失败时使用xmind2testcase
        cases = _parse_module_cases_from_xmind(xmind_file)
        if not cases:
            cases = _parse_module_cases_from_xmind2testcase(xmind_file)
        return cases


def build_module_csv_rows(cases: List[Dict[str, Any]]) -> List[List[str]]:
    """
    构建模块化用例CSV行数据
    表头：模块,自定义分级模块,用例名称,priority,前置条件,用例步骤,预期结果
    """
    headers = ["模块", "自定义分级模块", "用例名称", "priority", "前置条件", "用例步骤", "预期结果"]
    rows = [headers]
    
    for case in cases:
        # 处理步骤和预期结果
        steps_lines = []
        expected_lines = []
        
        for action, expected in case.get("steps", []):
            if action:
                steps_lines.append(action)
            if expected:
                expected_lines.append(expected)
        
        # 用换行符连接多个步骤
        steps_text = "\n".join(steps_lines).strip()
        expected_text = "\n".join(expected_lines).strip()
        
        # 格式化步骤和预期结果文本
        steps_text = _format_step_text(steps_text)
        expected_text = _format_step_text(expected_text)
        
        # 确保字段非空
        if not steps_text:
            steps_text = ""
        if not expected_text:
            expected_text = ""
        
        # 处理CSV中的特殊字符
        def escape_csv_field(text: str) -> str:
            """处理CSV字段中的特殊字符"""
            if not text:
                return ""
            # 如果包含逗号、换行符或双引号，需要用双引号包裹
            if ',' in text or '\n' in text or '"' in text:
                # 双引号转义为两个双引号
                text = text.replace('"', '""')
                return f'"{text}"'
            return text
        
        row = [
            case.get("module", ""),
            case.get("custom_module", ""),
            case.get("title", ""),
            case.get("priority", "P2"),
            escape_csv_field(case.get("preconditions", "")),
            escape_csv_field(steps_text),
            escape_csv_field(expected_text)
        ]
        
        rows.append(row)
    
    return rows


def convert_to_module_csv(xmind_file: str, output_path: str = None, parser: str = "auto") -> str:
    """
    将XMind文件转换为模块化用例CSV格式
    
    Args:
        xmind_file: XMind文件路径
        output_path: 输出CSV文件路径（可选）
        parser: 解析器选择 ("auto", "xmind", "xmind2testcase")
    
    Returns:
        生成的CSV文件绝对路径
    """
    cases = get_module_cases(xmind_file, parser=parser)
    rows = build_module_csv_rows(cases)
    
    if output_path:
        csv_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    else:
        temp_dir = tempfile.gettempdir()
        module_name = _extract_module_name(xmind_file)
        # 修复：使用简洁的文件名，不包含UUID前缀
        csv_filename = f"{module_name}_模块化用例.csv"
        csv_path = os.path.join(temp_dir, csv_filename)
        
        # 如果文件已存在，添加时间戳避免冲突
        if os.path.exists(csv_path):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"{module_name}_模块化用例_{timestamp}.csv"
            csv_path = os.path.join(temp_dir, csv_filename)
    
    # 使用UTF-8 BOM编码确保Excel正确显示中文
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    return csv_path


def get_module_export_filename(xmind_file: str) -> str:
    """
    生成模块化用例导出文件名
    格式：{原文件名}_模块化用例.csv
    """
    module_name = _extract_module_name(xmind_file)
    return f"{module_name}_模块化用例.csv"


if __name__ == "__main__":
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        xmind_file = sys.argv[1]
        if os.path.exists(xmind_file):
            try:
                csv_path = convert_to_module_csv(xmind_file)
                print(f"✅ 模块化用例转换成功！")
                print(f"📁 输出文件: {csv_path}")
                
                # 显示统计信息
                cases = get_module_cases(xmind_file)
                print(f"📊 转换统计:")
                print(f"   - 用例总数: {len(cases)}")
                print(f"   - 总步骤数: {sum(len(case.get('steps', [])) for case in cases)}")
                
            except Exception as e:
                print(f"❌ 转换失败: {str(e)}")
        else:
            print(f"❌ 文件不存在: {xmind_file}")
    else:
        print("用法: python module_converter_v2.py <xmind_file>")