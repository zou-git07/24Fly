# GameController-RoboCup2025 使用手册

## 1. 项目简介

GameController-RoboCup2025 是为 RoboCup SPL 联赛设计的比赛控制与监控工具，支持比赛流程管理、事件记录、日志导出等功能。

## 2. 环境配置

### 2.1 基础环境
- 操作系统：推荐 Linux（也可在 Windows/Mac 下运行）
- Java 运行环境：JRE 8 或更高版本
- Ant 构建工具（如需源码编译）

### 2.2 安装依赖
1. 安装 Java：
   ```bash
   sudo apt update
   sudo apt install openjdk-11-jre
   # 或根据需要安装 openjdk-8-jre
   ```
2. （可选）安装 Ant：
   ```bash
   sudo apt install ant
   ```

## 3. 项目结构说明

- `GameController/`：主程序目录
  - `GameControllerTester.jar.bak`、`EventRecorder.jar.bak` 等：可执行 JAR 包
  - `config/`：配置文件与图标
  - `examples/`：示例代码（C、Python、插件等）
  - `plugins/`：插件目录
  - `scene/`：场景与资源文件
  - `tools/`：辅助工具脚本

## 4. 编译与运行

### 4.1 直接运行

项目已包含编译好的 JAR 包，可直接运行：

```bash
cd GameController
java -jar GameControllerTester.jar.bak
```

图形化界面

```bash
cd GameController
java -jar TeamCommunicationMonitor.jar.bak
```

如需运行其他工具，替换为对应 JAR 包名称。

### 4.2 源码编译

如需从源码编译：

```bash
cd GameController
ant
```
编译成功后，会生成新的 JAR 包。

## 5. 配置文件说明

- `config/TCM.cfg`：主配置文件
- `config/spl/teams.cfg`：队伍信息配置

可根据实际需求修改配置文件内容。

## 6. 插件与示例

- `examples/plugins/role-gesture-whistle/`：插件开发与示例
- `examples/python/`：Python 示例与协议实现

## 7. 常见问题

- **Java 版本不兼容**：请确保已安装 JRE 8 或更高版本。
- **端口占用**：如端口被占用，检查是否有其他实例在运行。
- **配置文件找不到**：请确保在 `GameController` 目录下运行。

## 8. 参考与支持

- 详细说明请参考 `README.md`、`TCM.md`。
- 如有问题可联系开发者或在 RoboCup 社区寻求帮助。
