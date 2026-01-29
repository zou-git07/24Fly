/**
 * @file RobotStateReporter.h
 * 
 * SimRobot 专用的机器人状态上报模块（最小实现）
 * 
 * 设计原则：
 * - 非阻塞：UDP 发送不阻塞控制循环
 * - 解耦：不依赖外部服务，发送失败时静默丢弃
 * - 轻量：CPU 开销 < 0.5%
 * 
 * @author RoboCup SPL Team
 */

#pragma once

#include "Framework/Module.h"
#include "Representations/Infrastructure/FrameInfo.h"
#include "Representations/Infrastructure/GameState.h"
#include "Representations/Infrastructure/RobotHealth.h"
#include "Representations/Infrastructure/DummyRepresentation.h"
#include "Representations/Modeling/BallModel.h"
#include "Representations/Modeling/RobotPose.h"
#include "Representations/MotionControl/MotionInfo.h"
#include "Representations/BehaviorControl/BehaviorStatus.h"
#include "Representations/Sensing/FallDownState.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <string>

MODULE(RobotStateReporter,
{,
  REQUIRES(FrameInfo),
  REQUIRES(GameState),
  REQUIRES(RobotHealth),
  USES(BallModel),
  USES(RobotPose),
  USES(MotionInfo),
  USES(BehaviorStatus),
  USES(FallDownState),
  
  PROVIDES(DummyRepresentation),
  
  LOADS_PARAMETERS(
  {,
    (bool)(true) enabled,                           // 是否启用监控
    (std::string)("127.0.0.1") monitorAddress,      // Monitor Daemon 地址
    (int)(10020) monitorPort,                       // UDP 端口
    (int)(10) reportIntervalFrames,                 // 上报间隔（帧数）
    (bool)(true) detectEvents,                      // 是否检测事件
  }),
});

class RobotStateReporter : public RobotStateReporterBase
{
private:
  int udpSocket = -1;
  struct sockaddr_in monitorAddr;
  unsigned lastReportFrame = 0;
  
  // 事件检测状态
  std::string lastBehavior;
  bool lastBallVisible = false;
  bool lastFallen = false;
  
  unsigned reportCount = 0;
  unsigned sendErrors = 0;
  
  void initSocket();
  void collectState(std::string& jsonBuffer);
  void sendState(const std::string& jsonBuffer);
  
public:
  RobotStateReporter();
  ~RobotStateReporter();
  
  void update(DummyRepresentation& dummy) override;
};
