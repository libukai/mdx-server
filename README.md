# MDX Server

一个功能强大的多词典 MDX/MDD 查询服务器，支持多词典查询、资源文件服务和 Docker 部署。

[![Python Version](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 🚀 快速开始

### 本地开发
1. 克隆仓库: `git clone https://github.com/your-username/mdx-server.git`
2. 安装依赖: `uv venv && source .venv/bin/activate && uv sync`
3. 准备词典: 将 `.mdx` 和 `.mdd` 文件放入 `dict/` 目录
4. 启动服务: `python run_server.py`

### Docker 部署 (推荐)

1. **准备文件**:
   ```bash
   mkdir dict
   # 将 .mdx 和 .mdd 文件放入 dict/ 目录
   ```

2. **创建配置** `config.json`:
   ```json
   {
     "dictionaries": {
       "scene": {
         "name": "场景英语词典",
         "path": "/dict/SceneEnglish.mdx",
         "route": "scene",
         "enabled": true
       },
       "default": {
         "name": "默认词典",
         "path": "/dict/SceneEnglish.mdx",
         "route": "",
         "enabled": true
       }
     }
   }
   ```

3. **启动服务**:
   ```bash
   docker compose up -d
   # 或使用预构建镜像
   docker run -d --name mdx-server -p 8000:8000 \
     -v $(pwd)/dict:/dict -v $(pwd)/config.json:/app/config.json \
     ghcr.io/your-username/mdx-server:latest
   ```

4. **访问测试**: http://localhost:8000/hello

## 📖 API 接口

- `GET /{word}` - 默认词典查询
- `GET /{route}/{word}` - 指定词典查询  
- `GET /api/dicts` - 词典列表
- `GET /health` - 健康检查

## ⚙️ 配置

### 环境变量
支持通过环境变量自定义配置：
- `MDX_HOST` - 服务器地址 (默认: "")
- `MDX_PORT` - 端口 (默认: 8000)
- `MDX_DICT_DIR` - 词典目录 (默认: 自动检测)
- `MDX_LOG_LEVEL` - 日志级别 (默认: INFO)

### 多词典配置示例
```json
{
  "dictionaries": {
    "oxford": {
      "name": "牛津词典",
      "path": "/dict/OALE10.mdx",
      "route": "oxford",
      "enabled": true
    },
    "default": {
      "name": "默认词典", 
      "path": "/dict/default.mdx",
      "route": "",
      "enabled": true
    }
  }
}
```

## 🛠️ 开发

```bash
# 开发环境
uv sync --all-extras

# 代码检查
ruff check . && ruff format .

# 运行测试  
pytest
```

## 📦 发布

创建版本标签自动构建镜像：
```bash
git tag v2.0.0 && git push origin v2.0.0
```

## 📄 许可证

MIT License
