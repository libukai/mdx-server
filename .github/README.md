# GitHub Actions CI/CD 配置

本项目使用 GitHub Actions 自动构建和发布 Docker 镜像。

## 🚀 工作流说明

### 1. 测试工作流 (`test.yml`)
- **触发条件**: 每次 push 和 PR
- **功能**: 代码检查、类型检查、测试、Docker 构建验证
- **状态**: 自动运行，无需配置

### 2. Docker 构建工作流 (`docker.yml`)
- **触发条件**: 创建版本标签 (如 `v2.0.0`) 或手动触发
- **功能**: 构建多平台 Docker 镜像并发布到 GitHub Container Registry  
- **发布位置**: `ghcr.io/your-username/mdx-server`

### 3. 发布工作流 (`release.yml`)
- **触发条件**: 创建版本标签 (如 `v2.0.0`)
- **功能**: 创建 GitHub Release，包含源码归档和使用说明

## ⚙️ 配置步骤

### 1. GitHub Container Registry (GHCR)
✅ **无需额外配置** - 使用 `GITHUB_TOKEN` 自动授权，完全免费！

### 2. 权限配置
确保仓库具有以下权限：
1. Settings → Actions → General → Workflow permissions
2. 选择 "Read and write permissions"
3. 勾选 "Allow GitHub Actions to create and approve pull requests"

## 📦 使用方式

### 自动构建
- **创建版本标签**: 构建版本标签 + `latest`
- **创建 PR**: 构建测试镜像（不发布）
- **手动触发**: Actions 页面手动启动构建

### 手动发布
1. 创建版本标签：
   ```bash
   git tag v2.0.0
   git push origin v2.0.0
   ```

2. GitHub Actions 自动：
   - 构建多平台镜像
   - 发布到 GHCR 和 Docker Hub
   - 创建 GitHub Release

### 镜像使用
```bash
# GitHub Container Registry
docker pull ghcr.io/your-username/mdx-server:latest
docker pull ghcr.io/your-username/mdx-server:v2.0.0
```

## 🔧 支持的平台
- `linux/amd64` (x86_64) - Intel/AMD 64位
- `linux/arm64` (aarch64) - ARM 64位 (Apple M1/M2, Raspberry Pi 4+)

## 📋 标签策略
- `latest` - 最新稳定版本
- `v2.0.0` - 具体版本号
- `v2.0` - 主要和次要版本
- `v2` - 主要版本
- `master` - 开发分支构建

## 🐛 故障排除

### 构建失败
1. 检查 Dockerfile 语法
2. 确保所有文件都存在
3. 查看 Actions 日志

### 发布失败
1. 检查 GitHub 权限设置
2. 确保仓库名称正确
3. 验证 GITHUB_TOKEN 权限

### 权限问题
1. 确保 GITHUB_TOKEN 有足够权限
2. 检查仓库 Actions 权限设置
3. 验证 Secrets 配置正确