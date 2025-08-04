# MDX Server

一个功能强大的多词典 MDX/MDD 查询服务器,基于 Python 实现。

[![Python Version](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## ✨ 功能特性

- **多词典支持**: 同时加载和查询多个 MDX/MDD 词典。
- **动态词典加载**: 无需重启服务器即可添加或删除词典。
- **自动发现**: 自动扫描并加载指定目录下的词典文件。
- **RESTful API**: 提供清晰的 API 用于词典查询和管理。
- **资源文件服务**: 高效提供 MDD 文件中的资源 (CSS, JS, 图片, 音频等)。
- **灵活配置**: 支持通过 `config.json` 文件或环境变量进行配置。
- **高性能**: 支持 Gunicorn 进行生产环境部署,也内置了多线程服务器。
- **Docker 支持**: 提供 `Dockerfile` 和 `docker-compose.yml` 用于快速容器化部署。
- **健康检查**: 提供 `/health` 端点用于监控服务状态。

## 🚀 快速开始

### 环境准备

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (推荐的包管理器)

### 安装

1.  克隆本仓库:
    ```bash
    git clone https://github.com/your-username/mdx-server.git
    cd mdx-server
    ```

2.  创建虚拟环境并安装依赖:
    ```bash
    uv venv
    source .venv/bin/activate
    uv sync
    ```

### 运行

1.  **准备词典文件**:
    将你的 `.mdx` 和 `.mdd` 文件放入 `dict/` 目录下。

2.  **启动服务器**:
    ```bash
    python run_server.py
    ```

    服务器默认运行在 `http://localhost:8000`。

## 🐳 Docker 部署

项目提供了优化的 Docker 配置，实现**零配置启动**，用户体验极佳。

### 🚀 一键启动

1.  **准备词典文件**:
    ```bash
    mkdir dict
    # 将你的 .mdx 和 .mdd 文件放入 dict/ 目录
    ```

2.  **创建词典配置** `config.json`:
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

3.  **一键启动**:
    ```bash
    docker compose up -d
    ```

4.  **访问验证**:
    - 🌐 http://localhost:8000/scene/hello - 通过路由访问词典
    - 🌐 http://localhost:8000/hello - 默认词典
    - 📋 http://localhost:8000/api/dicts - 词典列表API

### ✨ 优化特性

- **🎯 智能路径检测**: 自动检测 Docker 环境，无需手动配置词典目录
- **📁 清晰的文件映射**: 
  - `./dict` → `/dict` (词典文件)
  - `./config.json` → `/app/config.json` (配置文件)
  - `./logs` → `/app/logs` (日志文件)
- **⚙️ 零环境变量**: 所有参数都有合理默认值
- **🔧 配置分离**: 业务配置在 config.json，环境配置在 docker-compose.yml

### 🔧 高级配置

如需自定义服务器参数，可在 `docker-compose.yml` 中添加环境变量：

```yaml
services:
  mdx-server:
    # ... 其他配置
    environment:
      # 服务器配置
      MDX_HOST: "0.0.0.0"         # 默认: ""
      MDX_PORT: 8080              # 默认: 8000  
      MDX_DEBUG: true             # 默认: false
      
      # 目录配置
      MDX_DICT_DIR: "/dict"       # 默认: 自动检测
      MDX_RESOURCE_DIR: "mdx"     # 默认: mdx
      
      # 性能配置
      MDX_CACHE_ENABLED: false    # 默认: true
      MDX_MAX_WORD_LENGTH: 200    # 默认: 100
      MDX_MAX_THREADS: 10         # 默认: 20
      MDX_REQUEST_QUEUE_SIZE: 100 # 默认: 50
      MDX_CONNECTION_TIMEOUT: 60  # 默认: 30
      
      # 日志配置
      MDX_LOG_LEVEL: "DEBUG"      # 默认: INFO
      
      # 生产环境配置 (Gunicorn)
      MDX_SERVER_TYPE: "gunicorn" # 默认: threaded
      MDX_USE_GUNICORN: true      # 默认: false
      MDX_GUNICORN_WORKERS: 8     # 默认: 4
      MDX_GUNICORN_THREADS: 2     # 默认: 5
```

### 📋 多词典配置示例

```json
{
  "dictionaries": {
    "oxford": {
      "name": "牛津高阶英汉双解词典",
      "path": "/dict/OALE10.mdx",
      "route": "oxford",
      "enabled": true
    },
    "cambridge": {
      "name": "剑桥高级学习词典",
      "path": "/dict/Cambridge.mdx",
      "route": "cambridge", 
      "enabled": true
    },
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

**访问方式**:
- `/oxford/hello` - 牛津词典
- `/cambridge/hello` - 剑桥词典  
- `/scene/hello` - 场景词典
- `/hello` - 默认词典

## ⚙️ 配置

服务器可以通过 `config.json` 文件或环境变量进行配置。

### 配置文件

在项目根目录下创建一个 `config.json` 文件。如果文件不存在,服务器会使用默认配置并自动发现 `dict` 目录下的词典。

这是一个配置示例:

```json
{
  "host": "0.0.0.0",
  "port": 8000,
  "debug": false,
  "dict_directory": "dict",
  "server_type": "threaded",
  "dictionaries": {
    "oale10": {
      "name": "Oxford Advanced Learner's English-Chinese Dictionary 10",
      "path": "dict/OALE10.mdx",
      "route": "oale10",
      "enabled": true
    },
    "default": {
      "name": "Default Dictionary",
      "path": "dict/default.mdx",
      "route": "",
      "enabled": true
    }
  }
}
```

### 环境变量

你也可以使用环境变量来覆盖 `config.json` 中的设置。

- `MDX_HOST`: 服务器主机名 (默认: `""`)
- `MDX_PORT`: 服务器端口 (默认: `8000`)
- `MDX_DEBUG`: 是否开启调试模式 (默认: `false`)
- `MDX_DICT_DIR`: 词典目录 (默认: `dict`)
- `MDX_LOG_LEVEL`: 日志级别 (默认: `INFO`)

## 📖 API 端点

- **GET /api/dicts** 或 **GET /api/dictionaries**: 获取加载的词典列表。
  ```json
  {
    "dictionaries": [
      {
        "id": "oale10",
        "name": "Oxford Advanced Learner's English-Chinese Dictionary 10",
        "route": "oale10",
        "enabled": true
      }
    ],
    "mode": "multi",
    "total": 1
  }
  ```

- **GET /{word}**: 在默认词典中查询单词。

- **GET /{dict_route}/{word}**: 在指定路由的词典中查询单词。

- **GET /{resource_path}**: 获取 MDD 中的资源文件 (例如 `style.css`, `jquery.js`)。

- **GET /health**: 健康检查端点。

## 🛠️ 开发

### 安装开发依赖

```bash
uv sync --all-extras
```

### 代码风格检查和格式化

本项目使用 `ruff` 进行代码检查和格式化。

```bash
# 格式化代码
ruff format .

# 检查代码
ruff check .
```

### 运行测试

```bash
pytest
```

## 📄 许可证

本项目基于 MIT 许可证。
