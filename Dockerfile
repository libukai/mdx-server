# 第一阶段：构建依赖
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖和元数据文件
COPY pyproject.toml uv.lock ./
# 再复制源码
COPY src ./src

RUN pip install --no-cache-dir uv && uv sync

# 第二阶段：生产镜像
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 只复制运行所需内容
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY src /app/src
COPY pyproject.toml /app/

# 创建 dict 目录
RUN mkdir -p /app/src/mdx_server/dict

WORKDIR /app/src/mdx_server

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "mdx_server.py"]
