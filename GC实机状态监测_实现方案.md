# GC 实机实时状态监测功能 - 实现方案

## 📋 需求概述

在 GameController 界面中，为每个机器人按钮添加双击功能，双击后弹出详细的实时状态监测窗口，显示机器人的详细信息。

## 🏗️ 架构分析

### 当前系统架构
- **前端**: React + Tailwind CSS
- **后端**: Rust + Tauri
- **通信**: Tauri IPC + Event System
- **数据流**: 后端通过 `state` 事件推送状态到前端

### 现有连接状态机制
后端已经实现了完整的连接状态监测：
- `ConnectionStatus`: Offline(0) / Bad(1) / Good(2)
- 超时阈值: Good < 2s, Bad < 4s, Offline >= 4s
- 数据来源: `StatusMessage` (UDP 端口 3838)

## 🎯 实现方案

### 方案 1: 轻量级弹窗（推荐）

**优点**: 实现简单，不需要修改后端，复用现有数据
**适用场景**: 快速查看机器人基本状态

#### 前端实现

1. **创建状态监测组件** `RobotStatusModal.jsx`
```jsx
// 显示内容：
- 机器人编号和队伍
- 连接状态（Good/Bad/Offline）
- 当前惩罚状态
- 惩罚剩余时间
- 球衣颜色
- 是否为守门员
```

2. **修改 PlayerButton.jsx**
```jsx
// 添加双击事件处理
const handleDoubleClick = (e) => {
  e.stopPropagation(); // 防止触发单击
  onDoubleClick(player);
};

<button
  onClick={onClick}
  onDoubleClick={handleDoubleClick}
  ...
>
```

3. **修改 TeamPanel.jsx**
```jsx
// 添加状态管理
const [selectedRobot, setSelectedRobot] = useState(null);

// 传递双击处理函数
<PlayerButton
  onDoubleClick={(player) => setSelectedRobot(player)}
  ...
/>

// 渲染弹窗
{selectedRobot && (
  <RobotStatusModal
    player={selectedRobot}
    side={side}
    teamParams={teamParams}
    onClose={() => setSelectedRobot(null)}
  />
)}
```

### 方案 2: 完整状态监测（高级）

**优点**: 可显示更详细的网络信息和历史数据
**适用场景**: 需要深度调试和监控

#### 需要扩展的功能

1. **后端扩展** - 添加新的 Tauri 命令
```rust
// game_controller_app/src/lib.rs

#[tauri::command]
async fn get_robot_details(
    side: String,
    player_number: u8,
    state: State<'_, RuntimeStateHandle>
) -> Result<RobotDetails, String> {
    // 返回详细信息：
    // - IP 地址
    // - 最后消息时间
    // - 消息接收频率
    // - 电池电量（如果 StatusMessage 包含）
    // - 姿态信息（如果 StatusMessage 包含）
}
```

2. **扩展 StatusMessage 解析**
```rust
// 解析 StatusMessage 的更多字段
// 参考 SPL 协议规范
```

3. **前端调用**
```jsx
import { invoke } from "@tauri-apps/api/core";

const fetchRobotDetails = async () => {
  const details = await invoke("get_robot_details", {
    side: side,
    playerNumber: player.number
  });
  setRobotDetails(details);
};
```

## 📝 实现步骤（方案 1 - 推荐）

### Step 1: 创建状态监测弹窗组件

```bash
# 创建新文件
touch GameController3修改版/frontend/src/components/main/RobotStatusModal.jsx
```

### Step 2: 实现弹窗组件

关键功能：
- 显示机器人基本信息
- 连接状态可视化（颜色指示器）
- 惩罚信息展示
- 关闭按钮

### Step 3: 修改 PlayerButton 组件

添加：
- `onDoubleClick` prop
- 双击事件处理
- 防止事件冲突

### Step 4: 修改 TeamPanel 组件

添加：
- 弹窗状态管理
- 双击回调函数
- 弹窗渲染逻辑

