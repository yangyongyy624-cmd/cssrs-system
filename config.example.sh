#!/bin/bash
# C-SSRS 系统配置模板
# 复制此文件为 config.sh 并填入实际值

# 云端服务器
export CLOUD_HOST="ubuntu@YOUR_SERVER_IP"
export CLOUD_DIR="/home/ubuntu/cssrs-system"

# 本地路径
export LOCAL_DIR="$HOME/Developer/cssrs-system"
export LOCAL_DB="$LOCAL_DIR/data/cssrs.db"

# 端口配置
export LOCAL_PORT=8000
export CLOUD_PORT=8888

# 防火墙设置
# 需要在云端控制台开放端口: 22, 8888
