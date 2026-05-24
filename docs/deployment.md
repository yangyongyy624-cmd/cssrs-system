# C-SSRS 系统部署指南

## 架构概览

```
患者手机 → 云端轻量网关 (Ubuntu) → SSH 隧道 → 本地 Mac/服务器 (数据存储)
            仅转发,不存储                  加密传输              评分 + 归档
```

| 组件 | 位置 | 功能 |
|------|------|------|
| 云端网关 | Ubuntu 服务器 (端口 8888) | 认证、转发、二维码生成 |
| 本地服务 | Mac mini 或任意服务器 (端口 8000) | 数据存储、评分计算、报告生成 |
| SSH 隧道 | 自动建立 | 加密传输评估数据 (云端 8889 → 本地 8000) |

### 网络端口

| 端口 | 用途 | 方向 |
|------|------|------|
| 8888 | 云端网关 (公开访问) | 入站 |
| 8889 | SSH 反向隧道 (内部) | 云端内部 |
| 8000 | 本地 FastAPI 服务 | 本地 |
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
- 开放防火墙: 端口 22, 8888

### 2.2 安装

```bash
ssh ubuntu@YOUR_SERVER_IP
git clone https://github.com/yangyongyy624-cmd/cssrs-system.git
cd cssrs-system
python3 -m venv backend/.venv
cd backend
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p ~/cssrs-system/logs
```

### 2.3 配置 systemd 服务

```bash
# 从本地拷贝
scp scripts/cssrs-cloud.service ubuntu@YOUR_SERVER_IP:/tmp/

# 在服务器上安装
ssh ubuntu@YOUR_SERVER_IP
sudo cp /tmp/cssrs-cloud.service /etc/systemd/system/
sudo nano /etc/systemd/system/cssrs-cloud.service   # 检查路径
sudo systemctl daemon-reload
sudo systemctl enable cssrs-cloud
sudo systemctl start cssrs-cloud
sudo systemctl status cssrs-cloud
```

### 2.4 防火墙设置

**腾讯云轻量服务器**:
1. 控制台 → 选择服务器 → 防火墙
2. 添加规则: TCP:22, TCP:8888

**腾讯云标准服务器 (安全组)**:
1. VPC → 安全组 → 入站规则
2. 添加: TCP:22, TCP:8888

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

### 3.3 手动启动隧道

```bash
ssh -fN \
  -o GatewayPorts=yes \
  -o ServerAliveInterval=60 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -R 0.0.0.0:8889:127.0.0.1:8000 \
  ubuntu@YOUR_SERVER_IP
```

### 3.4 验证隧道

```bash
# 在云端服务器上执行
curl -s http://127.0.0.1:8889/ -o /dev/null -w "%{http_code}"
# 应返回 200
```

### 3.5 开机自启 (macOS launchd)

创建 `~/Library/LaunchAgents/com.cssrs.tunnel.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cssrs.tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/ssh</string>
        <string>-fN</string>
        <string>-o</string>
        <string>GatewayPorts=yes</string>
        <string>-o</string>
        <string>ServerAliveInterval=60</string>
        <string>-o</string>
        <string>ServerAliveCountMax=3</string>
        <string>-o</string>
        <string>ExitOnForwardFailure=yes</string>
        <string>-R</string>
        <string>0.0.0.0:8889:127.0.0.1:8000</string>
        <string>ubuntu@YOUR_SERVER_IP</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ThrottleInterval</key>
    <integer>30</integer>
    <key>StandardOutPath</key>
    <string>/path/to/cssrs-system/logs/tunnel.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/cssrs-system/logs/tunnel.err.log</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.cssrs.tunnel.plist
```

---

## 第四部分：端到端验证

```bash
# 1. 创建 session
curl -s -X POST http://YOUR_SERVER_IP:8888/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"deploy-test-001","version":"baseline"}'

# 2. 提交评估
curl -s -X POST "http://YOUR_SERVER_IP:8888/api/assess/{session_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "ideation": {"i1_wish_dead":true,"i2_non_specific":true},
    "intensity": {"frequency":2,"duration":1,"controllability":2,"deterrents":1,"reason":1},
    "behavior": {"b1_actual_attempt":false,"b2_interrupted":false,"b3_aborted":false,"b4_preparatory":false,"b5_nssi":false},
    "lethality": 0
  }'

# 3. 验证数据到达本地
curl -s http://localhost:8000/api/summary?limit=1
```

---

## 第五部分：常见问题

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
3. 云端服务未运行 → `sudo systemctl status cssrs-cloud`

### Q: 评估提交后数据丢失

**原因**: SSH 隧道断开，云端无法推送到本地。
**解决**: 数据会暂存在云端 SQLite 中，隧道恢复后手动重推。

### Q: launchd 服务 exit code -15

**原因**: launchd 的 KeepAlive 在进程退出时立即重启，如果端口未释放会反复崩溃。
**解决**: plist 中使用 `SuccessfulExit: false` + `ThrottleInterval: 30` 防止重启风暴。

---

## 数据文件说明

| 文件 | 说明 | 是否公开 |
|------|------|----------|
| `backend/cssrs.db` | SQLite 数据库，含所有评估数据 | ❌ 加入 .gitignore |
| `logs/` | 运行日志 | ❌ 加入 .gitignore |
| `.env` | 环境变量 (如有) | ❌ 加入 .gitignore |
| `.env.example` | 配置模板 | ✅ 公开 |
