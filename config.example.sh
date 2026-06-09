#!/bin/bash
# C-SSRS 系统配置模板
# 复制此文件为 config.sh 并填入实际值

# 云端服务器
export CLOUD_HOST="ubuntu@YOUR_SERVER_IP"
export CLOUD_DIR="/home/ubuntu/cssrs-system"

# 本地路径
export LOCAL_DIR="$HOME/Developer/cssrs-system"
export LOCAL_DB="$LOCAL_DIR/backend/cssrs.db"

# 端口配置
export LOCAL_PORT=8000      # C-SSRS 本地服务
export LOCAL_TDM_PORT=8001  # TDM 本地服务
export CLOUD_PORT=8888      # C-SSRS 云端网关
export CLOUD_TDM_PORT=8890  # TDM 云端网关
export SSH_CSSRS_PORT=8889  # C-SSRS SSH 隧道端口
export SSH_TDM_PORT=8891    # TDM SSH 隧道端口

# 防火墙设置
# 需要在云端控制台开放端口: 22, 8888, 8890
