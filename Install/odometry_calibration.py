#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器人里程计校准工具
用于校准B-Human框架下机器人的里程计x和y系数
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from typing import List, Tuple, Optional


class OdometryCalibrationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("机器人里程计校准工具")
        self.root.geometry("1000x700")
        
        # 数据存储
        self.measurements = []
        self.current_kx = 1.0
        self.current_ky = 1.0
        self.start_x = 0.0
        self.start_y = 0.0
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 1. 当前系数输入区域
        coeff_frame = ttk.LabelFrame(main_frame, text="当前系数", padding="10")
        coeff_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(coeff_frame, text="当前X系数 (Kx):").grid(row=0, column=0, padx=5)
        self.kx_entry = ttk.Entry(coeff_frame, width=15)
        self.kx_entry.insert(0, "1.0")
        self.kx_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(coeff_frame, text="当前Y系数 (Ky):").grid(row=0, column=2, padx=5)
        self.ky_entry = ttk.Entry(coeff_frame, width=15)
        self.ky_entry.insert(0, "1.0")
        self.ky_entry.grid(row=0, column=3, padx=5)
        
        ttk.Button(coeff_frame, text="更新系数", command=self.update_coefficients).grid(
            row=0, column=4, padx=10
        )
        
        # 2. 起始坐标输入区域
        start_frame = ttk.LabelFrame(main_frame, text="起始坐标（只需设置一次）", padding="10")
        start_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(start_frame, text="起始X坐标:").grid(row=0, column=0, padx=5)
        self.start_x_entry = ttk.Entry(start_frame, width=15)
        self.start_x_entry.insert(0, "0.0")
        self.start_x_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(start_frame, text="起始Y坐标:").grid(row=0, column=2, padx=5)
        self.start_y_entry = ttk.Entry(start_frame, width=15)
        self.start_y_entry.insert(0, "0.0")
        self.start_y_entry.grid(row=0, column=3, padx=5)
        
        ttk.Button(start_frame, text="设置起始坐标", command=self.set_start_position).grid(
            row=0, column=4, padx=10
        )
        
        # 3. 测量数据表格区域
        table_frame = ttk.LabelFrame(main_frame, text="测量数据", padding="10")
        table_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # 创建表格
        columns = ("序号", "运动方向", "估算X", "估算Y", "实际X", "实际Y")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "序号":
                self.tree.column(col, width=50, anchor=tk.CENTER)
            elif col == "运动方向":
                self.tree.column(col, width=100, anchor=tk.CENTER)
            else:
                self.tree.column(col, width=120, anchor=tk.CENTER)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 绑定双击事件用于编辑
        self.tree.bind('<Double-1>', self.on_double_click)
        
        # 4. 数据输入区域
        input_frame = ttk.LabelFrame(main_frame, text="添加测量数据", padding="10")
        input_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(input_frame, text="运动方向:").grid(row=0, column=0, padx=5)
        self.direction_var = tk.StringVar(value="前进")
        direction_combo = ttk.Combobox(input_frame, textvariable=self.direction_var, 
                                       values=["前进", "横移"], width=12, state="readonly")
        direction_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="估算X:").grid(row=0, column=2, padx=5)
        self.est_x_entry = ttk.Entry(input_frame, width=12)
        self.est_x_entry.grid(row=0, column=3, padx=5)
        
        ttk.Label(input_frame, text="估算Y:").grid(row=0, column=4, padx=5)
        self.est_y_entry = ttk.Entry(input_frame, width=12)
        self.est_y_entry.grid(row=0, column=5, padx=5)
        
        ttk.Label(input_frame, text="实际X:").grid(row=0, column=6, padx=5)
        self.real_x_entry = ttk.Entry(input_frame, width=12)
        self.real_x_entry.grid(row=0, column=7, padx=5)
        
        ttk.Label(input_frame, text="实际Y:").grid(row=0, column=8, padx=5)
        self.real_y_entry = ttk.Entry(input_frame, width=12)
        self.real_y_entry.grid(row=0, column=9, padx=5)
        
        ttk.Button(input_frame, text="添加数据", command=self.add_measurement).grid(
            row=0, column=10, padx=10
        )
        
        # 5. 操作按钮区域
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(button_frame, text="删除选中数据", command=self.delete_measurement).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="清空所有数据", command=self.clear_all).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="计算新系数", command=self.calculate_coefficients).pack(
            side=tk.LEFT, padx=5
        )
        
        # 6. 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="计算结果", padding="10")
        result_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.result_text = tk.Text(result_frame, height=6, width=80)
        self.result_text.pack(fill=tk.BOTH, expand=True)
    
    def update_coefficients(self):
        """更新当前系数"""
        try:
            self.current_kx = float(self.kx_entry.get())
            self.current_ky = float(self.ky_entry.get())
            messagebox.showinfo("成功", f"系数已更新：Kx={self.current_kx}, Ky={self.current_ky}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def set_start_position(self):
        """设置起始坐标"""
        try:
            self.start_x = float(self.start_x_entry.get())
            self.start_y = float(self.start_y_entry.get())
            messagebox.showinfo("成功", f"起始坐标已设置：({self.start_x}, {self.start_y})")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def add_measurement(self):
        """添加测量数据"""
        try:
            direction = self.direction_var.get()
            est_x = float(self.est_x_entry.get())
            est_y = float(self.est_y_entry.get())
            real_x = float(self.real_x_entry.get())
            real_y = float(self.real_y_entry.get())
            
            measurement = {
                'direction': direction,
                'estimated': (est_x, est_y),
                'actual': (real_x, real_y)
            }
            
            self.measurements.append(measurement)
            
            # 添加到表格
            idx = len(self.measurements)
            self.tree.insert('', tk.END, values=(
                idx, direction, est_x, est_y, real_x, real_y
            ))
            
            # 清空输入框
            self.est_x_entry.delete(0, tk.END)
            self.est_y_entry.delete(0, tk.END)
            self.real_x_entry.delete(0, tk.END)
            self.real_y_entry.delete(0, tk.END)
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def delete_measurement(self):
        """删除选中的测量数据"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的数据")
            return
        
        for item in selected:
            idx = self.tree.index(item)
            self.tree.delete(item)
            if 0 <= idx < len(self.measurements):
                self.measurements.pop(idx)
        
        # 重新编号
        self.refresh_table()
    
    def clear_all(self):
        """清空所有数据"""
        if messagebox.askyesno("确认", "确定要清空所有测量数据吗？"):
            self.measurements.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.result_text.delete(1.0, tk.END)
    
    def refresh_table(self):
        """刷新表格显示"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for idx, m in enumerate(self.measurements, 1):
            self.tree.insert('', tk.END, values=(
                idx, m['direction'], 
                m['estimated'][0], m['estimated'][1],
                m['actual'][0], m['actual'][1]
            ))
    
    def on_double_click(self, event):
        """处理双击事件，开始编辑单元格"""
        region = self.tree.identify('region', event.x, event.y)
        if region != 'cell':
            return
        
        column = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        
        if not row_id:
            return
        
        # 获取列索引（#1, #2, ... -> 0, 1, ...）
        col_idx = int(column.replace('#', '')) - 1
        
        # 序号列不可编辑
        if col_idx == 0:
            return
        
        # 获取当前值
        values = self.tree.item(row_id, 'values')
        current_value = values[col_idx]
        
        # 获取单元格位置
        x, y, width, height = self.tree.bbox(row_id, column)
        
        # 创建编辑框
        if col_idx == 1:  # 运动方向列，使用下拉框
            edit_widget = ttk.Combobox(self.tree, values=['前进', '横移'], state='readonly')
            edit_widget.set(current_value)
        else:  # 数值列，使用输入框
            edit_widget = ttk.Entry(self.tree)
            edit_widget.insert(0, current_value)
        
        edit_widget.place(x=x, y=y, width=width, height=height)
        edit_widget.focus()
        
        # 保存编辑信息
        edit_widget.row_id = row_id
        edit_widget.col_idx = col_idx
        
        # 绑定事件
        edit_widget.bind('<Return>', self.save_edit)
        edit_widget.bind('<FocusOut>', self.save_edit)
        edit_widget.bind('<Escape>', lambda e: edit_widget.destroy())
        
        self.current_edit_widget = edit_widget
    
    def save_edit(self, event):
        """保存编辑的内容"""
        widget = event.widget
        new_value = widget.get()
        row_id = widget.row_id
        col_idx = widget.col_idx
        
        # 获取当前行的所有值
        values = list(self.tree.item(row_id, 'values'))
        
        # 验证数值列的输入
        if col_idx > 1:  # 数值列
            try:
                float(new_value)
            except ValueError:
                messagebox.showerror('错误', '请输入有效的数字')
                widget.destroy()
                return
        
        # 更新表格显示
        values[col_idx] = new_value
        self.tree.item(row_id, values=values)
        
        # 更新measurements数据
        row_idx = int(values[0]) - 1  # 序号从1开始，索引从0开始
        
        if 0 <= row_idx < len(self.measurements):
            if col_idx == 1:  # 运动方向
                self.measurements[row_idx]['direction'] = new_value
            elif col_idx == 2:  # 估算X
                est_y = self.measurements[row_idx]['estimated'][1]
                self.measurements[row_idx]['estimated'] = (float(new_value), est_y)
            elif col_idx == 3:  # 估算Y
                est_x = self.measurements[row_idx]['estimated'][0]
                self.measurements[row_idx]['estimated'] = (est_x, float(new_value))
            elif col_idx == 4:  # 实际X
                real_y = self.measurements[row_idx]['actual'][1]
                self.measurements[row_idx]['actual'] = (float(new_value), real_y)
            elif col_idx == 5:  # 实际Y
                real_x = self.measurements[row_idx]['actual'][0]
                self.measurements[row_idx]['actual'] = (real_x, float(new_value))
        
        widget.destroy()
    
    def calculate_coefficients(self):
        """使用最小二乘法计算新的系数"""
        if len(self.measurements) < 2:
            messagebox.showwarning("警告", "至少需要2组测量数据才能计算系数")
            return
        
        try:
            # 判断是否为初始状态（K=1）
            is_initial = (abs(self.current_kx - 1.0) < 1e-6 and 
                         abs(self.current_ky - 1.0) < 1e-6)
            
            if is_initial:
                # K=1的情况：估算坐标就是原始数据乘以1
                new_kx, new_ky = self._calculate_initial_coefficients()
            else:
                # K≠1的情况：需要反推原始数据
                new_kx, new_ky = self._calculate_iterative_coefficients()
            
            # 显示结果
            result = f"计算完成！\n\n"
            result += f"当前系数：Kx = {self.current_kx:.6f}, Ky = {self.current_ky:.6f}\n"
            result += f"新计算系数：Kx = {new_kx:.6f}, Ky = {new_ky:.6f}\n\n"
            result += f"建议更新 odometryWalkScaling 参数为：\n"
            result += f"  x: {new_kx:.6f}\n"
            result += f"  y: {new_ky:.6f}\n\n"
            result += f"使用了 {len(self.measurements)} 组测量数据\n"
            
            # 计算误差统计
            errors = self._calculate_errors(new_kx, new_ky, is_initial)
            result += f"\n平均误差：X方向 = {errors['mean_x']:.2f} mm, Y方向 = {errors['mean_y']:.2f} mm\n"
            result += f"最大误差：X方向 = {errors['max_x']:.2f} mm, Y方向 = {errors['max_y']:.2f} mm"
            
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, result)
            
            # 询问是否更新系数
            if messagebox.askyesno("更新系数", "是否将新计算的系数设置为当前系数？"):
                self.kx_entry.delete(0, tk.END)
                self.kx_entry.insert(0, f"{new_kx:.6f}")
                self.ky_entry.delete(0, tk.END)
                self.ky_entry.insert(0, f"{new_ky:.6f}")
                self.update_coefficients()
            
        except Exception as e:
            messagebox.showerror("计算错误", f"计算过程中出现错误：{str(e)}")
    
    def _calculate_initial_coefficients(self) -> Tuple[float, float]:
        """
        K=1时的系数计算
        估算位移 = 原始位移 * 1
        实际位移 = 原始位移 * K_new
        因此：K_new = 实际位移 / 估算位移
        """
        # 收集所有位移数据
        estimated_displacements = []
        actual_displacements = []
        
        for m in self.measurements:
            est_x, est_y = m['estimated']
            real_x, real_y = m['actual']
            
            # 计算相对于起始点的位移
            est_dx = est_x - self.start_x
            est_dy = est_y - self.start_y
            real_dx = real_x - self.start_x
            real_dy = real_y - self.start_y
            
            estimated_displacements.append((est_dx, est_dy))
            actual_displacements.append((real_dx, real_dy))
        
        # 使用最小二乘法
        # 对于X方向：real_dx = kx * est_dx
        # 对于Y方向：real_dy = ky * est_dy
        
        est_x_array = np.array([d[0] for d in estimated_displacements])
        est_y_array = np.array([d[1] for d in estimated_displacements])
        real_x_array = np.array([d[0] for d in actual_displacements])
        real_y_array = np.array([d[1] for d in actual_displacements])
        
        # 最小二乘法求解：kx = sum(est_x * real_x) / sum(est_x^2)
        kx = np.sum(est_x_array * real_x_array) / (np.sum(est_x_array ** 2) + 1e-10)
        ky = np.sum(est_y_array * real_y_array) / (np.sum(est_y_array ** 2) + 1e-10)
        
        return kx, ky
    
    def _calculate_iterative_coefficients(self) -> Tuple[float, float]:
        """
        K≠1时的系数计算
        估算位移 = 原始位移 * K_old
        实际位移 = 原始位移 * K_new
        因此：原始位移 = 估算位移 / K_old
              K_new = 实际位移 / 原始位移 = 实际位移 * K_old / 估算位移
        """
        estimated_displacements = []
        actual_displacements = []
        
        for m in self.measurements:
            est_x, est_y = m['estimated']
            real_x, real_y = m['actual']
            
            # 计算相对于起始点的位移
            est_dx = est_x - self.start_x
            est_dy = est_y - self.start_y
            real_dx = real_x - self.start_x
            real_dy = real_y - self.start_y
            
            # 反推原始位移
            raw_dx = est_dx / self.current_kx
            raw_dy = est_dy / self.current_ky
            
            estimated_displacements.append((raw_dx, raw_dy))
            actual_displacements.append((real_dx, real_dy))
        
        # 使用最小二乘法计算新系数
        est_x_array = np.array([d[0] for d in estimated_displacements])
        est_y_array = np.array([d[1] for d in estimated_displacements])
        real_x_array = np.array([d[0] for d in actual_displacements])
        real_y_array = np.array([d[1] for d in actual_displacements])
        
        kx = np.sum(est_x_array * real_x_array) / (np.sum(est_x_array ** 2) + 1e-10)
        ky = np.sum(est_y_array * real_y_array) / (np.sum(est_y_array ** 2) + 1e-10)
        
        return kx, ky
    
    def _calculate_errors(self, kx: float, ky: float, is_initial: bool) -> dict:
        """计算使用新系数后的误差统计"""
        errors_x = []
        errors_y = []
        
        for m in self.measurements:
            est_x, est_y = m['estimated']
            real_x, real_y = m['actual']
            
            est_dx = est_x - self.start_x
            est_dy = est_y - self.start_y
            real_dx = real_x - self.start_x
            real_dy = real_y - self.start_y
            
            if is_initial:
                # K=1时，原始位移就是估算位移
                corrected_dx = est_dx * kx
                corrected_dy = est_dy * ky
            else:
                # K≠1时，需要先反推原始位移
                raw_dx = est_dx / self.current_kx
                raw_dy = est_dy / self.current_ky
                corrected_dx = raw_dx * kx
                corrected_dy = raw_dy * ky
            
            errors_x.append(abs(corrected_dx - real_dx))
            errors_y.append(abs(corrected_dy - real_dy))
        
        return {
            'mean_x': np.mean(errors_x),
            'mean_y': np.mean(errors_y),
            'max_x': np.max(errors_x),
            'max_y': np.max(errors_y)
        }


def main():
    root = tk.Tk()
    app = OdometryCalibrationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
