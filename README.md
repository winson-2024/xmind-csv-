# XMind转CSV团队协作平台

## 项目简介
XMind转CSV团队协作平台是一个基于Flask的Web应用，支持将XMind思维导图文件转换为多种CSV格式，适用于测试用例管理和团队协作。

## 功能特性
- 🚀 **多格式导出**：支持标准CSV、禅道CSV、新表头CSV格式
- 👥 **团队协作**：支持文件上传、共享和管理
- 📝 **用例管理**：智能处理测试用例的模块层级和标题格式
- 🗑️ **文件管理**：支持文件删除和批量操作
- 📱 **拖拽上传**：现代化的文件上传体验
- 🌐 **网络访问**：支持局域网和外网访问

## 技术栈
- **后端**：Python 3.8+, Flask
- **前端**：HTML5, CSS3, JavaScript
- **文件处理**：xmind, csv
- **部署**：支持Docker和传统部署

## 快速开始

### 本地开发
```bash
# 克隆项目
git clone https://github.com/winson-2024/xmind-csv-.git
cd xmind-csv-

# 安装依赖
pip install -r requirements.txt

# 启动服务
python team_web_interface_v2.py
```

访问 http://localhost:5001

## 阿里云服务器部署指南

### 1. 服务器环境准备

#### 1.1 系统要求
- **操作系统**：Ubuntu 20.04 LTS 或 CentOS 7+
- **内存**：建议2GB以上
- **存储**：建议10GB以上可用空间
- **网络**：确保80、443、5001端口可访问

#### 1.2 安装基础环境
```bash
# Ubuntu系统
sudo apt update
sudo apt install -y python3 python3-pip git nginx supervisor

# CentOS系统
sudo yum update -y
sudo yum install -y python3 python3-pip git nginx supervisor
```

#### 1.3 安装Python依赖管理工具
```bash
# 安装虚拟环境
sudo pip3 install virtualenv

# 创建项目用户（可选，提高安全性）
sudo useradd -m -s /bin/bash xmind
sudo su - xmind
```

### 2. 项目部署

#### 2.1 克隆项目代码
```bash
# 切换到项目目录
cd /home/xmind  # 或你选择的目录

# 克隆项目
git clone https://github.com/winson-2024/xmind-csv-.git
cd xmind-csv-

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 2.2 配置生产环境
```bash
# 创建生产配置文件
cp team_web_interface_v2.py production_server.py

# 编辑生产配置（修改以下内容）
nano production_server.py
```

在 `production_server.py` 中修改：
```python
if __name__ == '__main__':
    # 生产环境配置
    app.run(
        debug=False,  # 关闭调试模式
        host='0.0.0.0',
        port=5001,
        threaded=True  # 启用多线程
    )
```

#### 2.3 创建系统服务
```bash
# 创建systemd服务文件
sudo nano /etc/systemd/system/xmind-csv.service
```

服务文件内容：
```ini
[Unit]
Description=XMind CSV Converter Service
After=network.target

[Service]
Type=simple
User=xmind
WorkingDirectory=/home/xmind/xmind-csv-
Environment=PATH=/home/xmind/xmind-csv-/venv/bin
ExecStart=/home/xmind/xmind-csv-/venv/bin/python production_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2.4 启动服务
```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start xmind-csv

# 设置开机自启
sudo systemctl enable xmind-csv

# 检查服务状态
sudo systemctl status xmind-csv
```

### 3. Nginx反向代理配置

#### 3.1 创建Nginx配置
```bash
sudo nano /etc/nginx/sites-available/xmind-csv
```

配置内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或IP

    client_max_body_size 50M;  # 允许上传大文件

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件缓存
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 3.2 启用配置
```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/xmind-csv /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 4. 防火墙配置

#### 4.1 阿里云安全组设置
在阿里云控制台配置安全组规则：
- **入方向规则**：
  - 端口80（HTTP）：0.0.0.0/0
  - 端口443（HTTPS）：0.0.0.0/0
  - 端口22（SSH）：你的IP地址/32
  - 端口5001（应用）：0.0.0.0/0（可选，用于直接访问）

#### 4.2 服务器防火墙配置
```bash
# Ubuntu (ufw)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5001/tcp
sudo ufw enable

# CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload
```

### 5. SSL证书配置（可选）

#### 5.1 使用Let's Encrypt免费证书
```bash
# 安装certbot
sudo apt install certbot python3-certbot-nginx  # Ubuntu
# 或
sudo yum install certbot python3-certbot-nginx  # CentOS

# 获取证书
sudo certbot --nginx -d your-domain.com

# 设置自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

### 6. 监控和日志

#### 6.1 查看应用日志
```bash
# 查看服务日志
sudo journalctl -u xmind-csv -f

# 查看Nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

#### 6.2 性能监控
```bash
# 安装htop监控工具
sudo apt install htop  # Ubuntu
sudo yum install htop  # CentOS

# 监控系统资源
htop
```

### 7. 备份和更新

#### 7.1 代码更新
```bash
# 进入项目目录
cd /home/xmind/xmind-csv-

# 拉取最新代码
git pull origin main

# 重启服务
sudo systemctl restart xmind-csv
```

#### 7.2 数据备份
```bash
# 备份上传的文件
sudo tar -czf /backup/xmind-files-$(date +%Y%m%d).tar.gz /tmp/xmind_team_files/

# 设置定期备份
sudo crontab -e
# 添加以下行（每天凌晨2点备份）
0 2 * * * tar -czf /backup/xmind-files-$(date +\%Y\%m\%d).tar.gz /tmp/xmind_team_files/
```

### 8. 故障排除

#### 8.1 常见问题
1. **服务无法启动**
   ```bash
   # 检查Python环境
   /home/xmind/xmind-csv-/venv/bin/python --version
   
   # 检查依赖
   /home/xmind/xmind-csv-/venv/bin/pip list
   ```

2. **端口被占用**
   ```bash
   # 查看端口占用
   sudo netstat -tlnp | grep 5001
   
   # 杀死占用进程
   sudo kill -9 PID
   ```

3. **文件上传失败**
   ```bash
   # 检查临时目录权限
   ls -la /tmp/xmind_team_files/
   sudo chown -R xmind:xmind /tmp/xmind_team_files/
   ```

#### 8.2 性能优化
```bash
# 使用Gunicorn提高性能
pip install gunicorn

# 创建Gunicorn配置
nano gunicorn.conf.py
```

Gunicorn配置：
```python
bind = "127.0.0.1:5001"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 60
max_requests = 1000
max_requests_jitter = 100
```

更新systemd服务：
```ini
ExecStart=/home/xmind/xmind-csv-/venv/bin/gunicorn -c gunicorn.conf.py production_server:app
```

## 访问地址
- **开发环境**：http://localhost:5001
- **生产环境**：http://your-domain.com 或 http://your-server-ip

## 项目结构
```
xmind-csv-/
├── team_web_interface_v2.py    # 主应用文件
├── module_converter_final.py   # 核心转换逻辑
├── requirements.txt            # Python依赖
├── README.md                   # 项目文档
├── static/                     # 静态资源
└── templates/                  # HTML模板
```

## 贡献指南
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证
本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 联系方式
- 项目地址：https://github.com/winson-2024/xmind-csv-
- 问题反馈：https://github.com/winson-2024/xmind-csv-/issues