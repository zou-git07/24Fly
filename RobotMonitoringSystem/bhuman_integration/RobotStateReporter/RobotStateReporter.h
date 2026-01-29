/**
 * @file RobotStateReporter.h
 * 
 * 机器人状态上报模块
 * 负责采集机器人状态并通过 UDP 发送到监控守护进程
 * 
 * 设计原则：
 * - 非阻塞：UDP 发送不阻塞控制循环
 * - 解耦：不依赖外部服务，发送失败时静默丢弃
 * - 轻量：CPU 开销 < 1%
 */

#pragma once

#include "Tools/Module/Module.h"
#include "Representations/Infrastructure/FrameInfo.h"
#include "Representations/Infrastructure/GameControllerData.h"
#include "Representations/Modeling/BallModel.h"
#include "Representations/Modeling/RobotPose.h"
#include "Representations/MotionControl/MotionRequest.h"
#include "Representations/BehaviorControl/StrategyStatus.h"
#include "Representations/Sensing/InertialData.h"
#include "Representations/Infrastructure/SensorData/SystemSensorData.h"
#include "robot_state.pb.h"  // Protobuf 生成的头文件

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <string>

MODULE(RobotStateReporter,
{,
  REQUIRES(FrameInfo),
  REQUIRES(GameControllerData),
  REQUIRES(BallModel),
  REQUIRES(RobotPose),
  REQUIRES(MotionRequest),
  REQUIRES(StrategyStatus),
  REQUIRES(InertialData),
  REQUIRES(SystemSensorData),
  // USES(ActivationGraph),  // 可选：用于获取行为激活状态
  
  PROVIDES(RobotStateReporterOutput),
  
  DEFINES_PARAMETERS(
  {,
    (bool)(true) enabled,                           // 是否启用监控
    (std::string)("239.0.0.1") monitorAddress,      // 监控守护进程地址（多播）
    (int)(10020) monitorPort,                       // 监控端口
    (int)(10) reportIntervalFrames,                 // 上报间隔（帧数）
    (bool)(true) detectEvents,                      // 是否检测事件
  }),
});

/**
 * RobotStateReporterOutput 表示
 * 用于其他模块查询监控状态
 */
STREAMABLE(RobotStateReporterOutput,
{
  void draw() const {},
  
  (bool)(false) isReporting,          // 是否正在上报
  (unsigned)(0) reportCount,          // 已上报次数
  (unsigned)(0) lastReportTime,       // 上次上报时间戳
  (unsigned)(0) sendErrors,           // 发送错误次数
});

class RobotStateReporter : public RobotStateReporterBase
{
private:
  int udpSocket = -1;
  struct sockaddr_in monitorAddr;
  unsigned lastReportFrame = 0;
  
  // 事件检测状态
  std::string lastBehavior;
  std::string lastRole;
  bool lastBallVisible = false;
  bool lastFallen = false;
  bool lastPenalized = false;
  
  unsigned reportCount = 0;
  unsigned sendErrors = 0;
  
  /**
   * 初始化 UDP socket
   * 设置为非阻塞模式
   */
  void initSocket();
  
  /**
   * 采集当前机器人状态
   * @param state 输出的状态数据
   */
  void collectState(bhuman::monitoring::RobotState& state);
  
  /**
   * 检测事件（行为切换、摔倒等）
   * @param state 状态数据（会添加事件到 events 字段）
   */
  void detectEvents(bhuman::monitoring::RobotState& state);
  
  /**
   * 发送状态数据到监控守护进程
   * @param state 状态数据
   */
  void sendState(const bhuman::monitoring::RobotState& state);
  
public:
  RobotStateReporter();
  ~RobotStateReporter();
  
  /**
   * 模块更新函数
   * 每帧调用一次
   */
  void update(RobotStateReporterOutput& output) override;
};
