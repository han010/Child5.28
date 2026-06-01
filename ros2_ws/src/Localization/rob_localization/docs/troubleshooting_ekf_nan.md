# EKF NaN 问题排错记录

> 日期：2026-04-20
> 环境：ROS2 Humble, robot_localization 3.5.4 (arm64), Jetson Orin

## 现象

启动 `ekf_indoor.launch.py` 后，`ekf_filter_node` 立刻输出大量 NaN 错误：

```
[ERROR] [ekf_filter_node]: Critical Error, NaNs were detected in the output state of the filter.
        This was likely due to poorly conditioned process, noise, or sensor covariances.
Error:   TF_NAN_INPUT: Ignoring transform for child_frame_id "base_link" because of a nan value
```

`/odometry/filtered` 话题输出全为 `.nan`，`odom→base_link` TF 变换也包含 NaN。

## 排查过程

### 1. 排除传感器数据问题

检查了 `/odom` 和 `/revo/imu` 话题数据：
- 所有字段均为有效数值，无 NaN/Inf
- 四元数范数为 1.0
- 协方差矩阵均为正定对角矩阵
- 时间戳与 ROS 时钟偏差仅 0.002 秒

### 2. 排除 initial_estimate_covariance 数值问题

原始配置使用 15 个对角线值 `1e-9`，尝试改为 `1.0` 等更大值，NaN 仍然出现。
**结论：不是协方差数值过小导致的问题。**

### 3. 隔离传感器源

| 测试场景 | 话题 | 结果 |
|---------|------|------|
| 仅 odom（无 IMU）+ 真实数据 | `/odom` | NaN |
| 假数据（`ros2 topic pub`） | `/test/odom` | **正常** |
| 真实数据中继 + 时间戳=0 | `/test/odom_ts0` | **正常** |
| 真实数据中继 + 原始时间戳 | relay | NaN |

**关键发现**：时间戳为 0 时正常，非零时间戳时 NaN。这说明 EKF 在"预测步骤"（predict）中出错——时间戳为 0 时，`last_measurement_time_` 始终为 0，EKF 内部跳过预测只做校正，因此绕过了 bug。

### 4. 启用 Debug 模式定位根因

在 `ekf_indoor.yaml` 中设置 `debug: true`，分析 `/tmp/ekf_debug_output.txt`：

```
Initial estimate error covariance is:    ← 配置值（15 个对角线元素）
(1  1  1e-09  1e-09  1e-09  1  1  1e-09  ...)

Current estimate error covariance is:    ← 实际矩阵（15×15）
[1           1           1e-09  ...     ← 第 0 行：15 个对角线值全被放入此行！
 5.5829e-322 4.9407e-324  ...          ← 第 1 行：未初始化内存垃圾
 2.1953e-152 6.5202e+252  ...          ← 第 2 行：巨大垃圾值
 ...]
```

## 根因

**robot_localization 3.5.4 的 YAML 参数解析 bug。**

当 `initial_estimate_covariance` 仅提供 15 个值（期望作为对角线）时：

```yaml
# 15 个值 → 被错误解析为矩阵第一行
initial_estimate_covariance: [1.0, 1.0, 1e-9, 1e-9, 1e-9, 1.0, 1.0, ...]
```

这 15 个值被放入 15×15 矩阵的**第一行**（位置 [0,0]~[0,14]），而非对角线（位置 [0,0], [1,1], ..., [14,14]）。矩阵的其余 14 行保持**未初始化的内存垃圾**。

预测步骤执行 `P_pred = F·P·F^T + Q` 时，垃圾值在矩阵乘法中指数爆炸（如 `6.52e+252`），导致 Kalman 增益中出现 `1.86e+187` 等天文数字，最终在第一次校正步骤后产生 NaN。

## 修复方案

提供完整的 **15×15 = 225 元素** 矩阵，而非仅 15 个对角线值：

```yaml
# 正确：225 元素完整矩阵
initial_estimate_covariance: [1.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,
                              0.0,  1.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,
                              0.0,  0.0,  1e-9, 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,
                              ...（共 15 行，每行 15 个元素）]
```

修改文件：`params/ekf_indoor.yaml`

## 验证结果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| NaN 错误数 | 持续（20Hz） | **0** |
| `/odometry/filtered` | 全 NaN | 有效位姿/速度 |
| `odom→base_link` TF | NaN 四元数 | 正常变换 |

## 注意事项

1. **`process_noise_covariance`** 使用 225 元素格式则无此问题（已正常工作）。
2. 仅 `initial_estimate_covariance` 以 15 元素格式提供时会触发此 bug。
3. 该 bug 存在于 `robot_localization` 3.5.4（Humble arm64），其他版本未验证。
4. 官方示例和文档中多处使用 15 元素格式，在此版本上均会触发此问题。

## 相关文件

- 配置文件：`params/ekf_indoor.yaml`
- 参考配置：`params/ekf_reference.yaml`
- Launch 文件：`launch/ekf_indoor.launch.py`
