#!/bin/bash
# revo_ugv_ros2 环境设置脚本
# 将外部 SDK 路径添加到 PYTHONPATH

export REVO_SDK_ROOT="/home/orin/Workspace/agri_ugv/sdk/xag/R100/agri_ugv_v1/revosdk"
export PYTHONPATH="${REVO_SDK_ROOT}:${PYTHONPATH}"

echo "Revo SDK PYTHONPATH 已设置: ${REVO_SDK_ROOT}"
