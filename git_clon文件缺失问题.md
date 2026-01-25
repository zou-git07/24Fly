# 检查项目是否有子模块
cat .gitmodules  # 查看子模块配置

# 如果文件存在，需要额外步骤：
git submodule init   # 初始化子模块
git submodule update --recursive  # 拉取所有子模块
