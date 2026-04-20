#!/bin/bash
clear
echo "===== B-Human 里程计校准工具 v2 (固定起点 + 向前/横向分开测量) ====="
echo "坐标单位：mm"
echo ""

# ================== 模式选择 ==================
while true; do
    read -p "选择模式：1 - 初次测量(k=1) | 2 - 迭代优化(当前k≠1)：" mode
    [[ "$mode" == "1" || "$mode" == "2" ]] && break
    echo "输入错误，请输入 1 或 2"
done

# ================== 迭代模式：输入当前系数 ==================
current_kx=1.0
current_ky=1.0
if [[ "$mode" == "2" ]]; then
    echo ""
    read -p "输入当前 kx：" current_kx
    read -p "输入当前 ky：" current_ky
fi

# ================== 输入【共用起点】原始坐标（只输一次！） ==================
echo ""
echo "==================== 原始坐标（所有测量共用起点） ===================="
read -p "起点 x0：" x0
read -p "起点 y0：" y0
echo ""

# ================== 输入测量组数 ==================
read -p "请输入本次测量总组数：" group_count
echo ""

# 存储结果
sum_kx=0
sum_ky=0
cnt_x=0
cnt_y=0

# ================== 循环输入每组数据 ==================
for ((i=1; i<=group_count; i++)); do
    echo "=================================================="
    echo "第 $i 组数据"
    echo "=================================================="

    # 选择运动类型
    while true; do
        read -p "运动类型：1 - 向前走(x轴) | 2 - 横向走(y轴)：" move_type
        [[ "$move_type" == "1" || "$move_type" == "2" ]] && break
        echo "输入错误，请输入 1 或 2"
    done

    # 输入里程计估计坐标 + 实际物理坐标
    read -p "估计坐标 x_est：" x_est
    read -p "估计坐标 y_est：" y_est
    read -p "实际坐标 x_real：" x_real
    read -p "实际坐标 y_real：" y_real

    # 计算位移
    dx_est=$(echo "$x_est - $x0" | bc -l)
    dy_est=$(echo "$y_est - $y0" | bc -l)
    dx_real=$(echo "$x_real - $x0" | bc -l)
    dy_real=$(echo "$y_real - $y0" | bc -l)

    # 根据运动类型计算系数
    if [[ "$move_type" == "1" ]]; then
        # 向前走 → 只算 x 比例
        echo "→ 模式：向前走，计算 kx"
        rx=$(echo "scale=6; $dx_real / $dx_est" | bc -l)
        if [[ "$mode" == "1" ]]; then
            kx_i=$rx
        else
            kx_i=$(echo "$current_kx * $rx" | bc -l)
        fi
        sum_kx=$(echo "$sum_kx + $kx_i" | bc -l)
        cnt_x=$((cnt_x + 1))
        echo "→ 本组 kx 贡献：$kx_i"
    else
        # 横向走 → 只算 y 比例
        echo "→ 模式：横向走，计算 ky"
        ry=$(echo "scale=6; $dy_real / $dy_est" | bc -l)
        if [[ "$mode" == "1" ]]; then
            ky_i=$ry
        else
            ky_i=$(echo "$current_ky * $ry" | bc -l)
        fi
        sum_ky=$(echo "$sum_ky + $ky_i" | bc -l)
        cnt_y=$((cnt_y + 1))
        echo "→ 本组 ky 贡献：$ky_i"
    fi
    echo ""
done

# ================== 计算最终平均系数 ==================
if [[ $cnt_x -gt 0 ]]; then
    final_kx=$(echo "scale=4; $sum_kx / $cnt_x" | bc -l)
else
    final_kx="无测量数据"
fi

if [[ $cnt_y -gt 0 ]]; then
    final_ky=$(echo "scale=4; $sum_ky / $cnt_y" | bc -l)
else
    final_ky="无测量数据"
fi

# ================== 输出结果 ==================
echo "================================================================"
echo "                          最终校准结果                          "
echo "================================================================"
echo "kx 有效测量组数：$cnt_x"
echo "ky 有效测量组数：$cnt_y"
echo ""
echo "推荐 odometryWalkScaling 系数："
echo "   kx = $final_kx"
echo "   ky = $final_ky"
echo "================================================================"
echo "直接填入配置文件即可！"
