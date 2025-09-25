#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 XMind 转换器
"""

import os
from converter import convert_to_csv, get_structured_cases

def test_converter():
    # 测试文件路径
    xmind_file = r'C:\Users\liwenxiang\CodeBuddy\20250807163614\xmind_store\9ed46f96-6d07-485b-a134-fdb63d8d1ed1_0929GoTyme.xmind'
    
    print("🔍 开始解析 XMind 文件...")
    print(f"文件路径: {xmind_file}")
    
    # 使用自动解析器
    cases = get_structured_cases(xmind_file, parser='auto')
    print(f"\n✅ 解析完成！共找到 {len(cases)} 个测试用例")
    
    # 显示前5个用例的详细信息
    print("\n📋 用例详情预览:")
    for i, case in enumerate(cases[:5]):
        print(f"\n--- 用例 {i+1} ---")
        print(f"标题: {case['title']}")
        print(f"模块: {case['module']}")
        print(f"优先级: {case['prio']}")
        print(f"前置条件: {case['pre']}")
        print(f"步骤数: {len(case['steps'])}")
        
        # 显示前2个步骤
        if case['steps']:
            print("步骤预览:")
            for j, (action, expected) in enumerate(case['steps'][:2]):
                print(f"  {j+1}. 操作: {action}")
                print(f"     预期: {expected}")
    
    # 生成 CSV 文件
    print(f"\n📄 生成 CSV 文件...")
    csv_path = convert_to_csv(xmind_file, "detailed_output.csv", parser='auto')
    print(f"✅ CSV 文件已生成: {csv_path}")
    
    # 显示文件大小
    file_size = os.path.getsize(csv_path)
    print(f"文件大小: {file_size} 字节")

if __name__ == "__main__":
    test_converter()