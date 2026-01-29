/**
 * @file RobotStateReporter.cpp
 * 
 * 机器人状态上报模块实现
 */

#include "RobotStateReporter.h"
#include "Platform/BHAssert.h"
#include <fcntl.h>
#include <unistd.h>
#include <cstring>
#include <errno.h>

MAKE_MODULE(RobotStateReporter, infrastructure);

RobotStateReporter::RobotStateReporter()
{
  if(enabled)
    initSocket();
}

RobotStateReporter::~RobotStateReporter()
{
  if(udpSocket >= 0)
    close(udpSocket);
}

void RobotStateReporter::initSocket()
{
  // 创建 UDP socket
  udpSocket = socket(AF_INET, SOCK_DGRAM, 0);
  if(udpSocket < 0)
  {
    OUTPUT_ERROR("RobotStateReporter: Failed to create socket: " << strerror(errno));
    enabled = false;
    return;
  }
  
  // 设置为非阻塞模式（关键：避免阻塞控制循环）
  int flags = fcntl(udpSocket, F_GETFL, 0);
  if(flags < 0 || fcntl(udpSocket, F_SETFL, flags | O_NONBLOCK) < 0)
  {
    OUTPUT_ERROR("RobotStateReporter: Failed to set non-blocking mode");
    close(udpSocket);
    udpSocket = -1;
    enabled = false;
    return;
  }
  
  // 配置目标地址
  memset(&monitorAddr, 0, sizeof(monitorAddr));
  monitorAddr.sin_family = AF_INET;
  monitorAddr.sin_port = htons(monitorPort);
  
  if(inet_pton(AF_INET, monitorAddress.c_str(), &monitorAddr.sin_addr) <= 0)
  {
    OUTPUT_ERROR("RobotStateReporter: Invalid monitor address: " << monitorAddress);
    close(udpSocket);
    udpSocket = -1;
    enabled = false;
    return;
  }
  
  OUTPUT_TEXT("RobotStateReporter: Initialized, sending to " << monitorAddress << ":" << monitorPort);
}

void RobotStateReporter::update(RobotStateReporterOutput& output)
{
  output.isReporting = false;
  output.reportCount = reportCount;
  output.sendErrors = sendErrors;
  
  if(!enabled || udpSocket < 0)
    return;
  
  // 降频发送（避免过载）
  // 默认每 10 帧发送一次（30Hz -> 3Hz）
  if(theFrameInfo.time - lastReportTime < reportIntervalFrames * 33)  // 33ms per frame
    return;
  
  lastReportTime = theFrameInfo.time;
  
  // 采集状态
  bhuman::monitoring::RobotState state;
  collectState(state);
  
  // 检测事件
  if(detectEvents)
    this->detectEvents(state);
  
  // 发送
  sendState(state);
  
  output.isReporting = true;
  output.lastReportTime = theFrameInfo.time;
  output.reportCount = reportCount;
  output.sendErrors = sendErrors;
}

void RobotStateReporter::collectState(bhuman::monitoring::RobotState& state)
{
  // ===== 系统状态 =====
  auto* sys = state.mutable_system();
  sys->set_timestamp_ms(theFrameInfo.time);
  sys->set_frame_number(theFrameInfo.getFrameNumber());
  sys->set_cycle_time_ms(theFrameInfo.cycleTime);
  
  sys->set_battery_charge(theSystemSensorData.batteryLevel);
  sys->set_battery_current(theSystemSensorData.batteryCurrent);
  sys->set_cpu_temperature(theSystemSensorData.cpuTemperature);
  
  auto* orient = sys->mutable_orientation();
  orient->set_roll(theInertialData.angle.x());
  orient->set_pitch(theInertialData.angle.y());
  orient->set_yaw(theInertialData.angle.z());
  
  sys->set_is_upright(!theInertialData.fallen);
  sys->set_is_fallen(theInertialData.fallen);
  
  // ===== 感知状态 =====
  auto* perc = state.mutable_perception();
  
  // 球感知
  auto* ball = perc->mutable_ball();
  bool ballVisible = (theFrameInfo.time - theBallModel.timeWhenLastSeen) < 1000;  // 1秒内看到
  ball->set_visible(ballVisible);
  ball->set_pos_x(theBallModel.estimate.position.x());
  ball->set_pos_y(theBallModel.estimate.position.y());
  ball->set_last_seen_ms(theBallModel.timeWhenLastSeen);
  ball->set_velocity_x(theBallModel.estimate.velocity.x());
  ball->set_velocity_y(theBallModel.estimate.velocity.y());
  
  // 定位
  auto* loc = perc->mutable_localization();
  loc->set_pos_x(theRobotPose.translation.x());
  loc->set_pos_y(theRobotPose.translation.y());
  loc->set_rotation(theRobotPose.rotation);
  
  // 映射定位质量
  switch(theRobotPose.quality)
  {
    case RobotPose::superb:
      loc->set_quality(bhuman::monitoring::RobotState::PerceptionStatus::LocalizationInfo::SUPERB);
      break;
    case RobotPose::okay:
      loc->set_quality(bhuman::monitoring::RobotState::PerceptionStatus::LocalizationInfo::OKAY);
      break;
    default:
      loc->set_quality(bhuman::monitoring::RobotState::PerceptionStatus::LocalizationInfo::POOR);
      break;
  }
  
  // ===== 决策状态 =====
  auto* dec = state.mutable_decision();
  
  // 比赛状态
  switch(theGameControllerData.state)
  {
    case STATE_INITIAL:
      dec->set_game_state(bhuman::monitoring::RobotState::DecisionStatus::INITIAL);
      break;
    case STATE_READY:
      dec->set_game_state(bhuman::monitoring::RobotState::DecisionStatus::READY);
      break;
    case STATE_SET:
      dec->set_game_state(bhuman::monitoring::RobotState::DecisionStatus::SET);
      break;
    case STATE_PLAYING:
      dec->set_game_state(bhuman::monitoring::RobotState::DecisionStatus::PLAYING);
      break;
    case STATE_FINISHED:
      dec->set_game_state(bhuman::monitoring::RobotState::DecisionStatus::FINISHED);
      break;
  }
  
  dec->set_team_number(theGameControllerData.teamNumber);
  dec->set_player_number(theGameControllerData.playerNumber);
  dec->set_is_penalized(theGameControllerData.isPenalized());
  
  // 角色和行为（需要根据实际 B-Human 版本调整）
  dec->set_role(theStrategyStatus.role.getName());
  // dec->set_active_behavior(theStrategyStatus.activeBehavior);  // 如果有此字段
  
  // 运动请求
  switch(theMotionRequest.motion)
  {
    case MotionRequest::stand:
      dec->set_motion_type(bhuman::monitoring::RobotState::DecisionStatus::STAND);
      break;
    case MotionRequest::walk:
      dec->set_motion_type(bhuman::monitoring::RobotState::DecisionStatus::WALK);
      dec->set_walk_speed_x(theMotionRequest.walkSpeed.translation.x());
      dec->set_walk_speed_y(theMotionRequest.walkSpeed.translation.y());
      dec->set_walk_speed_rot(theMotionRequest.walkSpeed.rotation);
      break;
    case MotionRequest::kick:
      dec->set_motion_type(bhuman::monitoring::RobotState::DecisionStatus::KICK);
      break;
    case MotionRequest::getUp:
      dec->set_motion_type(bhuman::monitoring::RobotState::DecisionStatus::GET_UP);
      break;
    default:
      dec->set_motion_type(bhuman::monitoring::RobotState::DecisionStatus::SPECIAL);
      break;
  }
  
  // ===== 元数据 =====
  state.set_robot_id(
    std::to_string(theGameControllerData.teamNumber) + "_" + 
    std::to_string(theGameControllerData.playerNumber)
  );
}

