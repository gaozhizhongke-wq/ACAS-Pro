# ACAS Pro v2.1 - Docker 镜像
# 高智中科（北京）科技有限公司

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p logs backups .keys certs

# 非 root 用户运行
RUN useradd -m -u 1000 acas && \
    chown -R acas:acas /app
USER acas

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 启动命令
CMD ["python", "api_server_v2.py"]
