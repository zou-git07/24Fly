#!/bin/bash

# 挂载机器人日志目录到本地进行实时分析

echo "      机器人日志实时挂载系统"
echo ""

# 检查sshfs是否安装
if ! command -v sshfs &> /dev/null; then
    echo "❌ 错误: sshfs 未安装"
    echo ""
    echo "请先安装 sshfs:"
    echo "  Ubuntu/Debian: sudo apt-get install sshfs"
    echo "  Fedora: sudo dnf install fuse-sshfs"
    echo "  Arch: sudo pacman -S sshfs"
    exit 1
fi

# 检查参数
if [ $# -lt 1 ]; then
    echo "用法: $0 <操作> [机器人IP列表]"
    echo ""
    echo "操作:"
    echo "  mount   - 挂载机器人日志目录"
    echo "  umount  - 卸载所有挂载"
    echo "  status  - 查看挂载状态"
    echo "  watch   - 实时监控日志"
    echo ""
    echo "示例:"
    echo "  $0 mount 10.0.70.13 10.0.70.14 10.0.70.15"
    echo "  $0 umount"
    echo "  $0 status"
    echo "  $0 watch"
    exit 1
fi

OPERATION=$1
shift
ROBOT_IPS=("$@")

# 创建挂载点目录
MOUNT_BASE="RobotLogs_Live"
mkdir -p "$MOUNT_BASE"

case $OPERATION in
    mount)
        if [ ${#ROBOT_IPS[@]} -eq 0 ]; then
            echo "❌ 错误: 请提供至少一个机器人IP地址"
            exit 1
        fi
        
        echo "开始挂载机器人日志目录..."
        echo ""
        
        for i in "${!ROBOT_IPS[@]}"; do
            IP="${ROBOT_IPS[$i]}"
            NUM=$((i+1))
            MOUNT_POINT="$MOUNT_BASE/Robot$NUM"
            
            # 创建挂载点
            mkdir -p "$MOUNT_POINT"
            
            echo "挂载机器人 $NUM ($IP)..."
            
            # 检查是否已经挂载
            if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
                echo "  ⚠️  已经挂载，先卸载..."
                fusermount -u "$MOUNT_POINT" 2>/dev/null || umount "$MOUNT_POINT" 2>/dev/null
                sleep 1
            fi
            
            # 挂载
            sshfs -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,follow_symlinks \
                  nao@$IP:/home/nao/logs "$MOUNT_POINT" 2>/dev/null
            
            if [ $? -eq 0 ]; then
                echo "  ✅ 机器人 $NUM 挂载成功: $MOUNT_POINT"
                
                # 显示日志文件
                FILE_COUNT=$(ls -1 "$MOUNT_POINT"/*.log 2>/dev/null | wc -l)
                if [ $FILE_COUNT -gt 0 ]; then
                    TOTAL_SIZE=$(du -sh "$MOUNT_POINT" 2>/dev/null | cut -f1)
                    echo "     日志文件: $FILE_COUNT 个, 总大小: $TOTAL_SIZE"
                fi
            else
                echo "  ❌ 机器人 $NUM 挂载失败"
                echo "     请检查: 1) 机器人是否开机 2) IP是否正确 3) SSH密码"
            fi
            echo ""
        done
        
        echo "=========================================="
        echo "挂载完成！"
        echo ""
        echo "日志目录: $MOUNT_BASE/"
        echo ""
        echo "现在可以:"
        echo "  1. 查看日志: ls -lh $MOUNT_BASE/Robot1/"
        echo "  2. 实时监控: $0 watch"
        echo "  3. 实时分析: python3 realtime_analyze.py"
        echo "  4. 卸载: $0 umount"
        echo "=========================================="
        ;;
        
    umount)
        echo "卸载所有机器人日志目录..."
        echo ""
        
        UNMOUNTED=0
        for mount_point in "$MOUNT_BASE"/Robot*; do
            if [ -d "$mount_point" ]; then
                if mountpoint -q "$mount_point" 2>/dev/null; then
                    echo "卸载: $mount_point"
                    fusermount -u "$mount_point" 2>/dev/null || umount "$mount_point" 2>/dev/null
                    if [ $? -eq 0 ]; then
                        echo "  ✅ 卸载成功"
                        UNMOUNTED=$((UNMOUNTED + 1))
                    else
                        echo "  ❌ 卸载失败"
                    fi
                fi
            fi
        done
        
        echo ""
        if [ $UNMOUNTED -gt 0 ]; then
            echo "✅ 已卸载 $UNMOUNTED 个挂载点"
        else
            echo "ℹ️  没有找到已挂载的目录"
        fi
        ;;
        
    status)
        echo "挂载状态:"
        echo ""
        
        MOUNTED=0
        for mount_point in "$MOUNT_BASE"/Robot*; do
            if [ -d "$mount_point" ]; then
                ROBOT_NAME=$(basename "$mount_point")
                if mountpoint -q "$mount_point" 2>/dev/null; then
                    echo "✅ $ROBOT_NAME: 已挂载"
                    
                    # 显示文件信息
                    FILE_COUNT=$(ls -1 "$mount_point"/*.log 2>/dev/null | wc -l)
                    if [ $FILE_COUNT -gt 0 ]; then
                        TOTAL_SIZE=$(du -sh "$mount_point" 2>/dev/null | cut -f1)
                        echo "   日志文件: $FILE_COUNT 个, 总大小: $TOTAL_SIZE"
                        
                        # 显示最新文件
                        LATEST=$(ls -t "$mount_point"/*.log 2>/dev/null | head -1)
                        if [ -n "$LATEST" ]; then
                            LATEST_NAME=$(basename "$LATEST")
                            LATEST_SIZE=$(du -h "$LATEST" 2>/dev/null | cut -f1)
                            LATEST_TIME=$(stat -c %y "$LATEST" 2>/dev/null | cut -d. -f1)
                            echo "   最新: $LATEST_NAME ($LATEST_SIZE, $LATEST_TIME)"
                        fi
                    fi
                    MOUNTED=$((MOUNTED + 1))
                else
                    echo "❌ $ROBOT_NAME: 未挂载"
                fi
                echo ""
            fi
        done
        
        if [ $MOUNTED -eq 0 ]; then
            echo "ℹ️  没有已挂载的机器人"
            echo ""
            echo "使用以下命令挂载:"
            echo "  $0 mount 10.0.70.13 10.0.70.14 10.0.70.15"
        fi
        ;;
        
    watch)
        echo "实时监控日志文件变化..."
        echo "按 Ctrl+C 停止"
        echo ""
        
        if ! command -v inotifywait &> /dev/null; then
            echo "⚠️  inotifywait 未安装，使用轮询模式"
            echo ""
            
            # 轮询模式
            while true; do
                clear
                echo "=== 实时日志监控 ($(date '+%Y-%m-%d %H:%M:%S')) ==="
                echo ""
                
                for mount_point in "$MOUNT_BASE"/Robot*; do
                    if [ -d "$mount_point" ] && mountpoint -q "$mount_point" 2>/dev/null; then
                        ROBOT_NAME=$(basename "$mount_point")
                        echo "[$ROBOT_NAME]"
                        
                        FILE_COUNT=$(ls -1 "$mount_point"/*.log 2>/dev/null | wc -l)
                        TOTAL_SIZE=$(du -sh "$mount_point" 2>/dev/null | cut -f1)
                        echo "  文件数: $FILE_COUNT, 总大小: $TOTAL_SIZE"
                        
                        # 最新的3个文件
                        ls -lht "$mount_point"/*.log 2>/dev/null | head -3 | while read line; do
                            echo "  $line"
                        done
                        echo ""
                    fi
                done
                
                sleep 2
            done
        else
            # inotify模式
            inotifywait -m -r -e create,modify,moved_to "$MOUNT_BASE" 2>/dev/null | while read path action file; do
                if [[ "$file" == *.log ]]; then
                    ROBOT=$(echo "$path" | grep -oP 'Robot\d+')
                    echo "[$(date '+%H:%M:%S')] $ROBOT: $action - $file"
                fi
            done
        fi
        ;;
        
    *)
        echo "❌ 未知操作: $OPERATION"
        echo "支持的操作: mount, umount, status, watch"
        exit 1
        ;;
esac
