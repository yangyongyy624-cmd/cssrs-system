#!/bin/bash
# C-SSRS 本地服务启动脚本
#
# 用法：
#   bash scripts/start-local.sh          — 前台运行（调试用）
#   bash scripts/start-local.sh --daemon — 后台运行（生产用）
#
# 要求：
#   - 在包含 backend/ 的目录下运行，或设置 PROJECT_DIR
#   - Python 虚拟环境在 PROJECT_DIR/.venv

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR/..}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
BACKEND_DIR="$PROJECT_DIR/backend"
PID_FILE="$PROJECT_DIR/.cssrs.pid"
LOG_DIR="$PROJECT_DIR/logs"

# ── Check prerequisites ──

if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ 虚拟环境未安装"
    echo "   运行: python3 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt"
    exit 1
fi

if [ ! -f "$BACKEND_DIR/main.py" ]; then
    echo "❌ backend/main.py 不存在"
    echo "   当前目录: $(pwd)"
    exit 1
fi

mkdir -p "$LOG_DIR"

# ── Kill existing process ──

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⏹ 停止旧进程 (PID $OLD_PID)"
        kill "$OLD_PID"
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

# Also kill anything on port 8000
EXISTING=$(lsof -ti :8000 2>/dev/null || true)
if [ -n "$EXISTING" ]; then
    echo "⚠️  端口 8000 被占用，清理中..."
    kill $EXISTING 2>/dev/null || true
    sleep 1
    kill -9 $EXISTING 2>/dev/null || true
    sleep 1
fi

# ── Start ──

if [ "$1" = "--daemon" ]; then
    echo "🚀 启动 C-SSRS 本地服务（后台）..."
    cd "$BACKEND_DIR"
    nohup "$VENV_PYTHON" -m uvicorn main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info \
        >> "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2

    # Verify
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q 200; then
        echo "✅ 服务已启动 (PID $(cat $PID_FILE))"
        echo "   医生端: http://localhost:8000/"
        echo "   患者端: http://localhost:8000/patient.html"
    else
        echo "❌ 启动失败，查看日志: $LOG_DIR/backend.log"
        exit 1
    fi
else
    echo "🚀 启动 C-SSRS 本地服务（前台）..."
    echo "   医生端: http://localhost:8000/"
    echo "   患者端: http://localhost:8000/patient.html"
    cd "$BACKEND_DIR"
    exec "$VENV_PYTHON" -m uvicorn main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info
fi
