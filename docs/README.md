# 农业UGV项目文档中心

> 欢迎来到农业无人车(UGV)项目文档中心！这里包含了团队介绍、开发指南和新人入门的全部必要信息。

## 📚 文档列表

### 🏢 [团队介绍](./团队介绍.md)
- 团队概况和技术实力
- 核心技术栈和创新点
- 项目经验和团队文化
- 联系方式和技术资源

### 🎯 [团队目标](./团队目标.md)
- 愿景与使命
- 短期、中期、长期发展目标
- 技术发展路线图
- 关键成功指标(KPI)

### 🚀 [新人入门指南](./新人入门指南.md)
- 项目概览和技术栈介绍
- 环境搭建和快速上手
- 开发流程和Git工作流
- 学习资源和常见问题

## 📋 项目概览

### 项目简介
这是一个基于ROS2的农业无人车项目，成功集成了两种不同技术特点的机器人平台：

1. **XAG Revo R100/R200** - 专业农业机器人平台（UDP控制）
2. **Agilex Hunter SE** - 通用移动机器人平台（CAN总线控制）

### 核心功能
- ✅ 统一的ROS2控制接口
- ✅ 高精度自主导航系统
- ✅ 多传感器集成（激光雷达、GNSS、视觉等）
- ✅ SLAM建图和路径规划
- ✅ 农业作业任务规划

### 技术特点
- 🚀 双平台统一控制架构
- 🚀 实时控制系统（50Hz控制频率）
- 🚀 适应性导航算法
- 🚀 模块化系统设计

## 🛠️ 快速开始

### 环境要求
- Ubuntu 20.04/22.04
- ROS2 Humble
- 16GB RAM
- 500GB SSD

### 安装步骤
```bash
# 1. 克隆项目
git clone https://github.com/your-team/agri_ugv.git
cd agri_ugv

# 2. 编译ROS2工作空间
cd ros2_ws
colcon build --symlink-install

# 3. 加载环境变量
source install/setup.bash
echo "source install/setup.bash" >> ~/.bashrc
```

### 启动机器人
```bash
# 启动Hunter SE
ros2 launch hunter_base hunter_base.launch.py

# 启动XAG Revo
ros2 launch revo_ugv_ros2 revo_bringup.launch.py

# 启动导航系统
ros2 launch revo_ugv_ros2 revo_navigation.launch.py
```

## 📖 文档导航

### 🔰 新手必读
- [新人入门指南](./新人入门.md) - 从零开始的完整指南
- [CLAUDE.md](../CLAUDE.md) - 项目开发指南
- [团队介绍](./团队介绍.md) - 了解团队和项目背景

### 💻 开发者指南
- [团队目标](./团队目标.md) - 了解项目发展方向
- [Git工作流](./新人入门指南.md#开发流程) - 代码提交规范
- [测试规范](./新人入门指南.md#测试流程) - 测试要求和流程

### 🔧 技术文档
- [ROS2 Navigation Tutorials](https://navigation.ros.org/tutorials/docs/index.html)
- [ROS2 Official Documentation](https://docs.ros.org/)
- [Foxglove Studio](https://foxglove.dev/) - 调试工具

## 🎯 学习路径

### 阶段一：基础入门（1-2周）
- [ ] 学习ROS2基础概念
- [ ] 搭建开发环境
- [ ] 运行第一个机器人
- [ ] 理解项目架构

### 阶段二：深入学习（3-4周）
- [ ] 掌握导航系统原理
- [ ] 学习传感器集成方法
- [ ] 理解控制算法
- [ ] 参与代码阅读

### 阶段三：实践项目（5-8周）
- [ ] 修复一个bug
- [ ] 添加新功能
- [ ] 编写单元测试
- [ ] 提交第一个PR

### 阶段四：独立开发（9周+）
- [ ] 负责一个模块
- [ ] 参与系统设计
- [ ] 技术分享
- [ ] 贡献开源项目

## 🤝 参与贡献

### 报告问题
- 使用 [GitHub Issues](https://github.com/your-team/agri_ugv/issues) 报告bug
- 提供详细的复现步骤和环境信息

### 提交代码
1. Fork 项目
2. 创建功能分支
3. 提交代码更改
4. 创建 Pull Request
5. 等待代码评审

### 改进文档
- 修正错误信息
- 添加缺失的文档
- 改进文档结构和可读性
- 翻译文档到其他语言

## 📞 联系方式

### 团队成员
- **项目负责人**：张三 - zhangsan@team.com
- **技术主管**：李四 - lisi@team.com
- **ROS2专家**：王五 - wangwu@team.com

### 社区交流
- **技术论坛**：[Agri Robot Forum](https://forum.agri-robot.org)
- **QQ群**：农业机器人技术交流群
- **微信群**：项目内部沟通群

### 技术支持
- **GitHub**：[项目仓库](https://github.com/your-team/agri_ugv)
- **文档**：[在线文档](https://docs.agri-robot.org)
- **API文档**：[Swagger UI](https://api.agri-robot.org)

## 🗂️ 相关资源

### 开源项目
- [ROS2](https://github.com/ros2)
- [Nav2](https://github.com/ros-planning/navigation2)
- [Cartographer](https://github.com/googlecartographer/cartographer)
- [RPLIDAR](https://github.com/Slamtec/rplidar_ros)

### 学习资源
- [ROS2 Tutorials](https://docs.ros.org/en/humble/Tutorials.html)
- [ROS2 Navigation](https://navigation.ros.org/)
- [Foxglove Studio](https://foxglove.dev/studio)

### 工具链
- [VS Code + ROS](https://marketplace.visualstudio.com/items?itemName=ms-iot.vscode-ros)
- [Git + GitHub](https://desktop.github.com/)
- [Docker](https://www.docker.com/)

## 📈 项目统计

- ⭐ Stars: [GitHub Stars数量]
- 🐛 Issues: [开放issues数量]
- 📝 Pull Requests: [PR数量]
- 👥 Contributors: [贡献者数量]
- 📦 版本: v1.0.0

## 🔄 更新日志

### v1.0.0 (2024-01)
- 🎉 初始版本发布
- ✅ 完成基础功能开发
- 📚 完善文档体系
- 👨‍💻 组建核心团队

### v0.9.0 (2023-12)
- 🔧 完善导航系统
- 📦 发布测试版本
- 📝 开始编写文档

### v0.8.0 (2023-11)
- ✅ 双平台控制实现
- 🎯 SLAM建图功能
- 🔌 传感器集成

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 🙏 致谢

感谢以下开源项目的支持：
- ROS2团队
- Nav2团队
- Cartographer团队
- RPLIDAR团队
- 以及所有贡献者的付出！

---

**最后更新**：2024年1月
**维护者**：农业机器人团队
**文档版本**：v1.0.0