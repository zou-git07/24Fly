#!/bin/bash
# 启动 Web 监控系统

echo "=========================================="
echo "  🤖 Robot Web Monitor"
echo "=========================================="
echo ""

# 检查依赖
echo "📦 Checking dependencies..."
python3 -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies. Installing..."
    pip3 install fastapi uvicorn websockets
fi

echo "✅ Dependencies OK"
echo ""

# 启动服务器
echo "🚀 Starting Web Monitor..."
echo ""
echo "📊 Open in browser: http://localhost:8080"
echo "🔴 Live Monitor: http://localhost:8080/static/index.html"
echo "📋 Match Logs: http://localhost:8080/static/logs.html"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."
python3 RobotMonitoringSystem/monitor_daemon/web_monitor.py
