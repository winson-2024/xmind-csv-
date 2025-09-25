#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
XMind -> CSV 新模板转换库（增强版）

目标：
- 保持原有业务逻辑：沿用 xmind2testcase 的用例字段与优先级体系
- 仅重构导出模板结构与多步骤合并规则
- 新增"解析器自动择优"：若 xmind2testcase 结果明显不全，则优先采用 xmind 库递归解析结果
  - 也可通过参数强制指定解析器：xmind2 或 xmindlib

必填字段（列顺序严格如下）：
1) [用例名称]
2) [所属模块]
3) [Priority等级]（importance 1-5 -> P0-4；兼容 '1'-'5'）
4) [用例类型]（固定"功能测试"）
5) [前置条件]
6) [用例步骤]（按 1. 2. 3. 编号并换行合并）
7) [预期结果]（与步骤一一对应编号并换行合并）
"""

import csv
import os
import re
import tempfile
import uuid
from typing import Dict, List, Tuple

import xmind  # 新版 xmind 库
from xmind2testcase.utils import get_xmind_testcase_list

# 优先级映射：严格沿用原体系（importance -> Priority）
PRIORITY_MAP = {
    1: "P0", 2: "P1", 3: "P2", 4: "P3", 5: "P4",
    "1": "P0", "2": "P1", "3": "P2", "4": "P3", "5": "P4",
}

# 固定用例类型
CASE_TYPE = "功能测试"

def _normalize_priority(value) -> str:
    """
    将多种优先级表示统一为P0-P4；缺失或非法时为P2。
    支持以下格式：
    - 1-5, '1'-'5'
    - P0-P4, p0-p4
    - 优先级1-5
    - 高、中、低
    - High, Medium, Low
    - Critical, Major, Minor, Trivial
    """
    if value is None:
        return "P2"
    
    v = str(value).strip().upper()
    
    # 直接是 P0-4
    if re.fullmatch(r"P[0-4]", v):
        return v
    
    # 纯数字 1-5
    if re.fullmatch(r"[1-5]", v):
        return PRIORITY_MAP.get(v, "P2")
    
    # 可能是整数
    try:
        iv = int(v)
        if 1 <= iv <= 5:
            return PRIORITY_MAP.get(iv, "P2")
    except Exception:
        pass
    
    # 处理"优先级X"格式
    priority_match = re.search(r'优先级[：:\s]*([1-5])', v)
    if priority_match:
        return PRIORITY_MAP.get(priority_match.group(1), "P2")
    
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
    
    # 默认返回P2
    return "P2"


def _sanitize_text(text: str) -> str:
    """基础清洗：去除 None、零宽字符、所有空白符合并为一个空格。适用于单行文本。"""
    if not text:
        return ""
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", str(text))
    text = re.sub(r"\s+", " ", text.strip())
    return text


def _sanitize_multiline_text(text: str) -> str:
    """多行文本清洗：保留换行符，但清理每行的多余空白。"""
    if not text:
        return ""
    text = str(text)
    # 移除零宽字符
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    # 对每一行进行处理
    lines = text.split('\n')
    processed_lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in lines]
    # 过滤掉完全是空内容的行
    processed_lines = [line for line in processed_lines if line]
    return "\n".join(processed_lines)


def _sanitize_module(module: str) -> str:
    """模块清洗：统一中文括号为英文括号，并进行通用清洗。"""
    if not module:
        return "/"
    module = re.sub(r"[（）]", lambda m: {"（": "(", "）": ")"}.get(m.group(), m.group()), module)
    return _sanitize_text(module)


# _number_steps_if_needed function is removed as per user's request to remove auto-numbering.


def _group_from_xmind2testcase(xmind_file: str) -> List[dict]:
    """
    直接将 xmind2testcase 的解析结果转换为列表，不进行去重或合并。
    每个测试用例（即使标题重复）都成为独立条目。
    """
    testcases = get_xmind_testcase_list(xmind_file)
    all_cases = []
    for tc in testcases:
        steps = []
        for step in (tc.get("steps", []) or []):
            action = _sanitize_multiline_text(step.get("actions", "") or "")
            expected = _sanitize_multiline_text(step.get("expectedresults", "") or "")
            if action or expected:
                steps.append((action, expected))

        # 即使没有步骤，也应作为一个用例存在
        all_cases.append({
            "title": _sanitize_text(tc.get("name", "") or ""),
            "module": _sanitize_module(tc.get("suite", "") or "/"),
            "pre": _sanitize_multiline_text(tc.get("preconditions", "") or "") or "无", # Ensure "无" for empty preconditions
            "prio": _normalize_priority(tc.get("importance")),
            "steps": steps
        })
    return all_cases


def _extract_priority_from_topic(topic) -> str:
    """
    从XMind主题中提取优先级信息。
    优先级可能存在于：
    1. 标题中的P0-P4标记
    2. 标签(markers)中的优先级标识
    3. 备注(notes)中的优先级信息
    """
    # 1. 检查标题中的优先级标记
    title = topic.getTitle() or ""
    priority_match = re.search(r'\b(P[0-4]|[1-5])\b', title)
    if priority_match:
        return _normalize_priority(priority_match.group(1))
    
    # 2. 检查标签(markers)中的优先级
    markers = topic.getMarkers() or []
    for marker in markers:
        marker_id = marker.getMarkerId() if hasattr(marker, 'getMarkerId') else str(marker)
        # 标签ID通常包含priority或importance字样
        if 'priority' in marker_id.lower() or 'importance' in marker_id.lower():
            # 从标签ID中提取数字
            num_match = re.search(r'(\d+)', marker_id)
            if num_match:
                return _normalize_priority(num_match.group(1))
    
    # 3. 检查备注中的优先级信息
    notes = topic.getNotes() or ""
    priority_in_notes = re.search(r'\b(P[0-4]|优先级[：:]\s*([1-5]))\b', str(notes))
    if priority_in_notes:
        if priority_in_notes.group(1).startswith('P'):
            return _normalize_priority(priority_in_notes.group(1))
        else:
            return _normalize_priority(priority_in_notes.group(2))
    
    # 默认返回P2
    return "P2"

def _group_from_xmindlib(xmind_file: str) -> List[dict]:
    """
    使用新版 xmind 库递归遍历主题，将识别出的每个测试用例（即使标题重复）添加为独立条目。
    增强了优先级提取功能。
    """
    workbook = xmind.load(xmind_file)
    sheet = workbook.getPrimarySheet()
    root = sheet.getRootTopic()

    all_cases = []

    def extract(topic, module_path_list: List[str]):
        if not topic:
            return
        raw_title = topic.getTitle() or ""
        title = _sanitize_text(raw_title)
        if not title:
            return

        sub_topics = topic.getSubTopics() or []
        
        # Heuristic for identifying a test case:
        # A topic is likely a test case if its children primarily look like steps
        # (i.e., they are not complex module structures themselves).
        # We assume a test case's direct children are steps, and steps' children are expected results.
        is_testcase_candidate = False
        if sub_topics:
            # Check if children are simple (steps) rather than complex (modules)
            # A simple child (step) would typically have no grandchildren, or only leaf grandchildren (expected results)
            simple_children_count = 0
            for st in sub_topics:
                if st and st.getTitle(): # Child has a title (potential action)
                    grandchildren = st.getSubTopics() or []
                    if not grandchildren or all(not gc.getSubTopics() for gc in grandchildren):
                        simple_children_count += 1
            
            # If a high percentage of children are simple, it's likely a test case
            if len(sub_topics) > 0 and simple_children_count / len(sub_topics) > 0.7: # Increased threshold
                is_testcase_candidate = True
        
        # Removed the title_keywords check for robustness, as it might cause false positives for modules.

        if is_testcase_candidate:
            current_module = "/".join(module_path_list) if module_path_list else "/"
            
            case_title = title
            preconditions = ""
            steps_data = [] # List of (action, expected) tuples

            # Extract preconditions from notes of the test case topic itself (common place)
            topic_notes = topic.getNotes()
            if topic_notes:
                preconditions = _sanitize_multiline_text(topic_notes)
            
            # Iterate through children to find preconditions, steps, and expected results
            for child_topic in sub_topics:
                child_title = _sanitize_multiline_text(child_topic.getTitle() or "")
                
                # Special handling for "前置条件" as a child topic
                if child_title.lower().strip() in ["前置条件", "preconditions"]:
                    # If preconditions already found in notes, append this
                    if preconditions:
                        preconditions += "\n" + _sanitize_multiline_text(child_topic.getNotes() or "")
                    else:
                        preconditions = _sanitize_multiline_text(child_topic.getNotes() or "")
                    
                    if not preconditions and child_topic.getSubTopics():
                        # If notes are empty, check first grandchild
                        first_grandchild = child_topic.getSubTopics()[0]
                        if first_grandchild:
                            preconditions = _sanitize_multiline_text(first_grandchild.getTitle() or "")
                    continue # Skip this child topic, as it's processed as precondition

                # Otherwise, treat as a step
                action = child_title
                expected_results_for_step = []
                # Collect all leaf grandchildren as expected results for this step
                for gc in (child_topic.getSubTopics() or []):
                    if gc and not gc.getSubTopics(): # Only collect leaf nodes
                        expected_results_for_step.append(_sanitize_multiline_text(gc.getTitle() or ""))
                expected = "\n".join(expected_results_for_step)
                
                if action or expected: # Only add if there's actual content
                    steps_data.append((action, expected))
            
            # 提取优先级
            priority = _extract_priority_from_topic(topic)
            
            all_cases.append({
                "title": case_title,
                "module": _sanitize_module(current_module),
                "pre": preconditions if preconditions else "无", # Ensure "无" for empty preconditions
                "prio": priority, # 使用提取的优先级
                "steps": steps_data
            })
        else:
            # Not a test case, continue recursive traversal for modules
            new_module_path_list = module_path_list + [title]
            for st in sub_topics:
                extract(st, new_module_path_list)

    # Start traversal from root topic's children (root topic is usually project name)
    for t in (root.getSubTopics() or []):
        extract(t, [])

    return all_cases


def _groups_auto(xmind_file: str) -> List[dict]:
    """
    自动选择解析结果更优的转换器。
    评分标准：优先选择用例总数更多的，如果总数接近，则选择平均每组步骤数更大的。
    """
    g1 = _group_from_xmind2testcase(xmind_file)
    try:
        g2 = _group_from_xmindlib(xmind_file)
    except Exception:
        g2 = []

    def _score(cases: List[dict]) -> tuple:
        if not cases:
            return (0, 0.0)
        case_count = len(cases)
        total_steps = sum(len(case.get("steps", [])) for case in cases)
        avg_steps = total_steps / max(case_count, 1)
        return (case_count, avg_steps)

    s1 = _score(g1)
    s2 = _score(g2)

    # 策略：用例数相差10%以内时，平均步骤数多的胜出；否则用例数多的胜出。
    # 这有助于在xmindlib解析不全时，仍优先选择用例数完整的xmind2testcase。
    count_diff_ratio = abs(s1[0] - s2[0]) / max(s1[0], s2[0], 1)

    if count_diff_ratio < 0.1:
        # 如果用例数接近，则平均步骤数多的更好
        return g2 if s2[1] > s1[1] else g1
    else:
        # 否则，用例数多的更好
        return g2 if s2[0] > s1[0] else g1


def build_rows_from_groups(cases: List[dict]) -> List[List[str]]:
    """根据用例列表构建带表头的 CSV 行，每个用例字典生成一行。"""
    headers = ["用例名称", "所属模块", "Priority等级", "用例类型", "前置条件", "用例步骤", "预期结果"]
    rows = [headers]

    for case in cases:
        steps_lines = []
        expected_lines = []

        # 为每个步骤和预期结果添加换行
        for action, expected in case.get("steps", []):
            if action:
                steps_lines.append(f"{action}")
            if expected:
                expected_lines.append(f"{expected}")

        # 撤销自动编号，保持原始文本；并确保字段非空
        # 确保每个步骤和预期结果之间有换行
        steps_text = "\n".join(steps_lines).strip()  # 使用单换行符分隔步骤
        expected_text = "\n".join(expected_lines).strip()  # 使用单换行符分隔预期结果
        if not steps_text:
            steps_text = "无"
        if not expected_text:
            expected_text = "无"

        full_module_path = case.get("module", "/")
        module_parts = full_module_path.split('/')
        
        display_module = module_parts[0] if module_parts else "/" # Take the first part for "所属模块"

        display_title = case.get("title", "")
        if len(module_parts) > 1:
            # Prepend the second part of the module path to the title
            display_title = f"{module_parts[1]}{display_title}"
        
        # Ensure display_module is not empty if module_parts was empty
        if not display_module:
            display_module = "/"

        rows.append([
            display_title, # Modified title
            display_module, # Modified module
            case.get("prio", "P2"),
            CASE_TYPE,
            case.get("pre", ""),
            steps_text,
            expected_text,
        ])
    return rows


def build_rows_from_xmind(xmind_file: str, parser: str = "auto") -> List[List[str]]:
    """
    将 XMind 文件按新模板规则转换为 CSV 行（含表头）。
    parser:
      - "auto": 自动选择更全面的解析结果（默认）
      - "xmind2": 仅使用 xmind2testcase
      - "xmindlib": 仅使用 xmind 库递归解析
    """
    if parser == "xmind2":
        cases = _group_from_xmind2testcase(xmind_file)
    elif parser == "xmindlib":
        cases = _group_from_xmindlib(xmind_file)
    else:
        cases = _groups_auto(xmind_file)

    return build_rows_from_groups(cases)


def get_structured_cases(xmind_file: str, parser: str = "auto") -> List[dict]:
    """
    将 XMind 文件解析为结构化的测试用例列表。
    每个用例是一个字典，包含 'title', 'module', 'prio', 'pre', 'steps' 等字段。
    'steps' 是一个列表，每个元素是 (action, expected) 元组。
    parser:
      - "auto": 自动选择更全面的解析结果（默认）
      - "xmind2": 仅使用 xmind2testcase
      - "xmindlib": 仅使用 xmind 库递归解析
    """
    if parser == "xmind2":
        cases = _group_from_xmind2testcase(xmind_file)
    elif parser == "xmindlib":
        cases = _group_from_xmindlib(xmind_file)
    else:
        cases = _groups_auto(xmind_file)
    return cases


def convert_to_csv(xmind_file: str, output_path: str = None, parser: str = "auto") -> str:
    """
    将 XMind 转换为符合新模板的 CSV 文件。
    - 使用 UTF-8 BOM 编码（utf-8-sig）
    - 默认写入临时目录，可指定 output_path
    - parser 参见 build_rows_from_xmind
    返回：生成的 CSV 文件绝对路径。
    """
    rows = build_rows_from_groups(get_structured_cases(xmind_file, parser=parser))

    if output_path:
        csv_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    else:
        temp_dir = tempfile.gettempdir()
        csv_filename = f"{uuid.uuid4()}_new_template.csv"
        csv_path = os.path.join(temp_dir, csv_filename)

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return csv_path