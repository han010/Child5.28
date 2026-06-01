#!/usr/bin/env python3
"""
农业UGV系统架构图生成器
生成适合面试展示的高质量PNG架构图
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# ====== 字体设置 ======
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'DejaVu Sans', 'AR PL UMing CN']
plt.rcParams['axes.unicode_minus'] = False

# ====== 颜色方案 ======
COLORS = {
    'bg': '#0f172a',
    'layer_app': ('#065f46', '#10b981'),        # 绿色 - 应用层
    'layer_perc': ('#4c1d95', '#8b5cf6'),        # 紫色 - 感知层
    'layer_bridge': ('#1e3a5f', '#3b82f6'),      # 蓝色 - 桥接层
    'layer_sdk': ('#78350f', '#f59e0b'),          # 黄色 - SDK层
    'layer_hw': ('#7f1d1d', '#ef4444'),           # 红色 - 硬件层
    'card_bg': '#1e293b',
    'card_border': '#334155',
    'text': '#f1f5f9',
    'text_sub': '#94a3b8',
    'text_dim': '#64748b',
    'white': '#ffffff',
    'tag_python': '#3b82f6',
    'tag_cpp': '#0ea5e9',
    'tag_udp': '#22c55e',
    'tag_can': '#ef4444',
    'tag_ekf': '#a78bfa',
    'tag_trt': '#84cc16',
    'tag_ros': '#f97316',
}

def hex_to_rgba(hex_color, alpha=1.0):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16)/255 for i in (0,2,4)) + (alpha,)

def draw_layer_bg(ax, x, y, w, h, color_pair, label, label_en):
    """绘制层背景"""
    bg_color = hex_to_rgba(color_pair[0], 0.85)
    border_color = color_pair[1]
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.01",
        facecolor=bg_color,
        edgecolor=hex_to_rgba(border_color, 0.8),
        linewidth=2.0,
        zorder=1
    )
    ax.add_patch(rect)
    # 层标签
    ax.text(x + 0.01, y + h - 0.008, f'{label} / {label_en}',
            fontsize=8, fontweight='bold', color=hex_to_rgba(border_color, 0.7),
            va='top', zorder=2)

def draw_card(ax, x, y, w, h, title, lines, tag_text=None, tag_color=None):
    """绘制模块卡片"""
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.004",
        facecolor=hex_to_rgba(COLORS['card_bg'], 0.9),
        edgecolor=hex_to_rgba(COLORS['card_border'], 0.6),
        linewidth=1.0,
        zorder=3
    )
    ax.add_patch(rect)
    # 标题
    ax.text(x + w/2, y + h - 0.012, title,
            fontsize=9, fontweight='bold', color=COLORS['text'],
            ha='center', va='top', zorder=4)
    # 描述行
    for i, line in enumerate(lines):
        ax.text(x + w/2, y + h - 0.028 - i*0.013, line,
                fontsize=7, color=COLORS['text_sub'],
                ha='center', va='top', zorder=4, family='monospace' if line.startswith('/') else 'sans-serif')
    # 标签
    if tag_text and tag_color:
        tag_y = y + 0.005
        tag_rect = FancyBboxPatch(
            (x + w/2 - 0.028, tag_y), 0.056, 0.014,
            boxstyle="round,pad=0.002",
            facecolor=hex_to_rgba(tag_color, 0.2),
            edgecolor=hex_to_rgba(tag_color, 0.4),
            linewidth=0.8,
            zorder=5
        )
        ax.add_patch(tag_rect)
        ax.text(x + w/2, tag_y + 0.007, tag_text,
                fontsize=6, fontweight='bold', color=tag_color,
                ha='center', va='center', zorder=6)

def draw_sensor_chip(ax, x, y, w, h, name, topic):
    """绘制传感器芯片"""
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.003",
        facecolor=hex_to_rgba(COLORS['card_bg'], 0.6),
        edgecolor=hex_to_rgba(COLORS['card_border'], 0.4),
        linewidth=0.8,
        zorder=3
    )
    ax.add_patch(rect)
    ax.text(x + w/2, y + h/2 + 0.005, name,
            fontsize=7, fontweight='bold', color=COLORS['text'],
            ha='center', va='center', zorder=4)
    ax.text(x + w/2, y + h/2 - 0.006, topic,
            fontsize=5.5, color=COLORS['text_sub'],
            ha='center', va='center', zorder=4, family='monospace')

def draw_arrow(ax, x, y_start, y_end, label=None, color='#475569'):
    """绘制层间箭头"""
    ax.annotate('',
        xy=(x, y_end), xytext=(x, y_start),
        arrowprops=dict(arrowstyle='->', color=hex_to_rgba(color, 0.5), lw=1.5),
        zorder=2
    )
    if label:
        ax.text(x + 0.005, (y_start + y_end)/2, label,
                fontsize=6, color=COLORS['text_dim'], va='center', zorder=2)


def main():
    fig, ax = plt.subplots(1, 1, figsize=(22, 16), dpi=150)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('auto')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['bg'])

    # ====== 尺寸常量 ======
    W = 0.94        # 总宽度
    X0 = 0.03       # 左边距
    CARD_W = 0.13   # 卡片宽度
    CARD_H = 0.085  # 卡片高度
    SENSOR_W = 0.09
    SENSOR_H = 0.035

    # ====== 标题 ======
    ax.text(0.5, 0.975, 'Agricultural UGV System Architecture',
            fontsize=22, fontweight='bold', color=COLORS['white'],
            ha='center', va='top')
    ax.text(0.5, 0.958, 'XAG Revo R100 (UDP)  •  Agilex Hunter SE (CAN)  •  ROS2 Humble  •  Jetson Orin',
            fontsize=10, color=COLORS['text_dim'], ha='center', va='top')

    # ====================================================================
    # LAYER 5: 应用层 (y: 0.87 - 0.95)
    # ====================================================================
    Y5 = 0.87
    H5 = 0.08
    draw_layer_bg(ax, X0, Y5, W, H5, COLORS['layer_app'], '应用层', 'Application')

    cx = X0 + 0.04
    cy = Y5 + 0.008
    draw_card(ax, cx, cy, CARD_W, CARD_H, '🎮 键盘遥控',
              ['Teleop Keyboard', '/revo/cmd_vel'], tag_text='Teleop', tag_color=COLORS['tag_ros'])
    cx += CARD_W + 0.02
    draw_card(ax, cx, cy, CARD_W, CARD_H, '🗺️ Nav2 室内导航',
              ['SLAM地图 + Nav2', '路径规划 / 避障'], tag_text='Navigation2', tag_color=COLORS['tag_ros'])
    cx += CARD_W + 0.02
    draw_card(ax, cx, cy, CARD_W, CARD_H, '🛰️ GPS 航点导航',
              ['WGS84→ENU转换', '多点航迹规划'], tag_text='gps_nav2', tag_color=COLORS['tag_ros'])
    cx += CARD_W + 0.02
    draw_card(ax, cx, cy, CARD_W, CARD_H, '🔍 YOLO 障碍物检测',
              ['YOLOv8n / TensorRT', '/yolo_obstacles'], tag_text='TensorRT', tag_color=COLORS['tag_trt'])
    cx += CARD_W + 0.02
    draw_card(ax, cx, cy, CARD_W, CARD_H, '🖥️ Foxglove 调试',
              ['WebSocket Bridge', ':8765 实时可视化'], tag_text='Debug', tag_color=COLORS['tag_ros'])

    # ====== 箭头: 应用 → 感知 ======
    arrow_y1 = Y5
    arrow_y2 = Y5 - 0.015
    ax.annotate('', xy=(0.3, arrow_y2), xytext=(0.3, arrow_y1),
                arrowprops=dict(arrowstyle='->', color='#6ee7b788', lw=1.5), zorder=2)
    ax.annotate('', xy=(0.7, arrow_y2), xytext=(0.7, arrow_y1),
                arrowprops=dict(arrowstyle='->', color='#6ee7b788', lw=1.5), zorder=2)
    ax.text(0.5, (arrow_y1+arrow_y2)/2, '/cmd_vel  /nav_goal  /gps_waypoints',
            fontsize=6, color=COLORS['text_dim'], ha='center', va='center', zorder=2)

    # ====================================================================
    # LAYER 4: 感知与定位层 (y: 0.74 - 0.855)
    # ====================================================================
    Y4 = 0.74
    H4 = 0.085
    draw_layer_bg(ax, X0, Y4, W, H4, COLORS['layer_perc'], '感知与定位层', 'Perception & Localization')

    cx = X0 + 0.04
    cy = Y4 + 0.008
    draw_card(ax, cx, cy, CARD_W + 0.02, CARD_H, '🧭 EKF 室内定位',
              ['轮速计(vx) + IMU(yaw)', '/odometry/filtered'], tag_text='robot_localization', tag_color=COLORS['tag_ekf'])
    cx += CARD_W + 0.04
    draw_card(ax, cx, cy, CARD_W + 0.02, CARD_H, '🛰️ EKF 室外定位',
              ['GPS(x,y) + IMU + 轮速计', '多源传感器融合'], tag_text='GPS + IMU Fusion', tag_color=COLORS['tag_ekf'])
    cx += CARD_W + 0.04
    draw_card(ax, cx, cy, CARD_W, CARD_H, '🏗️ SLAM 建图',
              ['slam_toolbox', 'LiDAR在线建图'], tag_text='slam_toolbox', tag_color=COLORS['tag_ros'])
    cx += CARD_W + 0.02
    draw_card(ax, cx, cy, CARD_W, CARD_H, '🧠 YOLOv8 感知',
              ['YOLOv8n→TensorRT', '实时障碍物检测'], tag_text='TensorRT 640×640', tag_color=COLORS['tag_trt'])
    cx += CARD_W + 0.02
    draw_card(ax, cx, cy, CARD_W, CARD_H, '📊 TF 树管理',
              ['odom→base_footprint', '→base_link→lidar/cam'], tag_text='tf2', tag_color=COLORS['tag_ros'])

    # ====== 箭头: 感知 → 桥接 ======
    arrow_y1 = Y4
    arrow_y2 = Y4 - 0.015
    ax.annotate('', xy=(0.2, arrow_y2), xytext=(0.2, arrow_y1),
                arrowprops=dict(arrowstyle='->', color='#c4b5fd88', lw=1.5), zorder=2)
    ax.annotate('', xy=(0.5, arrow_y2), xytext=(0.5, arrow_y1),
                arrowprops=dict(arrowstyle='->', color='#c4b5fd88', lw=1.5), zorder=2)
    ax.annotate('', xy=(0.8, arrow_y2), xytext=(0.8, arrow_y1),
                arrowprops=dict(arrowstyle='->', color='#c4b5fd88', lw=1.5), zorder=2)
    ax.text(0.5, (arrow_y1+arrow_y2)/2, '/revo/pose  /revo/imu  /odom  /scan  /image_raw',
            fontsize=6, color=COLORS['text_dim'], ha='center', va='center', zorder=2)

    # ====================================================================
    # LAYER 3: ROS2 适配层 (y: 0.49 - 0.725)
    # ====================================================================
    Y3 = 0.49
    H3 = 0.235
    draw_layer_bg(ax, X0, Y3, W, H3, COLORS['layer_bridge'], 'ROS2 适配层', 'ROS2 Adaptation Layer (Bridge Nodes)')

    # ---- Revo 平台 ----
    revo_x = X0 + 0.01
    revo_y = Y3 + 0.008
    revo_w = W * 0.52
    revo_h = 0.10
    revo_bg = FancyBboxPatch(
        (revo_x, revo_y), revo_w, revo_h,
        boxstyle="round,pad=0.005",
        facecolor=hex_to_rgba('#22c55e', 0.08),
        edgecolor=hex_to_rgba('#22c55e', 0.3),
        linewidth=1.0, zorder=2
    )
    ax.add_patch(revo_bg)
    ax.plot(revo_x + 0.012, revo_y + revo_h - 0.01, 'o', color='#22c55e', markersize=6, zorder=3)
    ax.text(revo_x + 0.02, revo_y + revo_h - 0.01, 'XAG Revo R100 / R200 — UDP 适配',
            fontsize=9, fontweight='bold', color='#6ee7b7', va='center', zorder=3)

    cx = revo_x + 0.02
    cy = revo_y + 0.005
    cw = 0.135
    ch = 0.065
    draw_card(ax, cx, cy, cw, ch, 'revo_bridge_node',
              ['SDK → ROS Topics', 'PoseState / Imu / Status', 'cmd_vel → SDK控制'], tag_text='Python/rclpy', tag_color=COLORS['tag_python'])
    cx += cw + 0.012
    draw_card(ax, cx, cy, cw, ch, 'revo_odom_node',
              ['IMU航向+轮速积分', '平滑滤波 α=0.5', '→ /odom + TF'], tag_text='Python/rclpy', tag_color=COLORS['tag_python'])
    cx += cw + 0.012
    draw_card(ax, cx, cy, cw, ch, 'revo_gnss_node',
              ['NMEA → NavSatFix', '/gps/fix', 'WGS84坐标输出'], tag_text='Python/rclpy', tag_color=COLORS['tag_python'])

    # ---- Hunter 平台 ----=
    hunter_x = X0 + 0.01 + revo_w + 0.01
    hunter_y = Y3 + 0.008
    hunter_w = W - revo_w - 0.03
    hunter_h = 0.10
    hunter_bg = FancyBboxPatch(
        (hunter_x, hunter_y), hunter_w, hunter_h,
        boxstyle="round,pad=0.005",
        facecolor=hex_to_rgba('#3b82f6', 0.08),
        edgecolor=hex_to_rgba('#3b82f6', 0.3),
        linewidth=1.0, zorder=2
    )
    ax.add_patch(hunter_bg)
    ax.plot(hunter_x + 0.012, hunter_y + hunter_h - 0.01, 'o', color='#3b82f6', markersize=6, zorder=3)
    ax.text(hunter_x + 0.02, hunter_y + hunter_h - 0.01, 'Agilex Hunter SE — CAN 适配',
            fontsize=9, fontweight='bold', color='#93c5fd', va='center', zorder=3)

    cx = hunter_x + 0.02
    cy = hunter_y + 0.005
    cw = 0.155
    draw_card(ax, cx, cy, cw, 0.065, 'hunter_base_node',
              ['CAN → ROS Topics', 'Odom / Status / TF', '自行车运动模型'], tag_text='C++/rclcpp', tag_color=COLORS['tag_cpp'])

    # ---- 传感器驱动条 ----=
    sensor_y = Y3 + 0.008 + 0.005
    sx = X0 + 0.02
    sw = 0.1
    sensors = [
        ('📡 RPLIDAR A1', '/scan'),
        ('🌍 GPS (NMEA)', '/gps/fix'),
        ('📷 Astra Camera', '/image_raw'),
        ('📻 MR20 毫米波', '/mmwave'),
        ('🔗 Serial ROS2', '/serial_data'),
    ]
    # 居中
    total_sw = len(sensors) * (sw + 0.01) - 0.01
    sx = 0.5 - total_sw/2
    sensor_y = Y3 + 0.005
    for name, topic in sensors:
        draw_sensor_chip(ax, sx, sensor_y, sw, 0.04, name, topic)
        sx += sw + 0.01

    # ====== 箭头: 桥接 → SDK ======
    arrow_y1 = Y3
    arrow_y2 = Y3 - 0.015
    ax.annotate('', xy=(0.3, arrow_y2), xytext=(0.3, arrow_y1),
                arrowprops=dict(arrowstyle='->', color='#93c5fd88', lw=1.5), zorder=2)
    ax.annotate('', xy=(0.7, arrow_y2), xytext=(0.7, arrow_y1),
                arrowprops=dict(arrowstyle='->', color='#93c5fd88', lw=1.5), zorder=2)
    ax.text(0.5, (arrow_y1+arrow_y2)/2, 'SDK API (Python)  |  SDK API (C++)  |  USB/UART',
            fontsize=6, color=COLORS['text_dim'], ha='center', va='center', zorder=2)

    # ====================================================================
    # LAYER 2: SDK 层 (y: 0.35 - 0.475)
    # ====================================================================
    Y2 = 0.35
    H2 = 0.11
    draw_layer_bg(ax, X0, Y2, W, H2, COLORS['layer_sdk'], '硬件抽象层', 'Hardware Abstraction (SDK)')

    cx = X0 + 0.04
    cy = Y2 + 0.008
    draw_card(ax, cx, cy, CARD_W + 0.04, CARD_H, '📦 Revo SDK',
              ['Python / UDP协议', '192.168.234.1:10151', '二进制小端序 / 50Hz'], tag_text='UDP Socket', tag_color=COLORS['tag_udp'])
    cx += CARD_W + 0.06
    draw_card(ax, cx, cy, CARD_W + 0.04, CARD_H, '📦 UGV SDK',
              ['C++ / CAN协议V2', '500K波特率', 'gs_usb CAN适配器'], tag_text='CAN Bus', tag_color=COLORS['tag_can'])
    cx += CARD_W + 0.06
    draw_card(ax, cx, cy, CARD_W + 0.04, CARD_H, '📦 Sensor Drivers',
              ['rplidar_ros / serial_ros2', 'wheeltec_gps / astra_cam', 'wheeltec_radar'], tag_text='ROS2 Packages', tag_color=COLORS['tag_ros'])
    cx += CARD_W + 0.06
    draw_card(ax, cx, cy, CARD_W + 0.04, CARD_H, '📦 Revosdk Protocol',
              ['PoseData 解析器', '控制命令编码器', '心跳保活管理'], tag_text='Binary Protocol', tag_color=COLORS['tag_udp'])

    # ====== 箭头: SDK → 硬件 ======
    arrow_y1 = Y2
    arrow_y2 = Y2 - 0.015
    ax.annotate('', xy=(0.3, arrow_y2), xytext=(0.3, arrow_y1),
                arrowprops=dict(arrowstyle='->', color='#fcd34d88', lw=1.5), zorder=2)
    ax.annotate('', xy=(0.7, arrow_y2), xytext=(0.7, arrow_y1),
                arrowprops=dict(arrowstyle='->', color='#fcd34d88', lw=1.5), zorder=2)
    ax.text(0.5, (arrow_y1+arrow_y2)/2, 'UDP Socket  |  CAN Frame  |  USB / UART',
            fontsize=6, color=COLORS['text_dim'], ha='center', va='center', zorder=2)

    # ====================================================================
    # LAYER 1: 硬件层 (y: 0.10 - 0.335)
    # ====================================================================
    Y1 = 0.10
    H1 = 0.235
    draw_layer_bg(ax, X0, Y1, W, H1, COLORS['layer_hw'], '硬件层', 'Hardware Layer')

    # ---- Revo 硬件 ----=
    revo_x = X0 + 0.01
    revo_y = Y1 + 0.008
    revo_w = W * 0.52
    revo_h = 0.10
    revo_bg = FancyBboxPatch(
        (revo_x, revo_y), revo_w, revo_h,
        boxstyle="round,pad=0.005",
        facecolor=hex_to_rgba('#ef4444', 0.08),
        edgecolor=hex_to_rgba('#ef4444', 0.3),
        linewidth=1.0, zorder=2
    )
    ax.add_patch(revo_bg)
    ax.plot(revo_x + 0.012, revo_y + revo_h - 0.01, 'o', color='#ef4444', markersize=6, zorder=3)
    ax.text(revo_x + 0.02, revo_y + revo_h - 0.01, 'XAG Revo R100 / R200 — 农业机器人平台',
            fontsize=9, fontweight='bold', color='#fca5a5', va='center', zorder=3)

    cx = revo_x + 0.02
    cy = revo_y + 0.005
    cw = 0.1
    ch = 0.05
    hw_cards_revo = [
        ('底盘控制器', ['UDP网络连接', '双轮差速驱动']),
        ('内置 IMU', ['航向角 / 角速度', '轮速计']),
        ('内置 GNSS', ['RTK定位', '经纬度 / 海拔']),
        ('电池系统', ['48V锂电池', '电量 / 功率监控']),
    ]
    for title, lines in hw_cards_revo:
        draw_card(ax, cx, cy, cw, ch, title, lines)
        cx += cw + 0.008

    # ---- Hunter 硬件 ----=
    hunter_x = X0 + 0.01 + revo_w + 0.01
    hunter_y = Y1 + 0.008
    hunter_w = W - revo_w - 0.03
    hunter_h = 0.10
    hunter_bg = FancyBboxPatch(
        (hunter_x, hunter_y), hunter_w, hunter_h,
        boxstyle="round,pad=0.005",
        facecolor=hex_to_rgba('#ef4444', 0.08),
        edgecolor=hex_to_rgba('#ef4444', 0.3),
        linewidth=1.0, zorder=2
    )
    ax.add_patch(hunter_bg)
    ax.plot(hunter_x + 0.012, hunter_y + hunter_h - 0.01, 'o', color='#f97316', markersize=6, zorder=3)
    ax.text(hunter_x + 0.02, hunter_y + hunter_h - 0.01, 'Agilex Hunter SE — 移动机器人平台',
            fontsize=9, fontweight='bold', color='#fdba74', va='center', zorder=3)

    cx = hunter_x + 0.02
    cy = hunter_y + 0.005
    hw_cards_hunter = [
        ('底盘控制器', ['CAN总线通信', '阿克曼转向']),
        ('电机编码器', ['后轮驱动', '前轮转向']),
        ('E-Stop 急停', ['安全保障', '遥控器模式']),
    ]
    for title, lines in hw_cards_hunter:
        draw_card(ax, cx, cy, cw, ch, title, lines)
        cx += cw + 0.008

    # ---- 外部传感器 ----=
    sensors_hw = [
        ('📡 RPLIDAR A1', '360° 激光雷达'),
        ('🌍 GPS 天线', 'NMEA 0183'),
        ('📷 Orbbec Astra', 'RGB-D 相机'),
        ('📻 MR20 毫米波', '60GHz FMCW'),
    ]
    total_sw = len(sensors_hw) * (sw + 0.01) - 0.01
    sx = 0.5 - total_sw/2
    sensor_y_hw = Y1 + 0.005
    for name, topic in sensors_hw:
        draw_sensor_chip(ax, sx, sensor_y_hw, sw, 0.04, name, topic)
        sx += sw + 0.01

    # ====== 底部技术栈 ======
    footer_y = 0.04
    ax.text(0.5, footer_y + 0.03, '数据流: 硬件层 ↑ SDK层 ↑ ROS2适配层 ↑ 感知定位层 ↑ 应用层    |    控制流: 应用层 ↓ ROS2适配层 ↓ SDK层 ↓ 硬件层',
            fontsize=8, color=COLORS['text_dim'], ha='center', va='center', zorder=2)

    # 技术栈标签
    tech_tags = [
        ('ROS2 Humble', '#f97316'),
        ('Python/rclpy', '#3b82f6'),
        ('C++/rclcpp', '#0ea5e9'),
        ('robot_localization', '#a78bfa'),
        ('Nav2', '#f97316'),
        ('slam_toolbox', '#f97316'),
        ('YOLOv8/TensorRT', '#84cc16'),
        ('Jetson Orin', '#64748b'),
        ('Git Flow', '#64748b'),
    ]
    tx = 0.5 - (len(tech_tags) * 0.055) / 2
    for text, color in tech_tags:
        tag_rect = FancyBboxPatch(
            (tx, footer_y - 0.005), 0.05, 0.018,
            boxstyle="round,pad=0.003",
            facecolor=hex_to_rgba(color, 0.15),
            edgecolor=hex_to_rgba(color, 0.3),
            linewidth=0.6, zorder=3
        )
        ax.add_patch(tag_rect)
        ax.text(tx + 0.025, footer_y + 0.004, text,
                fontsize=5.5, fontweight='bold', color=color,
                ha='center', va='center', zorder=4)
        tx += 0.055

    # ====== 保存 ======
    output_path = '/home/orin/Workspace/agri_ugv/docs/system_architecture.png'
    fig.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg'], edgecolor='none',
                pad_inches=0.3)
    plt.close()
    print(f'架构图已保存: {output_path}')


if __name__ == '__main__':
    main()
