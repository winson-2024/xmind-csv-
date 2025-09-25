#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
XMind 转 CSV Web 界面
提供简单的 Web 界面来使用 XMind 转换工具
"""

import os
import tempfile
import uuid
from flask import Flask, render_template_string, request, send_file, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from converter import convert_to_csv, get_structured_cases
from module_converter import convert_to_module_csv, get_module_cases, get_module_export_filename

app = Flask(__name__)
app.secret_key = 'xmind2csv_secret_key'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'xmind'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# HTML 模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XMind 转 CSV 工具</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .upload-area:hover {
            border-color: #4facfe;
            background: #f8f9ff;
        }
        
        .upload-area.dragover {
            border-color: #4facfe;
            background: #f0f8ff;
        }
        
        .upload-icon {
            font-size: 3em;
            color: #ddd;
            margin-bottom: 20px;
        }
        
        .upload-text {
            font-size: 1.2em;
            color: #666;
            margin-bottom: 20px;
        }
        
        .file-input {
            display: none;
        }
        
        .btn {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(79, 172, 254, 0.3);
        }
        
        .options {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        
        .option-group {
            margin-bottom: 15px;
        }
        
        .option-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #333;
        }
        
        .option-group select, .option-group input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1em;
        }
        
        .result {
            background: #e8f5e8;
            border: 1px solid #4caf50;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }
        
        .error {
            background: #ffe8e8;
            border: 1px solid #f44336;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            color: #d32f2f;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #4facfe;
        }
        
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .export-buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .export-btn {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 0.9em;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        
        .export-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(79, 172, 254, 0.3);
        }
        
        .export-btn.active {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
        }
        
        .export-btn.active::before {
            content: "✅ ";
        }
        
        .tooltip {
            position: relative;
            display: inline-block;
        }
        
        .tooltip .tooltiptext {
            visibility: hidden;
            width: 200px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 8px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.8em;
        }
        
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        
        .progress {
            width: 100%;
            height: 20px;
            background: #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
            margin: 20px 0;
            display: none;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            width: 0%;
            transition: width 0.3s ease;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #4facfe;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔄 XMind 转 CSV</h1>
            <p>将 XMind 思维导图转换为标准测试用例 CSV 文件</p>
        </div>
        
        <div class="content">
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="error">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST" enctype="multipart/form-data" id="uploadForm">
                <div class="upload-area" onclick="document.getElementById('file').click()">
                    <div class="upload-icon">📁</div>
                    <div class="upload-text">点击选择 XMind 文件或拖拽文件到此处</div>
                    <input type="file" id="file" name="file" class="file-input" accept=".xmind" required>
                    <button type="button" class="btn">选择文件</button>
                </div>
                
                <div class="options">
                    <h3>转换选项</h3>
                    <div class="option-group">
                        <label for="export_format">导出格式:</label>
                        <select name="export_format" id="export_format">
                            <option value="standard">标准CSV格式</option>
                            <option value="module">新家头CSV (模块化用例)</option>
                        </select>
                    </div>
                    <div class="option-group">
                        <label for="parser">解析器选择:</label>
                        <select name="parser" id="parser">
                            <option value="auto">自动选择 (推荐)</option>
                            <option value="xmind2">xmind2testcase</option>
                            <option value="xmindlib">xmind 库</option>
                        </select>
                    </div>
                    <div class="option-group">
                        <label for="output_name">输出文件名 (可选):</label>
                        <input type="text" name="output_name" id="output_name" placeholder="留空则自动生成">
                    </div>
                </div>
                
                <div class="progress" id="progress">
                    <div class="progress-bar" id="progressBar"></div>
                </div>
                
                <button type="submit" class="btn" id="submitBtn">
                    <span id="btnText">🚀 开始转换</span>
                </button>
            </form>
            
            {% if result %}
            <div class="result">
                <h3>✅ 转换成功！</h3>
                <p><strong>生成文件:</strong> {{ result.filename }}</p>
                <p><strong>文件大小:</strong> {{ result.size }} 字节</p>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{{ result.case_count }}</div>
                        <div class="stat-label">测试用例</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ result.step_count }}</div>
                        <div class="stat-label">测试步骤</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ result.parser_used }}</div>
                        <div class="stat-label">使用解析器</div>
                    </div>
                </div>
                
                <div class="export-buttons">
                    <a href="{{ url_for('download_file', filename=result.filename) }}" class="btn">📥 下载 CSV 文件</a>
                    {% if result.export_type == 'module' %}
                    <span class="export-btn active tooltip">
                        新家头CSV
                        <span class="tooltiptext">导出模块化用例格式</span>
                    </span>
                    {% else %}
                    <span class="export-btn tooltip">
                        标准CSV
                        <span class="tooltiptext">标准测试用例格式</span>
                    </span>
                    {% endif %}
                </div>
            </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        // 文件拖拽功能
        const uploadArea = document.querySelector('.upload-area');
        const fileInput = document.getElementById('file');
        const form = document.getElementById('uploadForm');
        const progress = document.getElementById('progress');
        const progressBar = document.getElementById('progressBar');
        const submitBtn = document.getElementById('submitBtn');
        const btnText = document.getElementById('btnText');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                updateFileName(files[0].name);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                updateFileName(e.target.files[0].name);
            }
        });
        
        function updateFileName(name) {
            const uploadText = document.querySelector('.upload-text');
            uploadText.textContent = `已选择: ${name}`;
        }
        
        form.addEventListener('submit', (e) => {
            if (!fileInput.files.length) {
                e.preventDefault();
                alert('请选择一个 XMind 文件');
                return;
            }
            
            // 显示进度条和加载状态
            progress.style.display = 'block';
            submitBtn.disabled = true;
            btnText.innerHTML = '<span class="loading"></span>转换中...';
            
            // 模拟进度条
            let width = 0;
            const interval = setInterval(() => {
                width += Math.random() * 10;
                if (width >= 90) {
                    clearInterval(interval);
                }
                progressBar.style.width = width + '%';
            }, 200);
        });
    </script>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 检查文件是否存在
        if 'file' not in request.files:
            flash('没有选择文件')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # 保存上传的文件
                filename = secure_filename(file.filename)
                temp_dir = tempfile.gettempdir()
                input_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{filename}")
                file.save(input_path)
                
                # 获取转换参数
                export_format = request.form.get('export_format', 'standard')
                parser = request.form.get('parser', 'auto')
                output_name = request.form.get('output_name', '').strip()
                
                # 根据导出格式选择转换方法
                if export_format == 'module':
                    # 模块化用例格式
                    if output_name:
                        if not output_name.endswith('.csv'):
                            output_name += '.csv'
                        output_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{output_name}")
                    else:
                        # 使用默认的模块化文件名格式
                        default_name = get_module_export_filename(input_path)
                        output_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{default_name}")
                    
                    # 执行模块化转换
                    csv_path = convert_to_module_csv(input_path, output_path, parser=parser)
                    
                    # 获取统计信息
                    cases = get_module_cases(input_path, parser=parser)
                    case_count = len(cases)
                    step_count = sum(len(case.get('steps', [])) for case in cases)
                    export_type = 'module'
                else:
                    # 标准格式
                    if output_name:
                        if not output_name.endswith('.csv'):
                            output_name += '.csv'
                        output_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{output_name}")
                    else:
                        output_path = None
                    
                    # 执行标准转换
                    csv_path = convert_to_csv(input_path, output_path, parser=parser)
                    
                    # 获取统计信息
                    cases = get_structured_cases(input_path, parser=parser)
                    case_count = len(cases)
                    step_count = sum(len(case.get('steps', [])) for case in cases)
                    export_type = 'standard'
                
                file_size = os.path.getsize(csv_path)
                
                # 清理临时输入文件
                os.remove(input_path)
                
                result = {
                    'filename': os.path.basename(csv_path),
                    'size': file_size,
                    'case_count': case_count,
                    'step_count': step_count,
                    'parser_used': parser,
                    'export_type': export_type
                }
                
                return render_template_string(HTML_TEMPLATE, result=result)
                
            except Exception as e:
                flash(f'转换失败: {str(e)}')
                return redirect(request.url)
        else:
            flash('请选择有效的 XMind 文件 (.xmind)')
            return redirect(request.url)
    
    return render_template_string(HTML_TEMPLATE)

@app.route('/download/<filename>')
def download_file(filename):
    temp_dir = tempfile.gettempdir()
    file_path = None
    
    # 查找文件
    for file in os.listdir(temp_dir):
        if file.endswith(filename):
            file_path = os.path.join(temp_dir, file)
            break
    
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        flash('文件不存在或已过期')
        return redirect(url_for('index'))

if __name__ == '__main__':
    print("🚀 启动 XMind 转 CSV Web 服务...")
    print("📍 访问地址: http://localhost:5000")
    print("🔧 支持的功能:")
    print("   - XMind 文件上传 (拖拽支持)")
    print("   - 多种解析器选择")
    print("   - 实时转换进度")
    print("   - CSV 文件下载")
    print("   - 转换统计信息")
    
    app.run(debug=True, host='0.0.0.0', port=5000)