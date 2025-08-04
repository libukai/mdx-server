# 第一阶段：构建依赖
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖和元数据文件
COPY pyproject.toml uv.lock ./
# 再复制源码
COPY mdx_server ./mdx_server

RUN pip install --no-cache-dir uv && uv sync

# 第二阶段：生产镜像
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 只复制运行所需内容
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY mdx_server /app/mdx_server
COPY pyproject.toml /app/
COPY run_server.py /app/

# 创建词典目录在根目录
RUN mkdir -p /dict

# 工作目录设为 /app
WORKDIR /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 从 /app 运行，使用专用启动脚本
CMD ["python", "run_server.py"]
