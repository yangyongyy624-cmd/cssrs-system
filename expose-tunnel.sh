#!/bin/bash
# C-SSRS SSH 反向隧道 — 将本地 8000 暴露到云端
# 用途：临时让外出患者通过公网访问本地服务
# 数据不经过云端存储，仅转发

set -e

CLOUD_HOST="ubuntu@YOUR_SERVER_IP"
LOCAL_PORT=8000
CLOUD_PORT=8888

case "${1:-start}" in
    start)
        echo "🔗 启动 SSH 反向隧道..."
        echo "   本地 :$LOCAL_PORT → 云端 YOUR_SERVER_IP:$CLOUD_PORT"
        ssh -fN -R $CLOUD_PORT:127.0.0.1:$LOCAL_PORT $CLOUD_HOST
        echo "✅ 隧道已建立"
        echo "   患者访问: http://YOUR_SERVER_IP:$CLOUD_PORT/code"
        echo "   关闭: $0 stop"
        ;;
    stop)
        echo "🛑 关闭 SSH 反向隧道..."
        ssh $CLOUD_HOST "kill \$(lsof -ti:$CLOUD_PORT) 2>/dev/null || true"
        echo "✅ 隧道已关闭"
        ;;
    status)
        ssh $CLOUD_HOST "ss -tlnp | grep $CLOUD_PORT 2>/dev/null && echo '隧道活跃' || echo '隧道未运行'"
        ;;
    *)
        echo "用法: $0 {start|stop|status}"
        ;;
esac
