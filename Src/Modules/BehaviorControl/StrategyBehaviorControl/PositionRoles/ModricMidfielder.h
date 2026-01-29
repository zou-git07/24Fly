 /**
 * @file ModricMidfielder.h
 *
 * This file declares the ModricMidfielder role.
 * A specialized midfielder with Modric-style passing characteristics:
 * - Enhanced long-range passing vision
 * - Precise through-ball capabilities
 * - Calm decision making under pressure
 * - Dynamic positioning for optimal pass angles
 *
 * @author Generated for Modric-style gameplay
 */

#pragma once

#include "Midfielder.h"
#include "Tools/BehaviorControl/KickSelection.h"

class ModricMidfielder : public Midfielder
{
  STREAMABLE(Parameters,
  {,
    (float)(3500.f) visionRange, /**< Extended vision range for long passes */
    (float)(0.8f) longPassPreference, /**< Preference for long passes over short ones */
    (float)(2000.f) throughBallDistance, /**< Preferred distance for through balls */
    (float)(0.9f) pressureResistance, /**< Resistance to opponent pressure when making decisions */
    (float)(1500.f) optimalPassAngleRange, /**< Range for finding optimal pass angles */
    (float)(0.7f) creativityFactor, /**< Factor for creative/unexpected passes */
    (float)(800.f) quickPassThreshold, /**< Distance threshold for quick short passes */
    (float)(0.6f) backPassAvoidance, /**< Tendency to avoid backward passes */
    (float)(1200.f) switchPlayDistance, /**< Distance for switching play to opposite flank */
    (float)(0.85f) accuracyWeight, /**< Weight for pass accuracy in decision making */
    (float)(2500.f) deepPassDistance, /**< Distance for deep passes into opponent territory */
    (float)(0.75f) riskTolerance, /**< Tolerance for risky but potentially rewarding passes */
    (float)(0.7f) startThreshold, /**< The rating has to be at least this much better at the destination to start moving */
    (float)(0.3f) stopThreshold, /**< If the rating is not at least this much better at the destination stop moving */
  });

  void preProcess() override;

  //computes the rating for a given point with Modric-style considerations
  float rating(const Vector2f& pos) const override;

  /**
   * Evaluates potential pass targets with Modric-style vision and decision making
   * @param ballPos Current ball position
   * @return Rating for pass opportunities from this position
   */
  float evaluatePassOpportunities(const Vector2f& ballPos) const;

  /**
   * Calculates positioning bonus for creating passing lanes
   * @param pos Position to evaluate
   * @return Bonus rating for pass lane creation
   */
  float calculatePassLaneBonus(const Vector2f& pos) const;

  /**
   * Evaluates pressure from opponents and adjusts positioning accordingly
   * @param pos Position to evaluate
   * @return Rating adjustment based on opponent pressure
   */
  float evaluateOpponentPressure(const Vector2f& pos) const;

  Parameters p;
};