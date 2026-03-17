#!/bin/bash

SCENE_NAME="SingleGoalKeeper"
OUTPUT_FILE="Config/Scenes/${SCENE_NAME}.ros3"

echo "Generating ${SCENE_NAME}.ros3..."

# 生成ROS3文件头部
cat > "$OUTPUT_FILE" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Simulation xmlns="http://www.b-human.de/ros3">
  
  <MetaData>
    <Name>SingleGoalKeeper</Name>
    <Description>Single goalkeeper training scenario</Description>
    <Version>1.0</Version>
    <CreatedBy>AutoGenerator</CreatedBy>
    <CreatedDate>$(date -I)</CreatedDate>
  </MetaData>
EOF

# 添加包含文件部分
cat >> "$OUTPUT_FILE" << 'EOF'
  
  <Includes>
    <Include file="Includes/NaoV6H25.rsi3"/>
    <Include file="Includes/Ball.rsi3"/>
    <Include file="Includes/Field2020.rsi3"/>
    <Include file="Includes/GoalKeeper.rsi3"/>
  </Includes>
EOF

# 添加场景定义
# ... (继续添加其他部分)

echo "Generated $OUTPUT_FILE successfully!"
