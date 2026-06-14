#!/bin/bash
# ACAS Pro v2.1 - 生产部署脚本
# 高智中科（北京）科技有限公司

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
PROJECT_NAME="acas-pro"
BACKUP_DIR="./backups/pre-deploy-$(date +%Y%m%d_%H%M%S)"

# 打印信息
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ACAS Pro v2.1 生产部署脚本${NC}"
echo -e "${GREEN}  高智中科（北京）科技有限公司${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查环境
check_prerequisites() {
    echo -e "${YELLOW}[1/6] 检查环境...${NC}"
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker 未安装${NC}"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}错误: Docker Compose 未安装${NC}"
        exit 1
    fi
    
    # 检查 .env 文件
    if [ ! -f .env ]; then
        echo -e "${YELLOW}警告: .env 文件不存在，使用默认配置${NC}"
        cp .env.example .env
        echo -e "${RED}请编辑 .env 文件设置生产环境配置后再运行！${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}  ✓ 环境检查通过${NC}"
}

# 备份数据
backup_data() {
    echo -e "${YELLOW}[2/6] 备份数据...${NC}"
    
    mkdir -p "$BACKUP_DIR"
    
    # 备份数据库
    if docker-compose ps | grep -q postgres; then
        echo "  备份 PostgreSQL..."
        docker-compose exec -T postgres pg_dump -U acas acas_pro > "$BACKUP_DIR/database.sql"
    fi
    
    # 备份 .keys 目录
    if [ -d .keys ]; then
        echo "  备份密钥..."
        cp -r .keys "$BACKUP_DIR/"
    fi
    
    echo -e "${GREEN}  ✓ 备份完成: $BACKUP_DIR${NC}"
}

# 拉取最新代码
update_code() {
    echo -e "${YELLOW}[3/6] 更新代码...${NC}"
    
    # 如果有 git，拉取最新
    if [ -d .git ]; then
        git pull origin main
    fi
    
    echo -e "${GREEN}  ✓ 代码更新完成${NC}"
}

# 构建和启动服务
deploy_services() {
    echo -e "${YELLOW}[4/6] 构建和启动服务...${NC}"
    
    # 拉取最新镜像
    docker-compose pull
    
    # 构建应用镜像
    docker-compose build --no-cache api
    
    # 启动服务
    docker-compose up -d
    
    echo -e "${GREEN}  ✓ 服务已启动${NC}"
}

# 等待服务就绪
wait_for_services() {
    echo -e "${YELLOW}[5/6] 等待服务就绪...${NC}"
    
    # 等待 PostgreSQL
    echo "  等待 PostgreSQL..."
    until docker-compose exec -T postgres pg_isready -U acas > /dev/null 2>&1; do
        sleep 1
    done
    
    # 等待 API
    echo "  等待 API 服务..."
    until curl -sf http://localhost:5000/health > /dev/null 2>&1; do
        sleep 1
    done
    
    echo -e "${GREEN}  ✓ 所有服务已就绪${NC}"
}

# 执行数据库迁移
run_migrations() {
    echo -e "${YELLOW}[6/6] 执行数据库迁移...${NC}"
    
    # 创建表
    docker-compose exec -T api python -c "from database.migrate_pg import init_postgres; init_postgres()"
    
    echo -e "${GREEN}  ✓ 数据库迁移完成${NC}"
}

# 显示状态
show_status() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "服务状态:"
    docker-compose ps
    echo ""
    echo "访问地址:"
    echo "  - Web 界面: http://localhost"
    echo "  - API: http://localhost/api/v2"
    echo "  - 健康检查: http://localhost/health"
    echo ""
    echo "常用命令:"
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
    echo ""
}

# 主流程
main() {
    check_prerequisites
    backup_data
    update_code
    deploy_services
    wait_for_services
    run_migrations
    show_status
}

# 处理参数
case "${1:-}" in
    "backup")
        backup_data
        ;;
    "rollback")
        echo "回滚功能待实现"
        ;;
    "status")
        docker-compose ps
        ;;
    "logs")
        docker-compose logs -f
        ;;
    *)
        main
        ;;
esac
