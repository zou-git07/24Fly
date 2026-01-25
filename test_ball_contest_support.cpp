/**
 * @file test_ball_contest_support.cpp
 *
 * Simple test to verify ball contest support implementation
 */

#include <iostream>
#include <vector>
#include "Src/Representations/BehaviorControl/BallContestStatus.h"

int main()
{
    std::cout << "Testing Ball Contest Support Implementation" << std::endl;
    
    // Create a simple test scenario
    BallContestStatus contestStatus;
    
    // Test ball position
    Vector2f ballPosition(1000.f, 500.f);
    
    // Test teammate positions
    std::vector<Vector2f> teammatePositions = {
        Vector2f(1050.f, 450.f),  // Close to ball (contestant)
        Vector2f(800.f, 600.f),   // Potential support
        Vector2f(-2000.f, 0.f),   // Defender
        Vector2f(-3000.f, 0.f)    // Goalkeeper area
    };
    
    // Test opponent positions (simplified)
    std::vector<Vector2f> opponentPositions = {
        Vector2f(1100.f, 500.f)   // Close to ball (opponent contestant)
    };
    
    // Update contest status
    contestStatus.update(ballPosition, teammatePositions, opponentPositions, 1000);
    
    std::cout << "Contest state: " << static_cast<int>(contestStatus.state) << std::endl;
    std::cout << "Should send support: " << (contestStatus.shouldSendSupport() ? "Yes" : "No") << std::endl;
    std::cout << "Defensive risk: " << contestStatus.defensiveRisk << std::endl;
    
    if(contestStatus.shouldSendSupport())
    {
        Vector2f supportPos = contestStatus.getSupportPosition();
        std::cout << "Support position: (" << supportPos.x() << ", " << supportPos.y() << ")" << std::endl;
    }
    
    std::cout << "Ball Contest Support test completed successfully!" << std::endl;
    return 0;
}