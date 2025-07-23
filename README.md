## MDX Server

MDX Server is a service used to read MDX/MDD dictionary data and provide a standard HTTP interface to external tools.

It is just a combination of [mdict-query](https://github.com/mmjang/mdict-query) and [PythonDictionaryOnline](https://github.com/amazon200code/PythonDictionaryOnline).

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
3. Open your browser and visit `http://localhost:8000/{word}` where `{word}` is the English word you want to query

### Configuration

The server can be configured via:

1. **Configuration file** (`src/mdx_server/config.json`):
   ```json
   {
     "host": "",
     "port": 8000,
     "debug": true,
     "dict_directory": "dict",
     "resource_directory": "mdx",
     "cache_enabled": true,
     "max_word_length": 100,
     "log_level": "INFO"
   }
   ```

2. **Environment variables**:
   ```bash
   MDX_PORT=8001 MDX_DEBUG=true python3 mdx_server.py
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



## MDX Server 使用说明

目前流行的 MDX 词典文件只能在 Mdict, GoldenDict, 欧路，深蓝等词典软件中使用，而不能将内容对外输出。MDX Server 通过读取 MDX、MDD 格式的词典文件，对外部提供一个标准的 HTTP 服务接口。使得一些需要词典服务的软件，比如 Kindlemate，Anki 划词助手以及其他工具可以利用这个本地服务，灵活选取所需的 MDX 词典，批量或者单独获取单词的解释。

1. 在 python 3.8+ 环境下运行`mdx_server.py`，弹窗内选择本地 mdx 文件，console 窗口内显示`port:8000` 表明服务器运行成功，等待外部请求。
2. 在浏览器地址栏输入 http://localhost:8000/{word}，其中{word} 部分为待查的单词，比如 http://localhost:8000/test ，通过 mdx-server 查询，浏览器内将显示该单词在第 1 步所选词典内的解释。

MDX Server 核心功能由 [mdict-query](https://github.com/mmjang/mdict-query) 和 [PythonDictionaryOnline](https://github.com/amazon200code/PythonDictionaryOnline) 整合而成。

更多内容和屏幕截图，请查阅[手册](<./src/mdx_server/manual/mdx-server manual.pdf>)

