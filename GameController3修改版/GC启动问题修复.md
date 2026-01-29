# GameController 启动问题修复

## 🐛 问题描述

GameController 启动后立即退出，错误信息：
```
Failed to setup app: error encountered during setup hook: 
a webview with label `main` already exists
```

## 🔍 问题原因

**重复创建窗口冲突**

在 Tauri 应用中，窗口被创建了两次：

1. **配置文件中**（`tauri.conf.json`）：
   ```json
   "windows": [
     {
       "title": "GameController",
       "width": 1400,
       "height": 900,
       ...
     }
   ]
   ```

2. **代码中**（`main.rs`）：
   ```rust
   WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
       .center()
       .inner_size(640.0, 480.0)
       ...
       .build()?;
   ```

Tauri 会自动为配置文件中的窗口创建一个名为 "main" 的 webview，然后代码又尝试创建同名的 webview，导致冲突。

## ✅ 解决方案

### 修改 `tauri.conf.json`

将窗口配置改为空数组，让代码完全控制窗口创建：

**修改前：**
```json
"windows": [
  {
    "title": "GameController",
    "width": 1400,
    "height": 900,
    "minWidth": 1000,
    "minHeight": 700,
    "resizable": true,
    "fullscreen": false,
    "decorations": true
  }
]
```

**修改后：**
```json
"windows": []
```

### 重新编译

```bash
cd GameController3修改版
cargo build --release
```

编译时间：约 18 秒

## 🎉 修复结果

- ✅ GameController 可以正常启动
- ✅ 窗口正常显示
- ✅ 不再出现 "webview already exists" 错误

## 📝 技术说明

### Tauri 窗口创建机制

Tauri 有两种创建窗口的方式：

1. **声明式**：在 `tauri.conf.json` 中配置
   - 自动创建，标签为 "main"
   - 适合简单应用

2. **编程式**：在代码中使用 `WebviewWindowBuilder`
   - 手动控制，可以自定义标签
   - 适合需要动态创建窗口的应用

**不能同时使用两种方式创建同名窗口！**

### 为什么选择编程式创建？

GameController 的代码中使用了编程式创建，可能是因为：
- 需要在启动时根据配置动态调整窗口大小
- 需要在 setup 阶段完成一些初始化后再创建窗口
- 更灵活的窗口控制

因此，我们保留代码中的创建方式，删除配置文件中的声明。

## 🔧 其他可能的解决方案

### 方案 2：删除代码中的窗口创建

如果想使用配置文件方式，可以：

1. 保留 `tauri.conf.json` 中的窗口配置
2. 删除 `main.rs` 中的 `WebviewWindowBuilder` 代码
3. 在配置文件中设置窗口属性

但这需要修改更多代码，不推荐。

## ⚠️ 注意事项

1. **每次修改 `tauri.conf.json` 后都需要重新编译**
2. **显卡驱动警告（nouveau）不影响程序运行**
3. **如果仍然无法启动，尝试清理缓存：**
   ```bash
   rm -rf ~/.local/share/game_controller_app
   rm -rf ~/.cache/game_controller_app
   ```

## 📊 当前状态

- ✅ 问题已修复
- ✅ GameController 正常运行（进程 145739）
- ✅ 可以与 SimRobot 和 Web Monitor 同时运行

---

**修复时间：** 2026-01-28 16:21
**修复方法：** 删除配置文件中的重复窗口定义
