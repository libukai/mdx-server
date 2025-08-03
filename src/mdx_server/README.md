## MDX Server

MDX Server is a modern, high-performance service for reading MDX/MDD dictionary data and providing standard HTTP interfaces to external tools. 

**✨ New Multi-Dictionary Features:**
- 🔀 **Multi-Dictionary Support**: Query multiple dictionaries with different routes
- 🚀 **Auto-Discovery**: Automatically detects and loads MDX files from directory
- 📱 **RESTful API**: Modern API endpoints for dictionary management and health checks
- 🔄 **Backward Compatible**: Existing single-dictionary setups continue to work seamlessly
- ⚡ **Smart Routing**: Route-based dictionary selection for organized access
- 📊 **Status Monitoring**: Real-time dictionary status and health monitoring

Built upon [mdict-query](https://github.com/mmjang/mdict-query) and [PythonDictionaryOnline](https://github.com/amazon200code/PythonDictionaryOnline) with modern Python 3.13+ enhancements.

## Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and includes ruff for linting/formatting.

### Installation

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Code Quality

```bash
# Run linting and formatting
uv run ruff check .
uv run ruff format .

# Run type checking
uv run ty .
```

## Usage

### Quick Start

1. Place your MDX dictionary files in the `src/mdx_server/dict/` directory
2. Run the server:
   ```bash
   cd src/mdx_server
   python3 mdx_server.py
   ```
3. Open your browser and test:
   - **Single dictionary**: `http://localhost:8000/{word}`
   - **Multi-dictionary**: `http://localhost:8000/{dict_route}/{word}`
   - **API endpoints**: `http://localhost:8000/api/dicts`

### Multi-Dictionary Configuration

Create a `config.json` file to define multiple dictionaries:

```json
{
  "host": "",
  "port": 8000,
  "debug": false,
  "dict_directory": "dict",
  "dictionaries": {
    "default": {
      "name": "Default Dictionary",
      "path": "dict/default.mdx",
      "route": "",
      "enabled": true
    },
    "oxford": {
      "name": "Oxford Dictionary", 
      "path": "dict/oxford.mdx",
      "route": "oxford",
      "enabled": true
    },
    "collins": {
      "name": "Collins Dictionary",
      "path": "dict/collins.mdx",
      "route": "collins", 
      "enabled": true
    }
  }
}
```

### API Routes

| Route | Description | Example | Response |
|-------|-------------|---------|----------|
| `GET /{word}` | Query default dictionary | `/hello` | HTML definition |
| `GET /{route}/{word}` | Query specific dictionary | `/oxford/hello` | HTML definition |
| `GET /api/dicts` | List all dictionaries | `/api/dicts` | JSON dictionary list |
| `GET /health` | Health check | `/health` | JSON health status |

### Multi-Dictionary Usage Examples

```bash
# Query default dictionary
curl http://localhost:8000/hello

# Query specific dictionaries  
curl http://localhost:8000/oxford/hello
curl http://localhost:8000/collins/pronunciation

# Get dictionary information
curl http://localhost:8000/api/dicts
# Returns:
# {
#   "dictionaries": [
#     {
#       "id": "oxford",
#       "name": "Oxford Dictionary", 
#       "route": "oxford",
#       "path": "dict/oxford.mdx",
#       "enabled": true,
#       "status": "loaded"
#     }
#   ],
#   "mode": "multi",
#   "total": 1
# }

# Health check
curl http://localhost:8000/health
# Returns: {"status": "healthy", "mode": "multi", "dictionaries": 2}
```

### Environment Variables

Override configuration with environment variables:

```bash
# Basic settings
export MDX_PORT=8001
export MDX_DEBUG=true
export MDX_DICT_DIR=my_dicts

# Run server
python3 mdx_server.py
```

### Auto-Discovery Mode

If no `dictionaries` configuration is provided, the server will automatically discover all `.mdx` files in the dictionary directory:

```bash
# Place MDX files in dict/ directory
dict/
├── oxford.mdx          # Route: /oxford/{word}
├── collins.mdx         # Route: /collins/{word}  
├── default.mdx         # Route: /{word} (default)
└── etymology.mdx       # Route: /etymology/{word}

# Start server - auto-discovers all dictionaries
python3 mdx_server.py
```

### Docker Usage

```bash
# Using docker-compose (recommended)
docker-compose up

# Or build and run manually
docker build -t mdx-server .
docker run -p 8000:8000 -v /path/to/your/dictionaries:/app/src/mdx_server/dict mdx-server
```

Please check with the [manual](<./src/mdx_server/manual/mdx-server manual.pdf>) for more detail and screenshot



## Upgrade Guide

### From Single Dictionary to Multi-Dictionary

Existing users can upgrade seamlessly:

1. **Keep existing setup** - Single dictionary mode continues to work
2. **Add new dictionaries** - Place additional `.mdx` files in `dict/` directory  
3. **Optional configuration** - Create `config.json` for custom routes and names

### Migration Example

**Before (v1.x):**
```bash
dict/
└── my_dictionary.mdx    # Accessible via /{word}
```

**After (v2.x):**
```bash
dict/
├── my_dictionary.mdx    # Still accessible via /{word} (backward compatible)
├── oxford.mdx           # New: accessible via /oxford/{word}
└── collins.mdx          # New: accessible via /collins/{word}
```

No configuration changes required - the server automatically detects the upgrade scenario.

---

## MDX Server 使用说明 (中文)

### 🆕 多词典支持功能

MDX Server 现已支持多词典功能！通过读取多个 MDX、MDD 格式的词典文件，为外部工具提供更丰富的词典服务。

**新增特性：**
- 🔀 **多词典支持**: 同时加载多个词典，通过不同路由访问
- 🚀 **自动发现**: 自动检测并加载词典目录中的所有 MDX 文件
- 📱 **RESTful API**: 提供现代化的 API 接口管理词典
- 🔄 **向后兼容**: 现有单词典配置无需修改即可继续使用

### 快速开始

1. **将 MDX 词典文件**放入 `src/mdx_server/dict/` 目录
2. **运行服务器**：
   ```bash
   cd src/mdx_server
   python3 mdx_server.py
   ```
3. **访问词典**：
   - 默认词典: `http://localhost:8000/hello`
   - 指定词典: `http://localhost:8000/oxford/hello`
   - 词典列表: `http://localhost:8000/api/dicts`

### 多词典配置示例

创建 `config.json` 文件自定义词典：

```json
{
  "dictionaries": {
    "牛津": {
      "name": "牛津高阶英汉双解词典",
      "path": "dict/oxford.mdx",
      "route": "oxford",
      "enabled": true
    },
    "柯林斯": {
      "name": "柯林斯英汉词典", 
      "path": "dict/collins.mdx",
      "route": "collins",
      "enabled": true
    }
  }
}
```

### API 使用示例

```bash
# 查询牛津词典
curl http://localhost:8000/oxford/hello

# 查询柯林斯词典
curl http://localhost:8000/collins/hello

# 获取词典列表
curl http://localhost:8000/api/dicts

# 健康检查
curl http://localhost:8000/health
```

更多内容和屏幕截图，请查阅[手册](<./manual/mdx-server manual.pdf>)

