#!/bin/bash
set -e

echo "=========================================="
echo "法规变更情报与影响研判平台 - 启动脚本"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v docker &> /dev/null; then
    echo "错误: 未检测到 Docker，请先安装 Docker 和 Docker Compose"
    exit 1
fi

echo ""
echo "[1/4] 创建数据目录..."
mkdir -p backend/data/snapshots backend/data/attachments

echo ""
echo "[2/4] 构建并启动服务..."
docker compose up -d --build

echo ""
echo "[3/4] 等待服务就绪..."
sleep 5

echo ""
echo "[4/4] 检查服务状态..."
docker compose ps

echo ""
echo "=========================================="
echo "服务启动完成！"
echo "=========================================="
echo ""
echo "前端地址:  http://localhost:5173"
echo "后端 API:  http://localhost:8000"
echo "API 文档:  http://localhost:8000/docs"
echo ""
echo "PostgreSQL: localhost:5432 (postgres/postgres)"
echo "Redis:      localhost:6379"
echo ""
echo "查看日志:  docker compose logs -f"
echo "停止服务:  docker compose down"
echo "=========================================="