### Step 5: 样式优化

使用 Tailwind CSS：
- 模态框背景遮罩
- 卡片样式
- 响应式布局
- 动画效果

## 🎨 UI 设计建议

### 弹窗布局
```
┌─────────────────────────────────┐
│  Robot #5 - Home Team      [×]  │
├─────────────────────────────────┤
│  Connection: ● Good             │
│  Jersey: Blue (Field Player)    │
│  Penalty: Ball Holding          │
│  Time Remaining: 00:25          │
│                                 │
│  [Close]                        │
└─────────────────────────────────┘
```

### 连接状态颜色
- Good: 绿色 ● (text-green-600)
- Bad: 黄色 ● (text-yellow-400)
- Offline: 红色 ● (text-red-600)

## 🔧 技术细节

### 事件处理优先级
```javascript
// 确保双击不触发单击
let clickTimer = null;

const handleClick = () => {
  clickTimer = setTimeout(() => {
    // 执行单击逻辑
  }, 200);
};

const handleDoubleClick = () => {
  clearTimeout(clickTimer);
  // 执行双击逻辑
};
```

### 数据流
```
StatusMessage (UDP) 
  → Backend (Rust)
  → AlivenessTimestampMap
  → ConnectionStatusMap
  → UiState (state event)
  → Frontend (React)
  → PlayerButton
  → RobotStatusModal
```

## 🧪 测试计划

1. **单元测试**
   - 双击事件不触发单击
   - 弹窗正确显示数据
   - 关闭功能正常

2. **集成测试**
   - 多个机器人同时监测
   - 连接状态实时更新
   - 不同惩罚状态显示

3. **真机测试**
   - 实际机器人连接
   - 状态变化响应
   - 性能影响评估

## 📦 文件清单

### 新增文件
- `frontend/src/components/main/RobotStatusModal.jsx`

### 修改文件
- `frontend/src/components/main/PlayerButton.jsx`
- `frontend/src/components/main/TeamPanel.jsx`

### 可选扩展（方案 2）
- `game_controller_app/src/lib.rs`
- `game_controller_runtime/src/robot_details.rs`

## 🚀 快速开始

```bash
# 1. 进入前端目录
cd GameController3修改版/frontend

# 2. 安装依赖（如果需要）
npm install

# 3. 开发模式运行
npm run dev

# 4. 在另一个终端构建后端
cd ..
cargo build --release

# 5. 运行 GameController
./run_gamecontroller.sh
```

## 📚 参考资料

- [Tauri 文档](https://tauri.app/v1/guides/)
- [React 事件处理](https://react.dev/learn/responding-to-events)
- [SPL GameController 协议](https://github.com/RoboCup-SPL/GameController3)
- 现有实现参考:
  - `connection_status.rs` - 连接状态逻辑
  - `PlayerButton.jsx` - 按钮组件
  - `api.js` - 前后端通信

## ⚠️ 注意事项

1. **性能考虑**
   - 弹窗不应阻塞主界面更新
   - 避免频繁的后端调用（方案 2）
   - 使用 React.memo 优化渲染

2. **用户体验**
   - 双击延迟不应影响单击操作
   - 弹窗应支持 ESC 键关闭
   - 点击遮罩层关闭弹窗

3. **兼容性**
   - 确保不影响现有的单击功能
   - 保持与现有 UI 风格一致
   - 支持键盘导航

## 🎯 下一步行动

1. ✅ 理解现有架构
2. ⬜ 实现 RobotStatusModal 组件
3. ⬜ 修改 PlayerButton 添加双击
4. ⬜ 修改 TeamPanel 集成弹窗
5. ⬜ 测试和调试
6. ⬜ 优化样式和动画
7. ⬜ 编写文档

---

**实现难度**: ⭐⭐☆☆☆ (中等偏易)
**预计时间**: 2-4 小时
**推荐方案**: 方案 1（轻量级弹窗）
