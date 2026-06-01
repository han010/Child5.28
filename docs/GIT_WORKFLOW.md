# Git Flow 分支管理指南

## 分支结构

```
main              # 主分支，稳定版本（生产环境）
├── develop       # 开发分支（默认分支，日常开发）
├── feature/*     # 功能分支，从 develop 创建
├── hotfix/*      # 紧急修复分支，从 main 创建
└── release/*     # 发布分支，从 develop 创建
```

## 当前状态

- **main**: 稳定版本分支
- **develop**: 开发分支（当前所在分支，默认开发分支）

---

## 分支说明

### 1. main（主分支）
- **用途**: 生产环境稳定版本
- **保护**: 只接受来自 release 或 hotfix 的合并
- **提交**: 禁止直接提交，必须通过 PR/merge

### 2. develop（开发分支）
- **用途**: 日常开发的主分支
- **默认**: 新开发从此分支开始
- **合并**: 接受来自 feature 分支的合并

### 3. feature/*（功能分支）
- **命名**: `feature/功能名称`
- **来源**: 从 `develop` 创建
- **合并**: 完成后合并回 `develop`
- **示例**: `feature/revo-navigation`, `feature/hunter-speed-control`

### 4. hotfix/*（紧急修复分支）
- **命名**: `hotfix/问题描述`
- **来源**: 从 `main` 创建
- **合并**: 修复后同时合并到 `main` 和 `develop`
- **示例**: `hotfix/fix-cmdvel-crash`, `hotfix/urgent-gps-fix`

### 5. release/*（发布分支）
- **命名**: `release/v版本号`
- **来源**: 从 `develop` 创建
- **合并**: 测试通过后合并到 `main` 和 `develop`
- **示例**: `release/v1.0.0`, `release/v1.1.0`

---

## 日常开发流程

### 场景1: 开发新功能

```bash
# 1. 确保在 develop 分支且是最新的
git checkout develop
git pull origin develop  # 如果有远程仓库

# 2. 创建功能分支
git checkout -b feature/功能名称

# 3. 开发代码并提交
git add .
git commit -m "feat: 添加XXX功能"

# 4. 开发完成后合并回 develop
git checkout develop
git merge feature/功能名称

# 5. 删除功能分支（可选）
git branch -d feature/功能名称
```

**示例 - 开发 Revo 导航功能**:
```bash
git checkout develop
git checkout -b feature/revo-navigation

# ... 编写代码 ...
git add .
git commit -m "feat: 添加Revo自主导航功能

- 实现Nav2集成
- 添加路径规划接口
- 配置导航参数"

# 完成后合并
git checkout develop
git merge --no-ff feature/revo-navigation  # 保留分支历史
git branch -d feature/revo-navigation
```

### 场景2: 修复紧急Bug

```bash
# 1. 从 main 创建 hotfix 分支
git checkout main
git checkout -b hotfix/问题描述

# 2. 修复并提交
git add .
git commit -m "fix: 修复XXX紧急问题"

# 3. 合并到 main
git checkout main
git merge --no-ff hotfix/问题描述

# 4. 合并到 develop（避免bug重复）
git checkout develop
git merge --no-ff hotfix/问题描述

# 5. 打标签
git tag -a v1.0.1 -m "Hotfix: 修复XXX问题"

# 6. 删除 hotfix 分支
git branch -d hotfix/问题描述
```

### 场景3: 准备发布版本

```bash
# 1. 从 develop 创建 release 分支
git checkout develop
git checkout -b release/v1.0.0

# 2. 在此分支进行最后的测试、修复、版本号更新
git add .
git commit -m "chore: 更新版本号到 v1.0.0"

# 3. 合并到 main
git checkout main
git merge --no-ff release/v1.0.0

# 4. 打上版本标签
git tag -a v1.0.0 -m "Release version 1.0.0

主要功能:
- XAG Revo机器人控制
- Hunter SE机器人控制
- SLAM建图和导航
- GPS航点导航"

# 5. 合并回 develop（包含 release 分支的修改）
git checkout develop
git merge --no-ff release/v1.0.0

# 6. 删除 release 分支
git branch -d release/v1.0.0
```

