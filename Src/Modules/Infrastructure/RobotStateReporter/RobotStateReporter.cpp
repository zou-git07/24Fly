/**
 * @file RobotStateReporter.cpp
 * 
 * SimRobot 专用的机器人状态上报模块实现
 */

#include "RobotStateReporter.h"
#include "Platform/BHAssert.h"
#include <fcntl.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <cstring>
#include <errno.h>
#include <sstream>
#include <iomanip>

MAKE_MODULE(RobotStateReporter);

RobotStateReporter::RobotStateReporter()
{
  if (enabled)
    initSocket();
}

RobotStateReporter::~RobotStateReporter()
{
  if (udpSocket >= 0)
    close(udpSocket);
}

void RobotStateReporter::initSocket()
{
  // 创建 UDP socket
  udpSocket = socket(AF_INET, SOCK_DGRAM, 0);
  if (udpSocket < 0)
  {
    OUTPUT_WARNING("RobotStateReporter: Failed to create socket: " << strerror(errno));
    enabled = false;
    return;
  }
  
  // 设置为非阻塞模式（关键：避免阻塞控制循环）
  int flags = fcntl(udpSocket, F_GETFL, 0);
  if (flags < 0 || fcntl(udpSocket, F_SETFL, flags | O_NONBLOCK) < 0)
  {
    OUTPUT_WARNING("RobotStateReporter: Failed to set non-blocking mode");
    close(udpSocket);
    udpSocket = -1;
    enabled = false;
    return;
  }
  
  // 设置发送超时（额外保险）
  struct timeval timeout;
  timeout.tv_sec = 0;
  timeout.tv_usec = 1000;  // 1ms
  setsockopt(udpSocket, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
  
  // 配置目标地址
  memset(&monitorAddr, 0, sizeof(monitorAddr));
  monitorAddr.sin_family = AF_INET;
  monitorAddr.sin_port = htons(monitorPort);
  
  if (inet_pton(AF_INET, monitorAddress.c_str(), &monitorAddr.sin_addr) <= 0)
  {
    OUTPUT_WARNING("RobotStateReporter: Invalid monitor address: " << monitorAddress);
    close(udpSocket);
    udpSocket = -1;
    enabled = false;
    return;
  }
  
  OUTPUT_TEXT("RobotStateReporter: Initialized, sending to " 
              << monitorAddress << ":" << monitorPort);
}

void RobotStateReporter::update(DummyRepresentation&)
{
  if (!enabled || udpSocket < 0)
    return;
  
  // 降频发送：每 N 帧发送一次（避免过载）
  // 使用时间戳而不是帧号
  static unsigned lastReportTime = 0;
  if (theFrameInfo.time - lastReportTime < static_cast<unsigned>(reportIntervalFrames * 33))  // 33ms per frame
    return;
  
  lastReportTime = theFrameInfo.time;
  
  // 采集状态
  std::string jsonBuffer;
  collectState(jsonBuffer);
  
  // 发送（非阻塞）
  sendState(jsonBuffer);
}

void RobotStateReporter::collectState(std::string& jsonBuffer)
{
  std::ostringstream json;
  json << std::fixed << std::setprecision(2);
  
  // ===== 机器人 ID =====
  std::string robotId = std::to_string(theGameState.ownTeam.number) + "_" + 
                        std::to_string(theGameState.playerNumber);
  
  // ===== 时间戳（仿真时间）=====
  unsigned timestamp = theFrameInfo.time;
  
  // ===== 电量和温度 =====
  // SimRobot 中是固定值，真机中是真实值
#ifdef TARGET_ROBOT
  float battery = theRobotHealth.batteryLevel;
  float temp = theRobotHealth.maxJointTemperatureStatus;
#else
  float battery = 100.0f;  // SimRobot 固定值
  float temp = 40.0f;      // SimRobot 固定值
#endif
  
  // ===== 摔倒状态 =====
  bool fallen = (theFallDownState.state != FallDownState::upright);
  
  // ===== 行为状态 =====
  std::string behavior = "unknown";  // 简化：不使用 activity
  
  // ===== 球感知 =====
  bool ballVisible = (theFrameInfo.time - theBallModel.timeWhenLastSeen) < 1000;  // 1秒内看到
  float ballX = theBallModel.estimate.position.x();
  float ballY = theBallModel.estimate.position.y();
  
  // ===== 定位 =====
  float posX = theRobotPose.translation.x();
  float posY = theRobotPose.translation.y();
  float rotation = theRobotPose.rotation;
  
  // ===== 运动状态 =====
  std::string motion = TypeRegistry::getEnumName(theMotionInfo.executedPhase);
  
  // ===== 构建 JSON =====
  json << "{"
       << "\"timestamp\":" << timestamp << ","
       << "\"robot_id\":\"" << robotId << "\","
       << "\"battery\":" << battery << ","
       << "\"temperature\":" << temp << ","
       << "\"fallen\":" << (fallen ? "true" : "false") << ","
       << "\"behavior\":\"" << behavior << "\","
       << "\"motion\":\"" << motion << "\","
       << "\"ball_visible\":" << (ballVisible ? "true" : "false") << ","
       << "\"ball_x\":" << ballX << ","
       << "\"ball_y\":" << ballY << ","
       << "\"pos_x\":" << posX << ","
       << "\"pos_y\":" << posY << ","
       << "\"rotation\":" << rotation;
  
  // ===== 事件检测 =====
  if (detectEvents)
  {
    json << ",\"events\":[";
    bool firstEvent = true;
    
    // 球丢失/发现
    if (ballVisible != lastBallVisible)
    {
      if (!firstEvent) json << ",";
      json << "{\"type\":\"" << (ballVisible ? "ball_found" : "ball_lost") << "\"}";
      firstEvent = false;
    }
    lastBallVisible = ballVisible;
    
    // 摔倒/起身
    if (fallen != lastFallen)
    {
      if (!firstEvent) json << ",";
      json << "{\"type\":\"" << (fallen ? "fallen" : "got_up") << "\"}";
      firstEvent = false;
    }
    lastFallen = fallen;
    
    json << "]";
  }
  
  json << "}";
  
  jsonBuffer = json.str();
}

void RobotStateReporter::sendState(const std::string& jsonBuffer)
{
  // 发送（非阻塞）
  ssize_t sent = sendto(udpSocket, jsonBuffer.c_str(), jsonBuffer.size(), 0,
                        (struct sockaddr*)&monitorAddr, sizeof(monitorAddr));
  
  if (sent < 0)
  {
    // 非阻塞模式下，EAGAIN/EWOULDBLOCK 表示缓冲区满，这是正常的
    if (errno != EAGAIN && errno != EWOULDBLOCK)
    {
      // 静默失败，不打印错误（避免日志洪水）
      sendErrors++;
    }
  }
  else
  {
    reportCount++;
  }
}
