#!/bin/bash

# 视频分析系统 - 一键安装脚本
# 支持：Ubuntu/Debian/CentOS/RHEL/macOS

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          视频分析系统 - 一键安装（Docker 版）              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检测操作系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        OS="unknown"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "❌ 不支持的操作系统: $OSTYPE"
    exit 1
fi

echo "📋 检测到操作系统: $OS"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    echo ""
    echo "请先安装 Docker："
    echo ""
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        echo "  curl -fsSL https://get.docker.com | sh"
        echo "  sudo usermod -aG docker \$USER"
    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]]; then
        echo "  curl -fsSL https://get.docker.com | sh"
        echo "  sudo systemctl start docker"
        echo "  sudo systemctl enable docker"
        echo "  sudo usermod -aG docker \$USER"
    elif [[ "$OS" == "macos" ]]; then
        echo "  下载并安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
    fi
    echo ""
    echo "安装完成后，请重新登录并再次运行此脚本"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    echo ""
    echo "请先安装 Docker Compose："
    echo "  sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose"
    echo "  sudo chmod +x /usr/local/bin/docker-compose"
    exit 1
fi

echo "✅ Docker 已安装"
echo "✅ Docker Compose 已安装"
echo ""

# 创建必要的目录
echo "📁 创建数据目录..."
mkdir -p backend/downloads
mkdir -p backend/compressed
mkdir -p backend/preset_images

# 创建默认配置文件（如果不存在）
if [ ! -f backend/api_config.yaml ]; then
    echo "📝 创建默认配置文件..."
    cat > backend/api_config.yaml << 'EOF'
active: gemini
max_concurrency: 5
apis:
  gemini:
    name: Google Gemini
    api_key: ""
    base_url: https://generativelanguage.googleapis.com/v1beta
    model: gemini-2.0-flash-exp
    temperature: 0.7
    max_tokens: 4096
    use_native_sdk: false
  custom:
    name: 自定义 API
    api_key: ""
    base_url: ""
    model: ""
    temperature: 0.7
    max_tokens: 4096
EOF
fi

echo ""
echo "🚀 开始构建 Docker 镜像..."
echo "   （首次构建需要 5-10 分钟，请耐心等待）"
echo ""

# 构建并启动容器
if docker compose version &> /dev/null; then
    docker compose build
    docker compose up -d
else
    docker-compose build
    docker-compose up -d
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    🎉 安装完成！                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📍 访问地址："
echo "   前端页面：http://localhost:1018"
echo "   管理后台：http://localhost:1018/admin"
echo ""
echo "🔧 配置 API 密钥："
echo "   1. 访问管理后台：http://localhost:1018/admin"
echo "   2. 默认密码：admin123"
echo "   3. 在 API 配置页面填写 Gemini API Key"
echo ""
echo "📊 查看日志："
if docker compose version &> /dev/null; then
    echo "   docker compose logs -f"
else
    echo "   docker-compose logs -f"
fi
echo ""
echo "🛑 停止服务："
if docker compose version &> /dev/null; then
    echo "   docker compose down"
else
    echo "   docker-compose down"
fi
echo ""
echo "🔄 重启服务："
if docker compose version &> /dev/null; then
    echo "   docker compose restart"
else
    echo "   docker-compose restart"
fi
echo ""
