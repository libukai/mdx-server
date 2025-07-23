# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables for performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install uv for faster dependency management
RUN pip install uv

# Install dependencies (no --frozen since we may not have exact lock)
RUN uv sync

# Create an empty dict directory in the correct location
RUN mkdir -p /app/src/mdx_server/dict

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Set working directory to where the server script is located
WORKDIR /app/src/mdx_server

# Create a production config for Docker
RUN echo '{\
  "host": "0.0.0.0",\
  "port": 8000,\
  "debug": false,\
  "dict_directory": "dict",\
  "resource_directory": "mdx",\
  "cache_enabled": true,\
  "max_word_length": 100,\
  "log_level": "INFO",\
  "log_file": null,\
  "server_type": "threaded",\
  "max_threads": 20,\
  "request_queue_size": 50,\
  "connection_timeout": 30,\
  "use_gunicorn": false,\
  "gunicorn_workers": 4,\
  "gunicorn_threads": 5\
}' > config.json

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run mdx_server.py when the container launches
CMD ["python", "mdx_server.py"]
