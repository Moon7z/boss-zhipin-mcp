#!/bin/bash
# Boss直聘AI助手 - 一键安装脚本

set -e

echo "🚀 安装Boss直聘AI助手..."
echo "================================"

# 检查Python版本
echo ""
echo "1. 检查Python版本..."
python3 --version || (echo "❌ 需要Python 3.8+" && exit 1)

# 检查pip
echo ""
echo "2. 检查pip..."
pip3 --version || (echo "❌ 需要安装pip" && exit 1)

# 克隆仓库
echo ""
echo "3. 下载项目..."
if [ ! -d "boss-zhipin-mcp" ]; then
    git clone https://github.com/Moon7z/boss-zhipin-mcp.git
fi
cd boss-zhipin-mcp

# 安装依赖
echo ""
echo "4. 安装Python依赖..."
pip3 install -r requirements.txt

# 安装Playwright浏览器
echo ""
echo "5. 安装浏览器..."
playwright install chromium

# 创建启动脚本
echo ""
echo "6. 创建启动脚本..."
cat > boss-zhipin-mcp << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
python3 -m boss_mcp.server_v3 "$@"
EOF
chmod +x boss-zhipin-mcp

# 添加到PATH（可选）
echo ""
echo "7. 配置环境..."
if ! grep -q "boss-zhipin-mcp" ~/.bashrc 2>/dev/null; then
    echo "export PATH=\"\$PATH:$(pwd)\"" >> ~/.bashrc
    echo "✅ 已添加到PATH，请运行: source ~/.bashrc"
fi

echo ""
echo "================================"
echo "✅ 安装完成！"
echo ""
echo "启动方式:"
echo "  1. 直接运行: ./boss-zhipin-mcp"
echo "  2. 或使用: python3 -m boss_mcp.server_v3"
echo ""
echo "配置MCP客户端:"
echo "  查看README.md获取详细配置"
echo ""
echo "需要帮助?"
echo "  GitHub: https://github.com/Moon7z/boss-zhipin-mcp"
echo "================================"
