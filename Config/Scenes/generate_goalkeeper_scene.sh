#!/bin/bash

SCENE_NAME="SingleGoalKeeper"
SCENE_DIR="Config/Scenes/$SCENE_NAME"

# 创建场景目录
mkdir -p "$SCENE_DIR"

# 生成主场景文件
cat > "$SCENE_DIR/$SCENE_NAME.ros2" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Simulation>
  <Include href="../Includes/NaoV6H25.rsi2"/>
  <Include href="../Includes/Ball.rsi2"/>
  <Include href="../Includes/Field2020.rsi2"/>
  
  <Scene name="SingleGoalKeeper" controller="SimulatedNao">
    <Field/>
    <Ball name="ball" x="0" y="0"/>
    <Robot name="GoalKeeper" playerNumber="1" teamNumber="1" 
           x="-4500" y="0" rotation="0" scenario="SingleGoalKeeper"/>
  </Scene>
</Simulation>
EOF

echo "Generated $SCENE_NAME.ros2"
