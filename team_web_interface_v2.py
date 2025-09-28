#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
XMind 转 CSV 团队协作Web界面 - 优化版本
支持文件上传、团队文件列表管理、多种导出格式
按照产品需求和参考图设计实现完整的团队文件管理功能
"""

import os
import tempfile
import uuid
import json
import datetime
import shutil
from flask import Flask, render_template_string, request, send_file, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from converter import convert_to_csv, get_structured_cases
from module_converter_final import convert_to_module_csv, get_module_cases, get_module_export_filename

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

# HTML 模板 - 按照参考图设计
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XMind转禅道CSV工具</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: #f8f9fa;
            color: #333;
            padding: 20px;
            text-align: center;
            border-bottom: 1px solid #dee2e6;
        }
        
        .header h1 {
            font-size: 1.8em;
            margin-bottom: 5px;
            color: #333;
        }
        
        .header p {
            font-size: 0.9em;
            color: #666;
        }
        
        .content {
            padding: 20px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        .upload-panel {
            background: #e3f2fd;
            border: 1px solid #2196f3;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .usage-panel {
            background: #e3f2fd;
            border: 1px solid #2196f3;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .panel-header {
            background: #2196f3;
            color: white;
            padding: 12px 15px;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .panel-content {
            padding: 20px;
        }
        
        .upload-area {
            border: 2px dashed #2196f3;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            margin-bottom: 20px;
            transition: all 0.3s ease;
            cursor: pointer;
            background: white;
        }
        
        .upload-area:hover {
            border-color: #1976d2;
            background: #f3f8ff;
        }
        
        .upload-area.dragover {
            border-color: #1976d2;
            background: #e3f2fd;
        }
        
        .upload-icon {
            font-size: 2.5em;
            color: #2196f3;
            margin-bottom: 15px;
        }
        
        .upload-text {
            font-size: 1.1em;
            color: #666;
            margin-bottom: 15px;
        }
        
        .file-input {
            display: none;
        }
        
        .btn {
            background: #2196f3;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn:hover {
            background: #1976d2;
        }
        
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #333;
        }
        
        .form-group input, .form-group textarea, .form-group select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1em;
        }
        
        .form-group textarea {
            height: 60px;
            resize: vertical;
        }
        
        .team-files-panel {
            background: #e8f5e8;
            border: 1px solid #4caf50;
            border-radius: 8px;
            grid-column: 1 / -1;
            margin-top: 20px;
            overflow: hidden;
        }
        
        .team-files-panel .panel-header {
            background: #4caf50;
        }
        
        .team-files-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
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
            gap: 5px;
            flex-wrap: wrap;
        }
        
        .export-btn {
            padding: 4px 8px;
            font-size: 0.8em;
            border-radius: 3px;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 3px;
            min-width: 70px;
            justify-content: center;
        }
        
        .export-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        .export-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .export-btn.xmind {
            background: #2196f3;
            color: white;
        }
        
        .export-btn.standard {
            background: #4caf50;
            color: white;
        }
        
        .export-btn.zentao {
            background: #ff9800;
            color: white;
        }
        
        .export-btn.module {
            background: #9c27b0;
            color: white;
        }
        
        .export-btn.delete {
            background: #f44336;
            color: white;
        }
        
        .file-info {
            font-size: 0.85em;
            color: #666;
        }
        
        .progress {
            width: 100%;
            height: 4px;
            background: #f0f0f0;
            border-radius: 2px;
            overflow: hidden;
            margin: 15px 0;
            display: none;
        }
        
        .progress-bar {
            height: 100%;
            background: #2196f3;
            width: 0%;
            transition: width 0.3s ease;
        }
        
        .alert {
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 15px;
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
        
        .usage-content {
            font-size: 0.9em;
            line-height: 1.6;
        }
        
        .usage-content h4 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .usage-content ol {
            margin-left: 20px;
            margin-bottom: 15px;
        }
        
        .usage-content li {
            margin-bottom: 5px;
        }
        
        .warning-box {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 10px;
            border-radius: 4px;
            margin-top: 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .loading {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #2196f3;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>XMind转禅道CSV工具</h1>
            <p>团队协作功能 - 批量管理和转换XMind文件</p>
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
            
            <!-- 文件上传面板 -->
            <div class="upload-panel">
                <div class="panel-header">
                    📤 上传XMind文件
                </div>
                <div class="panel-content">
                    <form method="POST" enctype="multipart/form-data" id="uploadForm">
                        <div class="upload-area" onclick="document.getElementById('file').click()">
                            <div class="upload-icon">📁</div>
                            <div class="upload-text">点击选择文件</div>
                            <div class="file-info">未选择任何文件</div>
                            <input type="file" id="file" name="file" class="file-input" accept=".xmind" required>
                            <button type="button" class="btn">选择文件</button>
                        </div>
                        
                        <div class="form-group">
                            <label for="action_type">操作类型:</label>
                            <select name="action_type" id="action_type" onchange="toggleUploadFields()">
                                <option value="convert">直接转换下载</option>
                                <option value="upload">上传到团队列表</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="export_format">导出格式:</label>
                            <select name="export_format" id="export_format">
                                <option value="module">📊 新表头CSV (模块化用例)</option>
                                <option value="standard">✓ 标准CSV</option>
                                <option value="zentao">⚡ 禅道CSV</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="uploader">上传者姓名:</label>
                            <input type="text" name="uploader" id="uploader" placeholder="请输入您的姓名（可选）">
                        </div>
                        
                        <div class="form-group">
                            <label for="description">文件描述:</label>
                            <textarea name="description" id="description" placeholder="请简要描述文件内容（可选）"></textarea>
                        </div>
                        
                        <div id="upload_fields" style="display: none;">
                        </div>
                        
                        <div class="progress" id="progress">
                            <div class="progress-bar" id="progressBar"></div>
                        </div>
                        
                        <button type="submit" class="btn" id="submitBtn">
                            <span id="btnText">🚀 转换并下载</span>
                        </button>
                    </form>
                    
                    {% if result %}
                    <div class="alert alert-success">
                        <h4>✅ 转换成功！</h4>
                        <p><strong>生成文件:</strong> {{ result.filename }}</p>
                        <p><strong>文件大小:</strong> {{ result.size }} 字节</p>
                        <p><strong>用例数量:</strong> {{ result.case_count }}</p>
                        <p><strong>步骤数量:</strong> {{ result.step_count }}</p>
                        <p><strong>导出格式:</strong> {{ result.export_type }}</p>
                        
                        <div style="margin-top: 15px;">
                            <a href="{{ url_for('download_file', filename=result.filename) }}" class="btn">📥 下载 CSV 文件</a>
                        </div>
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <!-- 使用说明面板 -->
            <div class="usage-panel">
                <div class="panel-header">
                    ℹ️ 使用说明
                </div>
                <div class="panel-content">
                    <div class="usage-content">
                        <h4>团队协作功能</h4>
                        <p>本工具支持多种XMind文件，实现协作式用例管理：</p>
                        <ol>
                            <li>上传您的XMind文件，填写姓名和描述</li>
                            <li>可以直接转换下载，或保存到团队文件库</li>
                            <li>可以下载原始XMind文件进行查看和编辑</li>
                            <li>可以将XMind文件转换为CSV格式进行下载</li>
                            <li>所有文件集中存储，方便团队协作管理</li>
                        </ol>
                        <div class="warning-box">
                            ⚠️ 注意：请勿上传包含敏感信息的文件，上传前请确认文件内容正确。
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 团队文件列表面板 -->
        <div class="team-files-panel">
            <div class="panel-header">
                📋 团队文件列表
            </div>
            <div class="panel-content">
                <table class="team-files-table">
                    <thead>
                        <tr>
                            <th>文件名</th>
                            <th>上传者</th>
                            <th>描述</th>
                            <th>上传时间</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for file in team_files %}
                        <tr>
                            <td>
                                <strong>{{ file.original_name }}</strong>
                                <div class="file-info">{{ "%.1f KB"|format(file.file_size / 1024) }}</div>
                            </td>
                            <td>{{ file.uploader }}</td>
                            <td>{{ file.description or '无描述' }}</td>
                            <td>{{ file.upload_time[:19].replace('T', ' ') }}</td>
                            <td>
                                <div class="export-buttons">
                                    <button class="export-btn xmind" onclick="exportFile('{{ file.id }}', 'xmind')" title="下载原始XMind文件">
                                        ↓ XMind
                                    </button>
                                    <button class="export-btn standard" onclick="exportFile('{{ file.id }}', 'standard')" title="标准测试用例格式">
                                        ✓ 标准CSV
                                    </button>
                                    <button class="export-btn zentao" onclick="exportFile('{{ file.id }}', 'zentao')" title="禅道系统导入格式">
                                        ⚡ 禅道CSV
                                    </button>
                                    <button class="export-btn module" onclick="exportFile('{{ file.id }}', 'module')" title="导出模块化用例格式">
                                        📊 新表头CSV
                                    </button>
                                    <button class="export-btn delete" onclick="deleteFile('{{ file.id }}')" title="删除文件">
                                        🗑️ 删除
                                    </button>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                        {% if not team_files %}
                        <tr>
                            <td colspan="5" style="text-align: center; color: #666; padding: 40px;">
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
            const fileInfo = document.querySelector('.upload-area .file-info');
            fileInfo.textContent = `已选择: ${name}`;
        }
        
        // 切换上传字段显示
        function toggleUploadFields() {
            const actionType = document.getElementById('action_type').value;
            const submitBtn = document.getElementById('submitBtn');
            const btnText = document.getElementById('btnText');
            
            if (actionType === 'convert') {
                btnText.textContent = '🚀 转换并下载';
            } else {
                btnText.textContent = '🚀 上传到团队';
            }
        }
        
        // 初始化字段显示
        toggleUploadFields();
        
        form.addEventListener('submit', (e) => {
            if (!fileInput.files.length) {
                e.preventDefault();
                alert('请选择一个 XMind 文件');
                return;
            }
            
            const actionType = document.getElementById('action_type').value;
            
            // 显示进度条和加载状态
            progress.style.display = 'block';
            submitBtn.disabled = true;
            
            if (actionType === 'convert') {
                btnText.innerHTML = '<span class="loading"></span>转换中...';
            } else {
                btnText.innerHTML = '<span class="loading"></span>上传中...';
            }
            
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
        
        // 导出文件功能 - 修复重复使用问题
        function exportFile(fileId, exportType) {
            const button = event.target;
            const originalText = button.innerHTML;
            
            // 防止重复点击
            if (button.disabled) {
                return;
            }
            
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
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.blob();
            })
            .then(blob => {
                // 创建下载链接
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                
                if (exportType === 'xmind') {
                    a.download = `${fileId.substring(0, 8)}.xmind`;
                } else {
                    a.download = `exported_${exportType}_${fileId.substring(0, 8)}.csv`;
                }
                
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            })
            .catch(error => {
                console.error('导出错误:', error);
                alert('导出失败: ' + error.message);
            })
            .finally(() => {
                // 恢复按钮状态
                button.innerHTML = originalText;
                button.disabled = false;
            });
        }
        
        // 删除文件功能
        function deleteFile(fileId) {
            if (!confirm('确定要删除这个文件吗？此操作不可撤销。')) {
                return;
            }
            
            const button = event.target;
            const originalText = button.innerHTML;
            
            // 防止重复点击
            if (button.disabled) {
                return;
            }
            
            // 显示加载状态
            button.innerHTML = '<span class="loading"></span>删除中...';
            button.disabled = true;
            
            // 发送删除请求
            fetch('/api/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_id: fileId
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // 删除成功，刷新页面
                    location.reload();
                } else {
                    throw new Error(data.error || '删除失败');
                }
            })
            .catch(error => {
                console.error('删除错误:', error);
                alert('删除失败: ' + error.message);
                // 恢复按钮状态
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
        action_type = request.form.get('action_type', 'convert')
        export_format = request.form.get('export_format', 'module')
        uploader = request.form.get('uploader', '').strip()
        description = request.form.get('description', '').strip()
        
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)
        

        
        if file and allowed_file(file.filename):
            try:
                if action_type == 'convert':
                    # 直接转换并下载
                    filename = secure_filename(file.filename or 'unknown.xmind')
                    temp_dir = tempfile.gettempdir()
                    input_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{filename}")
                    file.save(input_path)
                    
                    # 根据导出格式执行转换
                    if export_format == 'module':
                        csv_path = convert_to_module_csv(input_path, parser='auto')
                        cases = get_module_cases(input_path, parser='auto')
                        export_type_name = '模块化用例'
                    elif export_format == 'zentao':
                        csv_path = convert_to_csv(input_path, parser='auto')
                        cases = get_structured_cases(input_path, parser='auto')
                        export_type_name = '禅道CSV'
                    else:
                        csv_path = convert_to_csv(input_path, parser='auto')
                        cases = get_structured_cases(input_path, parser='auto')
                        export_type_name = '标准CSV'
                    
                    # 获取统计信息
                    case_count = len(cases)
                    step_count = sum(len(case.get('steps', [])) for case in cases)
                    file_size = os.path.getsize(csv_path)

                    # 将原始XMind文件保存到团队库，并加入团队列表，便于后续导出操作
                    try:
                        unique_filename = f"{uuid.uuid4()}_{filename}"
                        team_file_path = os.path.join(TEAM_FILES_DIR, unique_filename)
                        shutil.copyfile(input_path, team_file_path)
                        add_team_file(unique_filename, filename, uploader or '未填', description or '')
                    except Exception as _:
                        pass
                    
                    # 清理临时输入文件
                    os.remove(input_path)
                    
                    result = {
                        'filename': os.path.basename(csv_path),
                        'size': file_size,
                        'case_count': case_count,
                        'step_count': step_count,
                        'export_type': export_type_name
                    }
                    
                    team_files = load_team_files()
                    return render_template_string(HTML_TEMPLATE, team_files=team_files, result=result)
                    
                else:
                    # 上传到团队列表
                    filename = secure_filename(file.filename or 'unknown.xmind')
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    file_path = os.path.join(TEAM_FILES_DIR, unique_filename)
                    file.save(file_path)
                    
                    # 添加到团队文件列表
                    file_id = add_team_file(unique_filename, filename, uploader, description)
                    
                    success_message = f"文件 '{filename}' 上传成功！文件ID: {str(file_id)[:8]}..."
                    team_files = load_team_files()
                    return render_template_string(HTML_TEMPLATE, team_files=team_files, success_message=success_message)
                
            except Exception as e:
                flash(f'操作失败: {str(e)}')
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
        if export_type == 'xmind':
            # 直接返回原始XMind文件
            return send_file(file_path, as_attachment=True, download_name=target_file['original_name'])
        elif export_type == 'module':
            # 模块化用例格式
            csv_path = convert_to_module_csv(file_path, parser='auto')
            download_name = get_module_export_filename(file_path)
        elif export_type == 'zentao':
            # 禅道CSV格式
            csv_path = convert_to_csv(file_path, parser='auto')
            download_name = f"{target_file['original_name'].replace('.xmind', '')}_禅道CSV.csv"
        else:
            # 标准CSV格式
            csv_path = convert_to_csv(file_path, parser='auto')
            download_name = f"{target_file['original_name'].replace('.xmind', '')}_标准CSV.csv"
        
        return send_file(csv_path, as_attachment=True, download_name=download_name)
        
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500

@app.route('/api/delete', methods=['POST'])
def api_delete():
    """API接口：删除文件"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'error': '缺少文件ID', 'success': False}), 400
        
        # 查找文件
        team_files = load_team_files()
        target_file = None
        file_index = -1
        for i, file_info in enumerate(team_files):
            if file_info['id'] == file_id:
                target_file = file_info
                file_index = i
                break
        
        if not target_file:
            return jsonify({'error': '文件不存在', 'success': False}), 404
        
        # 删除物理文件
        file_path = os.path.join(TEAM_FILES_DIR, target_file['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # 从数据库中删除记录
        team_files.pop(file_index)
        save_team_files(team_files)
        
        return jsonify({'success': True, 'message': '文件删除成功'})
        
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}', 'success': False}), 500

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
    
    print("🚀 启动 XMind 转 CSV 团队协作平台 V2...")
    print("📍 本地访问地址: http://localhost:5001")
    print("📍 网络访问地址: http://0.0.0.0:5001")
    print("🔧 支持的功能:")
    print("   - 团队文件上传管理")
    print("   - 多种导出格式 (标准CSV、禅道CSV、新表头CSV)")
    print("   - XMind原文件下载")
    print("   - 文件列表和操作记录")
    print("   - 拖拽上传支持")
    print("   - 修复导出功能重复使用问题")
    print(f"📁 团队文件存储目录: {TEAM_FILES_DIR}")
    
    app.run(debug=True, host='0.0.0.0', port=5001)