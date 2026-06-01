#!/usr/bin/env python3
"""
测试 SDK altitude 数据
"""
import sys
import time
from xa_revosdk_ugv import RevoSDK

def main():
    host = "192.168.234.1"
    client_name = "AltitudeTest"

    sdk = RevoSDK()

    print(f"正在连接到: {host}:10151")
    if not sdk.connect(host):
        print("连接失败!")
        return 1
    print("连接成功!")

    if not sdk.register(client_name):
        print("注册失败!")
        return 1
    print(f"注册成功!")

    # 位姿数据回调
    def on_pose_data(data):
        print(f"\n========== Altitude 测试 ==========")
        print(f"longitude: {data.get_longitude_degrees()}")
        print(f"latitude:  {data.get_latitude_degrees()}")
        print(f"altitude:  {data.get_altitude_meters()} 米")
        print(f"roll:      {data.get_roll_rad()} rad")
        print(f"pitch:     {data.get_pitch_rad()} rad")
        print(f"yaw:       {data.get_yaw_rad()} rad")
        print(f"==================================\n")

    # 订阅位姿数据
    sdk.subscribe_pose(True, on_pose_data)

    print("正在接收数据（按 Ctrl+C 退出）...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n退出测试")
    finally:
        sdk.subscribe_pose(False)
        sdk.unregister()
        sdk.disconnect()

    return 0

if __name__ == '__main__':
    sys.exit(main())
