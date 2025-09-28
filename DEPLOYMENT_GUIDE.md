# 阿里云服务器部署快速指南

## 🚀 一键部署（推荐）

### 1. 准备工作
```bash
# 1. 登录阿里云服务器
ssh root@your-server-ip

# 2. 创建普通用户（安全考虑）
useradd -m -s /bin/bash xmind
usermod -aG sudo xmind
su - xmind

# 3. 下载部署脚本
wget https://raw.githubusercontent.com/winson-2024/xmind-csv-/main/deploy.sh
chmod +x deploy.sh
```

### 2. 执行部署
```bash
# 运行一键部署脚本
./deploy.sh
```

脚本会自动完成：
- ✅ 系统环境准备
- ✅ 项目代码下载
- ✅ Python环境配置
- ✅ 服务创建和启动
- ✅ Nginx反向代理配置
- ✅ 防火墙设置
- ✅ SSL证书配置（可选）
- ✅ 备份和更新脚本

### 3. 阿里云安全组配置
在阿里云控制台 → ECS → 安全组 → 配置规则：

| 方向 | 协议 | 端口 | 授权对象 | 说明 |
|------|------|------|----------|------|
| 入方向 | TCP | 22 | 你的IP/32 | SSH访问 |
| 入方向 | TCP | 80 | 0.0.0.0/0 | HTTP访问 |
| 入方向 | TCP | 443 | 0.0.0.0/0 | HTTPS访问 |

## 📋 手动部署步骤

如果需要手动部署，请参考 [README.md](README.md) 中的详细步骤。

## 🔧 部署后管理

### 服务管理
```bash
# 查看服务状态
sudo systemctl status xmind-csv

# 重启服务
sudo systemctl restart xmind-csv

# 查看实时日志
sudo journalctl -u xmind-csv -f

# 查看Nginx状态
sudo systemctl status nginx
```

### 代码更新
```bash
# 使用更新脚本
cd ~/xmind-csv
./update.sh

# 或手动更新
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart xmind-csv
```

### 备份管理
```bash
# 查看备份文件
ls -la /backup/

# 手动备份
sudo /usr/local/bin/backup-xmind.sh

# 恢复备份
sudo tar -xzf /backup/xmind-files-YYYYMMDD_HHMMSS.tar.gz -C /
```

## 🛡️ 安全建议

1. **定期更新系统**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **监控服务状态**
   ```bash
   # 安装监控工具
   sudo apt install htop iotop
   
   # 查看系统资源
   htop
   ```

3. **日志轮转**
   ```bash
   # 配置日志轮转
   sudo nano /etc/logrotate.d/xmind-csv
   ```

4. **防火墙规则**
   ```bash
   # 查看防火墙状态
   sudo ufw status verbose
   
   # 限制SSH访问（可选）
   sudo ufw delete allow 22
   sudo ufw allow from YOUR_IP to any port 22
   ```

## 🔍 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 查看详细错误
   sudo journalctl -u xmind-csv --no-pager
   
   # 检查端口占用
   sudo netstat -tlnp | grep 5001
   ```

2. **Nginx配置错误**
   ```bash
   # 测试配置
   sudo nginx -t
   
   # 查看错误日志
   sudo tail -f /var/log/nginx/error.log
   ```

3. **SSL证书问题**
   ```bash
   # 手动续期证书
   sudo certbot renew --dry-run
   
   # 重新申请证书
   sudo certbot --nginx -d your-domain.com
   ```

4. **文件上传失败**
   ```bash
   # 检查临时目录
   ls -la /tmp/xmind_team_files/
   
   # 修复权限
   sudo chown -R xmind:xmind /tmp/xmind_team_files/
   sudo chmod -R 755 /tmp/xmind_team_files/
   ```

### 性能优化

1. **增加Gunicorn工作进程**
   ```bash
   # 编辑配置文件
   nano ~/xmind-csv/gunicorn.conf.py
   
   # 修改workers数量（建议CPU核心数 * 2 + 1）
   workers = 8
   ```

2. **优化Nginx配置**
   ```bash
   # 编辑Nginx配置
   sudo nano /etc/nginx/sites-available/xmind-csv
   
   # 添加缓存和压缩配置
   gzip on;
   gzip_types text/css application/javascript application/json;
   ```

## 📞 技术支持

- **项目地址**：https://github.com/winson-2024/xmind-csv-
- **问题反馈**：https://github.com/winson-2024/xmind-csv-/issues
- **部署文档**：[README.md](README.md)

## 📈 监控和维护

### 设置监控脚本
```bash
# 创建健康检查脚本
cat > ~/health-check.sh << 'EOF'
#!/bin/bash
if ! curl -f http://localhost:5001 > /dev/null 2>&1; then
    echo "Service is down, restarting..."
    sudo systemctl restart xmind-csv
    # 发送通知（可选）
    # curl -X POST "https://api.telegram.org/botTOKEN/sendMessage" \
    #      -d "chat_id=CHAT_ID&text=XMind服务已重启"
fi
EOF

chmod +x ~/health-check.sh

# 添加到定时任务（每5分钟检查一次）
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/health-check.sh") | crontab -
```

### 日志分析
```bash
# 分析访问日志
sudo tail -f /var/log/nginx/access.log | grep -E "(POST|GET) /"

# 统计访问量
sudo awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -nr | head -10