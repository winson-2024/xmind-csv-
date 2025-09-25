#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模块化用例转换器测试脚本
测试新的模块化用例导出功能
"""

import os
import sys
from module_converter import convert_to_module_csv, get_module_cases, get_module_export_filename

def test_module_converter():
    """测试模块化转换器"""
    print("🧪 开始测试模块化用例转换器...")
    
    # 查找测试文件
    test_files = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 在当前目录和上级目录查找xmind文件
    for root, dirs, files in os.walk(current_dir):
        for file in files:
            if file.endswith('.xmind'):
                test_files.append(os.path.join(root, file))
    
    if not test_files:
        print("❌ 未找到测试用的XMind文件")
        print("请在项目目录中放置一个.xmind文件进行测试")
        return
    
    # 测试第一个找到的文件
    test_file = test_files[0]
    print(f"📁 测试文件: {os.path.basename(test_file)}")
    
    try:
        # 测试模块名提取
        expected_filename = get_module_export_filename(test_file)
        print(f"📝 预期文件名: {expected_filename}")
        
        # 测试用例解析
        print("\n🔍 解析测试用例...")
        cases = get_module_cases(test_file, parser='auto')
        print(f"✅ 解析成功，共找到 {len(cases)} 个用例")
        
        # 显示前3个用例的详细信息
        for i, case in enumerate(cases[:3]):
            print(f"\n📋 用例 {i+1}:")
            print(f"   模块: {case.get('module', 'N/A')}")
            print(f"   自定义模块: {case.get('custom_module', 'N/A')}")
            print(f"   用例名称: {case.get('title', 'N/A')}")
            print(f"   优先级: {case.get('priority', 'N/A')}")
            print(f"   前置条件: {case.get('preconditions', 'N/A')[:50]}...")
            print(f"   步骤数量: {len(case.get('steps', []))}")
        
        if len(cases) > 3:
            print(f"\n... 还有 {len(cases) - 3} 个用例")
        
        # 测试CSV转换
        print(f"\n🔄 转换为模块化CSV...")
        csv_path = convert_to_module_csv(test_file, parser='auto')
        print(f"✅ 转换成功！")
        print(f"📄 输出文件: {csv_path}")
        
        # 显示文件大小
        file_size = os.path.getsize(csv_path)
        print(f"📊 文件大小: {file_size} 字节 ({file_size/1024:.1f} KB)")
        
        # 读取并显示CSV前几行
        print(f"\n📖 CSV文件内容预览:")
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:5]):
                print(f"   第{i+1}行: {line.strip()[:100]}...")
        
        if len(lines) > 5:
            print(f"   ... 共 {len(lines)} 行")
        
        print(f"\n🎉 模块化用例转换测试完成！")
        print(f"📁 可以打开文件查看完整结果: {csv_path}")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_different_parsers():
    """测试不同解析器的效果"""
    print("\n🔬 测试不同解析器效果...")
    
    # 查找测试文件
    test_files = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    for root, dirs, files in os.walk(current_dir):
        for file in files:
            if file.endswith('.xmind'):
                test_files.append(os.path.join(root, file))
    
    if not test_files:
        print("❌ 未找到测试文件")
        return
    
    test_file = test_files[0]
    parsers = ['auto', 'xmind', 'xmind2testcase']
    
    for parser in parsers:
        try:
            print(f"\n🔧 测试解析器: {parser}")
            cases = get_module_cases(test_file, parser=parser)
            total_steps = sum(len(case.get('steps', [])) for case in cases)
            print(f"   用例数量: {len(cases)}")
            print(f"   总步骤数: {total_steps}")
            print(f"   平均步骤数: {total_steps/max(len(cases), 1):.1f}")
            
        except Exception as e:
            print(f"   ❌ 解析器 {parser} 失败: {str(e)}")

if __name__ == "__main__":
    test_module_converter()
    test_different_parsers()