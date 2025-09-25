#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
XMind 转 CSV 团队协作Web界面
支持文件上传、团队文件列表管理、多种导出格式
按照产品需求实现完整的团队文件管理功能
"""

import os
import tempfile
import uuid
import json
import datetime
from flask import Flask, render_template_string, request, send_file, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from converter import convert_to_csv, get_structured_cases
from module_converter import convert_to_module_csv, get_module_cases, get_module_export_filename

app = Flask(__name__)
app.secret_key = 'xmind2csv_team_secret_key'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'xmind'}

# 团队文件存储目录
TEAM_FILES_DIR = os.path.join(tempfile.gettempdir(), 'xmind_team_files')
TEAM_FILES_DB = os.path.join(TEAM_FILES_DIR, 'files_db.json')

def init_team_storage():
    """初始化团队文件存储"""
    if not os.path.exists(TEAM_FILES_DIR):
        os.makedirs(TEAM_FILES_DIR)
    if not os.path.exists(TEAM_FILES_DB):
        with open(TEAM_FILES_DB, 'w', encoding='utf-8') as f:
            json.dump([], f)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_team_files():
    """加载团队文件列表"""
    try:
        with open(TEAM_FILES_DB, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_team_files(files_data):
    """保存团队文件列表"""
    with open(TEAM_FILES_DB, 'w', encoding='utf-8') as f:
        json.dump(files_data, f, ensure_ascii=False, indent=2)

def add_team_file(filename, original_name, uploader, description):
    """添加文件到团队列表"""
    files_data = load_team_files()
    file_info = {
        'id': str(uuid.uuid4()),
        'filename': filename,
        'original_name': original_name,
        'uploader': uploader,
        'description': description,
        'upload_time': datetime.datetime.now().isoformat(),
        'file_size': os.path.getsize(os.path.join(TEAM_FILES_DIR, filename))
    }
    files_data.append(file_info)
    save_team_files(files_data)
    return file_info['id']

# HTML 模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XMind 转 CSV 团队协作平台</title>
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
            max-width: 1200px;
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
        
        .tabs {
            display: flex;
            border-bottom: 2px solid #f0f0f0;
            margin-bottom: 30px;
        }
        
        .tab {
            padding: 15px 30px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1.1em;
            color: #666;
            transition: all 0.3s ease;
        }
        
        .tab.active {
            color: #4facfe;
            border-bottom: 3px solid #4facfe;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
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
        
        .btn-small {
            padding: 8px 16px;
            font-size: 0.9em;
            margin: 2px;
        }
        
        .btn-success {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        }
        
        .btn-warning {
            background: linear-gradient(135deg, #ffc107 0%, #ff8c00 100%);
        }
        
        .btn-info {
            background: linear-gradient(135deg, #17a2b8 0%, #007bff 100%);
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
        }
        
        .form-group textarea {
            height: 80px;
            resize: vertical;
        }
        
        .team-files-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        .team-files-table th,
        .team-files-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        .team-files-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        
        .team-files-table tr:hover {
            background: #f8f9ff;
        }
        
        .export-buttons {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .export-btn {
            padding: 6px 12px;
            font-size: 0.8em;
            border-radius: 15px;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        
        .export-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        
        .export-btn.standard {
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
            color: white;
        }
        
        .export-btn.zentao {
            background: linear-gradient(135deg, #fd7e14 0%, #e63946 100%);
            color: white;
        }
        
        .export-btn.module {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
        }
        
        .export-btn.module.active {
            box-shadow: 0 0 0 2px #28a745;
        }
        
        .file-info {
            font-size: 0.9em;
            color: #666;
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
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .alert-success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        
        .alert-error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .loading {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #4facfe;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔄 XMind 转 CSV 团队协作平台</h1>
            <p>支持多种导出格式的思维导图转测试用例工具</p>
        </div>
        
        <div class="content">
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="alert alert-error">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            {% if success_message %}
                <div class="alert alert-success">{{ success_message }}</div>
            {% endif %}
            
            <div class="tabs">
                <button class="tab active" onclick="switchTab('upload')">📤 文件上传</button>
                <button class="tab" onclick="switchTab('team-files')">📋 团队文件列表</button>
            </div>
            
            <!-- 文件上传标签页 -->
            <div id="upload" class="tab-content active">
                <form method="POST" enctype="multipart/form-data" id="uploadForm">
                    <div class="upload-area" onclick="document.getElementById('file').click()">
                        <div class="upload-icon">📁</div>
                        <div class="upload-text">点击选择 XMind 文件或拖拽文件到此处</div>
                        <input type="file" id="file" name="file" class="file-input" accept=".xmind" required>
                        <button type="button" class="btn">选择文件</button>
                    </div>
                    
                    <div class="form-group">
                        <label for="uploader">上传者姓名:</label>
                        <input type="text" name="uploader" id="uploader" required placeholder="请输入您的姓名">
                    </div>
                    
                    <div class="form-group">
                        <label for="description">文件描述:</label>
                        <textarea name="description" id="description" placeholder="请简要描述文件内容和用途"></textarea>
                    </div>
                    
                    <div class="progress" id="progress">
                        <div class="progress-bar" id="progressBar"></div>
                    </div>
                    
                    <button type="submit" class="btn" id="submitBtn">
                        <span id="btnText">🚀 上传文件</span>
                    </button>
                </form>
            </div>
            
            <!-- 团队文件列表标签页 -->
            <div id="team-files" class="tab-content">
                <h3>团队文件列表</h3>
                <table class="team-files-table">
                    <thead>
                        <tr>
                            <th>文件名</th>
                            <th>上传者</th>
                            <th>描述</th>
                            <th>上传时间</th>
                            <th>文件大小</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for file in team_files %}
                        <tr>
                            <td>
                                <strong>{{ file.original_name }}</strong>
                                <div class="file-info">ID: {{ file.id[:8] }}...</div>
                            </td>
                            <td>{{ file.uploader }}</td>
                            <td>{{ file.description or '无描述' }}</td>
                            <td>{{ file.upload_time[:19].replace('T', ' ') }}</td>
                            <td>{{ "%.1f KB"|format(file.file_size / 1024) }}</td>
                            <td>
                                <div class="export-buttons">
                                    <button class="export-btn standard tooltip" onclick="exportFile('{{ file.id }}', 'standard')">
                                        ↓ 标准CSV
                                        <span class="tooltiptext">标准测试用例格式</span>
                                    </button>
                                    <button class="export-btn zentao tooltip" onclick="exportFile('{{ file.id }}', 'zentao')">
                                        ↘ 禅道CSV
                                        <span class="tooltiptext">禅道系统导入格式</span>
                                    </button>
                                    <button class="export-btn module active tooltip" onclick="exportFile('{{ file.id }}', 'module')">
                                        ✅ 新家头CSV
                                        <span class="tooltiptext">导出模块化用例格式</span>
                                    </button>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                        {% if not team_files %}
                        <tr>
                            <td colspan="6" style="text-align: center; color: #666; padding: 40px;">
                                暂无团队文件，请先上传 XMind 文件
                            </td>
                        </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        // 标签页切换
        function switchTab(tabName) {
            // 隐藏所有标签页内容
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(content => content.classList.remove('active'));
            
            // 移除所有标签的active类
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => tab.classList.remove('active'));
            
            // 显示选中的标签页内容
            document.getElementById(tabName).classList.add('active');
            
            // 添加active类到选中的标签
            event.target.classList.add('active');
        }
        
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
            
            const uploader = document.getElementById('uploader').value.trim();
            if (!uploader) {
                e.preventDefault();
                alert('请输入上传者姓名');
                return;
            }
            
            // 显示进度条和加载状态
            progress.style.display = 'block';
            submitBtn.disabled = true;
            btnText.innerHTML = '<span class="loading"></span>上传中...';
            
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
        
        // 导出文件功能
        function exportFile(fileId, exportType) {
            const button = event.target;
            const originalText = button.innerHTML;
            
            // 显示加载状态
            button.innerHTML = '<span class="loading"></span>导出中...';
            button.disabled = true;
            
            // 发送导出请求
            fetch('/api/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_id: fileId,
                    export_type: exportType
                })
            })
            .then(response => {
                if (response.ok) {
                    return response.blob();
                } else {
                    throw new Error('导出失败');
                }
            })
            .then(blob => {
                // 创建下载链接
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `exported_${exportType}_${fileId.substring(0, 8)}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                // 恢复按钮状态
                button.innerHTML = originalText;
                button.disabled = false;
            })
            .catch(error => {
                alert('导出失败: ' + error.message);
                button.innerHTML = originalText;
                button.disabled = false;
            });
        }
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
        uploader = request.form.get('uploader', '').strip()
        description = request.form.get('description', '').strip()
        
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)
        
        if not uploader:
            flash('请输入上传者姓名')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # 保存文件到团队目录
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(TEAM_FILES_DIR, unique_filename)
                file.save(file_path)
                
                # 添加到团队文件列表
                file_id = add_team_file(unique_filename, filename, uploader, description)
                
                success_message = f"文件 '{filename}' 上传成功！文件ID: {file_id[:8]}..."
                team_files = load_team_files()
                return render_template_string(HTML_TEMPLATE, team_files=team_files, success_message=success_message)
                
            except Exception as e:
                flash(f'上传失败: {str(e)}')
                return redirect(request.url)
        else:
            flash('请选择有效的 XMind 文件 (.xmind)')
            return redirect(request.url)
    
    # GET请求，显示主页面
    team_files = load_team_files()
    return render_template_string(HTML_TEMPLATE, team_files=team_files)

@app.route('/api/export', methods=['POST'])
def api_export():
    """API接口：导出文件"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        export_type = data.get('export_type', 'standard')
        
        if not file_id:
            return jsonify({'error': '缺少文件ID'}), 400
        
        # 查找文件
        team_files = load_team_files()
        target_file = None
        for file_info in team_files:
            if file_info['id'] == file_id:
                target_file = file_info
                break
        
        if not target_file:
            return jsonify({'error': '文件不存在'}), 404
        
        # 获取文件路径
        file_path = os.path.join(TEAM_FILES_DIR, target_file['filename'])
        if not os.path.exists(file_path):
            return jsonify({'error': '文件已被删除'}), 404
        
        # 根据导出类型执行转换
        if export_type == 'module':
            # 模块化用例格式
            csv_path = convert_to_module_csv(file_path, parser='auto')
            download_name = get_module_export_filename(file_path)
        elif export_type == 'zentao':
            # 禅道CSV格式（使用标准格式，可以后续扩展）
            csv_path = convert_to_csv(file_path, parser='auto')
            download_name = f"{target_file['original_name'].replace('.xmind', '')}_禅道CSV.csv"
        else:
            # 标准CSV格式
            csv_path = convert_to_csv(file_path, parser='auto')
            download_name = f"{target_file['original_name'].replace('.xmind', '')}_标准CSV.csv"
        
        return send_file(csv_path, as_attachment=True, download_name=download_name)
        
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """下载文件"""
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
    # 初始化团队文件存储
    init_team_storage()
    
    print("🚀 启动 XMind 转 CSV 团队协作平台...")
    print("📍 访问地址: http://localhost:5001")
    print("🔧 支持的功能:")
    print("   - 团队文件上传管理")
    print("   - 多种导出格式 (标准CSV、禅道CSV、模块化用例)")
    print("   - 文件列表和操作记录")
    print("   - 拖拽上传支持")
    print(f"📁 团队文件存储目录: {TEAM_FILES_DIR}")
    
    app.run(debug=True, host='0.0.0.0', port=5001)