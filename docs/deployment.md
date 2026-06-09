# C-SSRS 系统部署指南

**作者**：杨勇（Yang Yong），武汉市普仁医院精神科医生

## 架构概览

```
患者手机(流量) → 云端网关(YOUR_SERVER_IP:PORT) → SSH隧道(8889) → 本地电脑(8000)
医生手机(流量) → 云端网关(YOUR_SERVER_IP:PORT) → SSH隧道(8889) → 本地电脑(8000)
```

| 组件 | 位置 | 功能 |
|------|------|------|
| 云端网关 | Ubuntu 服务器 (Nginx PORT) | 纯转发，不存储任何评估数据 |
| SSH 隧道 | 自动建立 | 加密传输 (云端 8889 → 本地 8000) |
| 本地服务 | Mac/PC (FastAPI 8000) | 数据存储、评分计算、报告生成 |

### 网络端口

| 端口 | 用途 | 方向 |
|------|------|------|
| PORT | 云端网关 (公开访问) | 入站 |
| 8889 | SSH 反向隧道 (内部) | 云端内部 |
| 8000 | 本地 C-SSRS 服务 | 本地 |
| 22 | SSH | 入站 |

---

## 第一部分：本地服务部署

### 1.1 环境准备

```bash
git clone https://github.com/yangyongyy624-cmd/cssrs-system.git
cd cssrs-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
mkdir -p logs
```

### 1.2 启动服务

```bash
# 前台运行 (调试)
bash scripts/start-local.sh

# 后台运行 (生产)
bash scripts/start-local.sh --daemon

# 验证
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

### 1.3 开机自启 (macOS)

```bash
# 编辑 plist 中的 PROJECT_DIR 路径
nano scripts/com.cssrs.system.plist

# 安装
cp scripts/com.cssrs.system.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cssrs.system.plist
launchctl list | grep cssrs
```

### 1.4 开机自启 (Linux systemd)

```bash
sudo cp scripts/cssrs-local.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cssrs-local
sudo systemctl start cssrs-local
```

---

## 第二部分：云端网关部署

### 2.1 服务器要求

- Ubuntu 22.04+ (推荐腾讯云轻量，1核1G即可)
- 开放防火墙: 端口 22, PORT

### 2.2 安装 Nginx

```bash
ssh ubuntu@YOUR_SERVER_IP
sudo apt update
sudo apt install -y nginx
```

### 2.3 配置 Nginx

```bash
sudo nano /etc/nginx/conf.d/cssrs.conf
```

```nginx
server {
    listen 8888;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8889;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo nginx -t
sudo systemctl restart nginx
```

### 2.4 防火墙设置

**腾讯云轻量服务器**:
1. 控制台 → 选择服务器 → 防火墙
2. 添加规则: TCP:22, TCP:8888

---

## 第三部分：SSH 隧道

### 3.1 原理

```
云端 :8889  →  SSH 反向隧道  →  本地 :8000
```

### 3.2 配置免密登录

```bash
# 本地生成密钥 (如果没有)
ssh-keygen -t ed25519 -C "cssrs-tunnel"

# 拷贝到云端
ssh-copy-id ubuntu@YOUR_SERVER_IP
```

### 3.3 启动隧道

```bash
ssh -fN \
  -o ServerAliveInterval=60 \
  -o ServerAliveCountMax=3 \
  -o StrictHostKeyChecking=no \
  -o ExitOnForwardFailure=yes \
  -R 8889:127.0.0.1:8000 \
  ubuntu@YOUR_SERVER_IP
```

### 3.4 验证隧道

```bash
# 在云端服务器上执行
ssh ubuntu@YOUR_SERVER_IP "ss -tlnp | grep 8889"
```

### 3.5 开机自启 (macOS launchd)

创建 `~/Library/LaunchAgents/com.cssrs.tunnel.plist`，配置 SSH 隧道参数。

```bash
launchctl load ~/Library/LaunchAgents/com.cssrs.tunnel.plist
```

---

## 第四部分：二维码生成

### 4.1 医生入口二维码

```bash
# 使用 Python qrcode 库生成
python3 -c "
import qrcode
qr = qrcode.QRCode(version=1, box_size=10, border=4)
qr.add_data('http://YOUR_SERVER_IP:PORT/')
qr.make(fit=True)
img = qr.make_image(fill_color='black', back_color='white')
img.save('doctor-entry-qr.png')
"
```

生成后可访问 `http://YOUR_SERVER_IP:PORT/doctor-qr` 查看，或直接截图保存。

### 4.2 患者二维码

由医生端自动生成，每次新建评估时系统生成：
- 患者二维码图片
- 6 位访问码（备用）

---

## 第五部分：系统验证

```bash
# 1. 验证入口页
curl -s -o /dev/null -w "入口页: HTTP %{http_code}\n" http://YOUR_SERVER_IP:PORT/

# 2. 验证医生端
curl -s -o /dev/null -w "医生端: HTTP %{http_code}\n" http://YOUR_SERVER_IP:PORT/mobile

# 3. 验证管理后台
curl -s -o /dev/null -w "管理后台: HTTP %{http_code}\n" http://YOUR_SERVER_IP:PORT/admin

# 4. 验证医生入口二维码页
curl -s -o /dev/null -w "二维码页: HTTP %{http_code}\n" http://YOUR_SERVER_IP:PORT/doctor-qr
```

---

## 第六部分：常见问题

### Q: 本地服务频繁崩溃

**原因**: 端口被占用或 venv 路径不正确。
**解决**: 使用 `scripts/start-local.sh --daemon` 启动，脚本会自动清理旧进程。

### Q: SSH 隧道建立失败

**原因**: 云端 8889 端口被旧的 sshd 子进程占用。
**解决**:
```bash
ssh ubuntu@YOUR_SERVER_IP "sudo lsof -i :8889"   # 找到 PID
ssh ubuntu@YOUR_SERVER_IP "sudo kill <PID>"       # 杀掉
# 重新建立隧道
```

### Q: 患者扫码后打不开

**原因**:
1. 微信内置浏览器会拦截外部链接 → 用系统相机扫码
2. 防火墙未开放 8888 → 检查腾讯云控制台
3. SSH 隧道断开 → 重新建立隧道

### Q: 502 Bad Gateway

**原因**: SSH 隧道断开，云端无法连接到本地服务。
**解决**: 重新建立 SSH 隧道。

### Q: 如何打印医生入口二维码？

访问 `http://YOUR_SERVER_IP:PORT/doctor-qr`，截图或打印该页面即可。

---

## 数据文件说明

| 文件 | 说明 | 是否公开 |
|------|------|----------|
| `backend/cssrs.db` | SQLite 数据库（本地），含所有评估数据 | ❌ 加入 .gitignore |
| `logs/` | 运行日志 | ❌ 加入 .gitignore |
| `.env` | 环境变量 (如有) | ❌ 加入 .gitignore |
| `.env.example` | 配置模板 | ✅ 公开 |
| `config.sh` | 个人配置（含服务器地址等） | ❌ 加入 .gitignore |