---

## 分支切换命令

### 查看分支
```bash
# 查看所有本地分支
git branch

# 查看所有分支（包括远程）
git branch -a

# 查看当前所在分支
git branch --show-current
```

### 创建和切换分支
```bash
# 创建新分支（不切换）
git branch 分支名

# 创建并切换到新分支
git checkout -b 分支名

# 切换到已有分支
git checkout 分支名

# 或使用新语法（推荐）
git switch 分支名
git switch -c 新分支名  # 创建并切换
```

### 删除分支
```bash
# 删除已合并的分支
git branch -d 分支名

# 强制删除未合并的分支
git branch -D 分支名
```

---

## 实用技巧

### 1. 暂存当前工作
```bash
# 当你需要切换分支但还有未提交的修改时
git stash
git checkout develop
git stash pop  # 恢复暂存的修改
```

### 2. 查看分支差异
```bash
# 查看当前分支与 develop 的差异
git diff develop

# 查看两个分支之间的差异
git diff main develop
```

### 3. 查看分支历史图
```bash
# 图形化显示分支历史
git log --graph --oneline --all --decorate

# 或使用更简洁的版本
git log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit
```

### 4. 保留分支历史
使用 `--no-ff` 参数合并，可以保留功能分支的历史：
```bash
git merge --no-ff feature/xxx
```

---

## 提交信息规范

使用以下前缀标记提交类型：
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具链相关

---

## 常见工作场景

### 开发 Revo 相关功能
```bash
git checkout develop
git checkout -b feature/revo-xxx
# ... 开发 ...
git checkout develop
git merge --no-ff feature/revo-xxx
```

### 开发 Hunter 相关功能
```bash
git checkout develop
git checkout -b feature/hunter-xxx
# ... 开发 ...
git checkout develop
git merge --no-ff feature/hunter-xxx
```

### 修改项目文档
```bash
git checkout develop
git checkout -b feature/update-docs
# ... 修改文档 ...
git checkout develop
git merge feature/update-docs
```

---

## 当前项目分支管理

### 主要分支
- `main` - 稳定发布版本
- `develop` - 当前开发分支（默认）

### 推荐的功能分支命名
- `feature/revo-nav` - Revo导航功能
- `feature/hunter-control` - Hunter控制功能
- `feature/slam-mapping` - SLAM建图功能
- `feature/sensor-fusion` - 传感器融合
- `feature/auto-docking` - 自动回充功能

### 快速开始新开发
```bash
# 1. 确保在 develop
git checkout develop

# 2. 创建功能分支
git checkout -b feature/你的功能名

# 3. 开发并提交
git add .
git commit -m "描述你的修改"

# 4. 完成后合并回 develop
git checkout develop
git merge --no-ff feature/你的功能名

# 5. 清理
git branch -d feature/你的功能名
```

---

## 注意事项

1. **永远不要直接在 main 分支开发**
2. **feature 分支从 develop 创建，完成后合并回 develop**
3. **hotfix 分支从 main 创建，完成后合并到 main 和 develop**
4. **使用 `--no-ff` 合并保留分支历史**
5. **定期合并 develop 到 feature 分支，避免冲突**
6. **提交前先 `pull` 或 `rebase` 保持最新**

---

## 备份提醒

由于使用本地Git仓库，建议定期备份：

```bash
# 备份整个仓库（包括所有分支）
tar -czf agri_ugv_git_backup_$(date +%Y%m%d).tar.gz .git

# 或备份完整项目
tar -czf agri_ugv_backup_$(date +%Y%m%d).tar.gz \
    --exclude='ros2_ws/build' \
    --exclude='ros2_ws/install' \
    --exclude='ros2_ws/log' \
    /home/orin/Workspace/agri_ugv
```
