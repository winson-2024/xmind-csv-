#!/bin/bash

# XMind转CSV团队协作平台 - 阿里云一键部署脚本
# 适用于Ubuntu 20.04 LTS

set -e

echo "🚀 开始部署 XMind转CSV团队协作平台..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}请不要使用root用户运行此脚本${NC}"
   echo "建议创建普通用户: sudo useradd -m -s /bin/bash xmind"
   exit 1
fi

# 获取用户输入
read -p "请输入你的域名或服务器IP地址: " DOMAIN
read -p "是否安装SSL证书? (y/n): " INSTALL_SSL

echo -e "${GREEN}开始安装系统依赖...${NC}"

# 更新系统
sudo apt update

# 安装基础软件
sudo apt install -y python3 python3-pip python3-venv git nginx supervisor curl

# 检查Python版本
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python版本: $PYTHON_VERSION"

if [[ $(echo "$PYTHON_VERSION < 3.8" | bc -l) -eq 1 ]]; then
    echo -e "${RED}Python版本过低，需要3.8+${NC}"
    exit 1
fi

echo -e "${GREEN}克隆项目代码...${NC}"

# 创建项目目录
PROJECT_DIR="$HOME/xmind-csv"
if [ -d "$PROJECT_DIR" ]; then
    echo "项目目录已存在，更新代码..."
    cd "$PROJECT_DIR"
    git pull origin main
else
    git clone https://github.com/winson-2024/xmind-csv-.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

echo -e "${GREEN}设置Python虚拟环境...${NC}"

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 安装生产环境依赖
pip install gunicorn

echo -e "${GREEN}创建生产配置文件...${NC}"

# 创建生产服务器配置
cat > production_server.py << EOF
from team_web_interface_v2 import app

if __name__ == '__main__':
    app.run(
        debug=False,
        host='127.0.0.1',
        port=5001,
        threaded=True
    )
EOF

# 创建Gunicorn配置
cat > gunicorn.conf.py << EOF
bind = "127.0.0.1:5001"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 60
max_requests = 1000
max_requests_jitter = 100
preload_app = True
EOF

echo -e "${GREEN}创建系统服务...${NC}"

# 创建systemd服务文件
sudo tee /etc/systemd/system/xmind-csv.service > /dev/null << EOF
[Unit]
Description=XMind CSV Converter Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/gunicorn -c gunicorn.conf.py team_web_interface_v2:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重载systemd并启动服务
sudo systemctl daemon-reload
sudo systemctl enable xmind-csv
sudo systemctl start xmind-csv

echo -e "${GREEN}配置Nginx反向代理...${NC}"

# 创建Nginx配置
sudo tee /etc/nginx/sites-available/xmind-csv > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# 启用站点
sudo ln -sf /etc/nginx/sites-available/xmind-csv /etc/nginx/sites-enabled/

# 删除默认站点
sudo rm -f /etc/nginx/sites-enabled/default

# 测试Nginx配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx

echo -e "${GREEN}配置防火墙...${NC}"

# 配置UFW防火墙
sudo ufw --force enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# SSL证书配置
if [[ "$INSTALL_SSL" == "y" || "$INSTALL_SSL" == "Y" ]]; then
    echo -e "${GREEN}安装SSL证书...${NC}"
    
    # 安装certbot
    sudo apt install -y certbot python3-certbot-nginx
    
    # 获取证书
    sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN"
    
    # 设置自动续期
    (sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | sudo crontab -
fi

echo -e "${GREEN}创建备份脚本...${NC}"

# 创建备份目录
sudo mkdir -p /backup

# 创建备份脚本
sudo tee /usr/local/bin/backup-xmind.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf "$BACKUP_DIR/xmind-files-$DATE.tar.gz" /tmp/xmind_team_files/ 2>/dev/null || true
# 保留最近7天的备份
find "$BACKUP_DIR" -name "xmind-files-*.tar.gz" -mtime +7 -delete
EOF

sudo chmod +x /usr/local/bin/backup-xmind.sh

# 设置定期备份
(sudo crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-xmind.sh") | sudo crontab -

echo -e "${GREEN}创建更新脚本...${NC}"

# 创建更新脚本
cat > update.sh << 'EOF'
#!/bin/bash
cd "$HOME/xmind-csv"
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart xmind-csv
echo "更新完成！"
EOF

chmod +x update.sh

echo -e "${GREEN}检查服务状态...${NC}"

# 等待服务启动
sleep 5

# 检查服务状态
if sudo systemctl is-active --quiet xmind-csv; then
    echo -e "${GREEN}✅ XMind服务运行正常${NC}"
else
    echo -e "${RED}❌ XMind服务启动失败${NC}"
    sudo systemctl status xmind-csv
fi

if sudo systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx服务运行正常${NC}"
else
    echo -e "${RED}❌ Nginx服务启动失败${NC}"
    sudo systemctl status nginx
fi

# 测试HTTP连接
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
    echo -e "${GREEN}✅ HTTP服务可访问${NC}"
else
    echo -e "${YELLOW}⚠️  HTTP服务可能有问题，请检查${NC}"
fi

echo -e "${GREEN}🎉 部署完成！${NC}"
echo ""
echo "📍 访问地址："
if [[ "$INSTALL_SSL" == "y" || "$INSTALL_SSL" == "Y" ]]; then
    echo "   https://$DOMAIN"
else
    echo "   http://$DOMAIN"
fi
echo ""
echo "🔧 管理命令："
echo "   查看服务状态: sudo systemctl status xmind-csv"
echo "   重启服务: sudo systemctl restart xmind-csv"
echo "   查看日志: sudo journalctl -u xmind-csv -f"
echo "   更新代码: ./update.sh"
echo ""
echo "📁 重要路径："
echo "   项目目录: $PROJECT_DIR"
echo "   配置文件: /etc/nginx/sites-available/xmind-csv"
echo "   服务文件: /etc/systemd/system/xmind-csv.service"
echo "   备份目录: /backup"
echo ""
echo "🛡️  安全提醒："
echo "   1. 请在阿里云控制台配置安全组规则"
echo "   2. 定期更新系统和应用"
echo "   3. 监控服务运行状态"
echo ""