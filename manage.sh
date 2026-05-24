#!/bin/bash
# C-SSRS System — Start/Stop/Status scripts

BASE_DIR="$HOME/Developer/cssrs-system"
BACKEND_DIR="$BASE_DIR/backend"
PID_FILE="$BASE_DIR/.server.pid"
LOG_FILE="$BASE_DIR/logs/server.log"

mkdir -p "$BASE_DIR/logs"

start() {
    if is_running; then
        echo "✅ C-SSRS 已在运行 (PID $(cat "$PID_FILE"))"
        echo "   医生端: http://localhost:8000/"
        echo "   患者端: http://$(ipconfig getifaddr en0 2>/dev/null || echo '127.0.0.1'):8000/code"
        return 0
    fi

    echo "🚀 启动 C-SSRS 评估系统..."
    cd "$BACKEND_DIR" && source "$BASE_DIR/.venv/bin/activate"
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"

    sleep 2
    if is_running; then
        echo "✅ C-SSRS 已启动 (PID $(cat "$PID_FILE"))"
        echo "   医生端: http://localhost:8000/"
        local ip=$(ipconfig getifaddr en0 2>/dev/null || echo '127.0.0.1')
        echo "   患者访问: http://$ip:8000/code"
    else
        echo "❌ 启动失败，查看日志: $LOG_FILE"
    fi
}

stop() {
    if ! is_running; then
        echo "ℹ️  C-SSRS 未运行"
        rm -f "$PID_FILE"
        return 0
    fi

    local pid=$(cat "$PID_FILE")
    echo "🛑 停止 C-SSRS (PID $pid)..."
    kill "$pid" 2>/dev/null
    sleep 2

    if is_running; then
        echo "⚠️  进程未退出，强制停止..."
        kill -9 "$pid" 2>/dev/null
    fi

    rm -f "$PID_FILE"
    echo "✅ C-SSRS 已停止"
}

status() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        echo "✅ C-SSRS 运行中 (PID $pid)"
        echo "   医生端: http://localhost:8000/"
        local ip=$(ipconfig getifaddr en0 2>/dev/null || echo '127.0.0.1')
        echo "   患者访问: http://$ip:8000/code"
        echo "   数据库: $BASE_DIR/data/cssrs.db"
        echo "   日志: $LOG_FILE"
    else
        echo "⏸️  C-SSRS 未运行"
        echo "   启动: $0 start"
    fi
}

is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        kill -0 "$pid" 2>/dev/null
        return $?
    fi
    return 1
}

case "${1:-status}" in
    start)  start ;;
    stop)   stop ;;
    status) status ;;
    *)      echo "用法: $0 {start|stop|status}" ;;
esac
