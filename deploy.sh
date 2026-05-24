#!/bin/bash
# C-SSRS 系统管理 — Mac mini 本地运行，云端仅转发
#
# 架构：
#   Mac mini: FastAPI 服务 (launchd 管理) + SQLite 数据存储
#   云端 YOUR_SERVER_IP: 轻量网关，仅转发，不存储评估数据
#   SSH 反向隧道: 云端 8888 → Mac mini 8000
#
# 用法：
#   ./manage.sh start/stop/status  — 本地服务管理
#   ./expose-tunnel.sh start/stop/status — 隧道管理

set -e

case "${1:-status}" in
    start)
        bash "$(dirname "$0")/manage.sh" start
        ;;
    stop)
        bash "$(dirname "$0")/manage.sh" stop
        bash "$(dirname "$0")/expose-tunnel.sh" stop 2>/dev/null || true
        ;;
    expose)
        bash "$(dirname "$0")/expose-tunnel.sh" start
        ;;
    status)
        echo "=== C-SSRS 系统状态 ==="
        echo ""
        bash "$(dirname "$0")/manage.sh" status
        echo ""
        echo "--- 公网隧道 ---"
        bash "$(dirname "$0")/expose-tunnel.sh" status 2>/dev/null || echo "  隧道未运行"
        echo ""
        echo "  患者访问: http://YOUR_SERVER_IP:8888/code"
        echo "  医生端:   http://localhost:8000/"
        ;;
    sync-frontend)
        echo "同步前端文件到云端..."
        scp ~/Developer/cssrs-system/frontend/*.html ubuntu@YOUR_SERVER_IP:/home/ubuntu/cssrs-system/frontend/
        echo "✅ 前端已同步"
        ;;
    *)
        echo "用法: $0 {start|stop|expose|status|sync-frontend}"
        echo ""
        echo "  start           启动本地服务"
        echo "  stop            停止本地服务和隧道"
        echo "  expose          启动公网访问（SSH 反向隧道）"
        echo "  status          查看服务状态"
        echo "  sync-frontend   同步前端到云端"
        ;;
esac