void RobotStateReporter::detectEvents(bhuman::monitoring::RobotState& state)
{
  const auto& dec = state.decision();
  const auto& perc = state.perception();
  const auto& sys = state.system();
  
  // 行为切换
  std::string currentBehavior = dec.active_behavior();
  if(!currentBehavior.empty() && currentBehavior != lastBehavior && !lastBehavior.empty())
  {
    auto* event = state.add_events();
    event->set_type(bhuman::monitoring::RobotState::Event::BEHAVIOR_CHANGED);
    event->set_description("Behavior: " + lastBehavior + " -> " + currentBehavior);
    event->set_timestamp_ms(sys.timestamp_ms());
  }
  lastBehavior = currentBehavior;
  
  // 角色切换
  std::string currentRole = dec.role();
  if(currentRole != lastRole && !lastRole.empty())
  {
    auto* event = state.add_events();
    event->set_type(bhuman::monitoring::RobotState::Event::ROLE_CHANGED);
    event->set_description("Role: " + lastRole + " -> " + currentRole);
    event->set_timestamp_ms(sys.timestamp_ms());
  }
  lastRole = currentRole;
  
  // 球丢失/发现
  bool ballVisible = perc.ball().visible();
  if(ballVisible != lastBallVisible)
  {
    auto* event = state.add_events();
    event->set_type(ballVisible ? 
      bhuman::monitoring::RobotState::Event::BALL_FOUND :
      bhuman::monitoring::RobotState::Event::BALL_LOST);
    event->set_description(ballVisible ? "Ball found" : "Ball lost");
    event->set_timestamp_ms(sys.timestamp_ms());
  }
  lastBallVisible = ballVisible;
  
  // 摔倒/起身
  bool fallen = sys.is_fallen();
  if(fallen != lastFallen)
  {
    auto* event = state.add_events();
    event->set_type(fallen ? 
      bhuman::monitoring::RobotState::Event::FALLEN :
      bhuman::monitoring::RobotState::Event::GOT_UP);
    event->set_description(fallen ? "Robot fallen" : "Robot got up");
    event->set_timestamp_ms(sys.timestamp_ms());
  }
  lastFallen = fallen;
  
  // 处罚状态
  bool penalized = dec.is_penalized();
  if(penalized != lastPenalized)
  {
    auto* event = state.add_events();
    event->set_type(penalized ? 
      bhuman::monitoring::RobotState::Event::PENALIZED :
      bhuman::monitoring::RobotState::Event::UNPENALIZED);
    event->set_description(penalized ? "Robot penalized" : "Robot unpenalized");
    event->set_timestamp_ms(sys.timestamp_ms());
  }
  lastPenalized = penalized;
}

void RobotStateReporter::sendState(const bhuman::monitoring::RobotState& state)
{
  // 序列化为 Protobuf
  std::string buffer;
  if(!state.SerializeToString(&buffer))
  {
    OUTPUT_ERROR("RobotStateReporter: Failed to serialize state");
    sendErrors++;
    return;
  }
  
  // 发送（非阻塞）
  ssize_t sent = sendto(udpSocket, buffer.data(), buffer.size(), 0,
                        (struct sockaddr*)&monitorAddr, sizeof(monitorAddr));
  
  if(sent < 0)
  {
    // 非阻塞模式下，EAGAIN/EWOULDBLOCK 表示缓冲区满，这是正常的
    if(errno != EAGAIN && errno != EWOULDBLOCK)
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
