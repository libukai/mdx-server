# MDX Server

MDX Server is a modern, high-performance service for reading MDX/MDD dictionary data and providing standard HTTP interfaces to external tools.

## ✨ Features

### 🆕 New Multi-Dictionary Support
- 🔀 **Multi-Dictionary Support**: Query multiple dictionaries with different routes
- 🚀 **Auto-Discovery**: Automatically detects and loads MDX files from directory
- 📱 **RESTful API**: Modern API endpoints for dictionary management and health checks
- 🔄 **Backward Compatible**: Existing single-dictionary setups continue to work seamlessly
- ⚡ **Smart Routing**: Route-based dictionary selection for organized access
- 📊 **Status Monitoring**: Real-time dictionary status and health monitoring

### Core Features
- **Python 3.13+ Modern Implementation**: Fully refactored with modern Python features
- **High Performance**: Threaded server with optimized query processing
- **Docker Support**: Ready-to-deploy containerized setup
- **Flexible Configuration**: JSON config files and environment variable support
- **Security**: Input validation and SQL injection protection

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/your-repo/mdx-server.git
cd mdx-server

# Install dependencies with uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# Or with pip
pip install -r requirements.txt
```

### 2. Setup Dictionaries

```bash
# Place your MDX files in the dictionary directory
mkdir -p src/mdx_server/dict
cp your_dictionaries/*.mdx src/mdx_server/dict/
```

### 3. Run Server

```bash
cd src/mdx_server
python3 mdx_server.py
```

### 4. Test Multi-Dictionary Features

```bash
# Query default dictionary
curl http://localhost:8000/hello

# Query specific dictionary (if you have oxford.mdx)
curl http://localhost:8000/oxford/hello

# Get dictionary list
curl http://localhost:8000/api/dicts

# Health check
curl http://localhost:8000/health
```

## 📖 API Documentation

### Dictionary Query Routes

| Route | Description | Example |
|-------|-------------|---------|
| `GET /{word}` | Query default dictionary | `/hello` |
| `GET /{route}/{word}` | Query specific dictionary | `/oxford/hello` |

### Management API Routes

| Route | Description | Response |
|-------|-------------|----------|
| `GET /api/dicts` | List all dictionaries | JSON dictionary info |
| `GET /health` | Health check | JSON status |

### Example API Response

```json
// GET /api/dicts
{
  "dictionaries": [
    {
      "id": "oxford",
      "name": "Oxford Dictionary",
      "route": "oxford", 
      "path": "dict/oxford.mdx",
      "enabled": true,
      "status": "loaded"
    }
  ],
  "mode": "multi",
  "total": 1
}
```

## ⚙️ Configuration

### Multi-Dictionary Configuration

Create `src/mdx_server/config.json`:

```json
{
  "host": "",
  "port": 8000,
  "debug": false,
  "dict_directory": "dict",
  
  "dictionaries": {
    "oxford": {
      "name": "Oxford Advanced Learner's Dictionary",
      "path": "dict/oxford.mdx",
      "route": "oxford",
      "enabled": true
    },
    "collins": {
      "name": "Collins Dictionary",
      "path": "dict/collins.mdx", 
      "route": "collins",
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

### Environment Variables

```bash
export MDX_PORT=8001
export MDX_DEBUG=true
export MDX_DICT_DIR=my_dicts
python3 mdx_server.py
```

### Auto-Discovery Mode

If no `dictionaries` configuration is provided, the server automatically discovers all `.mdx` files:

```bash
dict/
├── oxford.mdx          # Route: /oxford/{word}
├── collins.mdx         # Route: /collins/{word}
├── default.mdx         # Route: /{word} (default)
└── etymology.mdx       # Route: /etymology/{word}
```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f mdx-server
```

### Manual Docker Build

```bash
# Build image
docker build -t mdx-server .

# Run container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/dict:/app/src/mdx_server/dict \
  --name mdx-server \
  mdx-server
```

## 🔄 Upgrade Guide

### From Single Dictionary (v1.x) to Multi-Dictionary (v2.x)

**No changes required!** The upgrade is seamless:

1. **Existing setup continues to work** - Your current single dictionary remains accessible
2. **Add more dictionaries** - Simply place additional `.mdx` files in the `dict/` directory
3. **Optional configuration** - Create `config.json` for custom routes and names

**Before:**
```
dict/
└── my_dictionary.mdx    # Accessible via /{word}
```

**After:**
```
dict/
├── my_dictionary.mdx    # Still accessible via /{word}
├── oxford.mdx           # New: /oxford/{word}
└── collins.mdx          # New: /collins/{word}
```

## 🛠️ Development

### Code Quality Tools

```bash
# Linting and formatting
uv run ruff check .
uv run ruff format .

# Type checking  
uv run mypy .
```

### Testing

```bash
# Run tests
uv run pytest

# Test with real MDX files
python3 -c "from config import load_config; print(load_config())"
```

## 📚 Documentation

- **[API Design](API_DESIGN.md)** - Complete API specification
- **[Multi-Dict Architecture](MULTI_DICT_DESIGN.md)** - Technical architecture overview
- **[Performance Guide](PERFORMANCE_OPTIMIZATION.md)** - Optimization strategies
- **[Implementation Roadmap](IMPLEMENTATION_ROADMAP.md)** - Development roadmap
- **[User Manual](src/mdx_server/manual/)** - Detailed user guide with screenshots

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and test thoroughly
4. Run code quality checks: `uv run ruff check . && uv run ruff format .`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project builds upon [mdict-query](https://github.com/mmjang/mdict-query) and [PythonDictionaryOnline](https://github.com/amazon200code/PythonDictionaryOnline).

## 🎯 Use Cases

MDX Server enables various applications to access dictionary data:

- **Language Learning Apps**: Anki add-ons, vocabulary builders
- **Reading Tools**: Kindle companion apps, browser extensions
- **Development Tools**: IDE dictionary plugins, documentation tools
- **Research**: Academic text analysis, linguistic research
- **Mobile Apps**: Dictionary apps with custom MDX collections

---

Built with ❤️ for the dictionary community. Supports Python 3.13+ with modern async/await patterns and type hints.