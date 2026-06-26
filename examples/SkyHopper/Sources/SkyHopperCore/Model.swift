//
//  Model.swift
//  SkyHopperCore
//
//  Value-type building blocks for the simulation. No SpriteKit/SwiftUI imports — pure logic,
//  geometry in plain `Double` (the renderer converts to CGPoint at the edge).
//
import Foundation

/// The run state machine: tap to start, fly through gaps, one hit ends the run.
public enum RunPhase: Sendable, Equatable {
    case ready
    case playing
    case gameOver
}

/// One obstacle = a vertical pair of barriers with a gap centered at `gapCenterY`.
public struct Obstacle: Identifiable, Equatable, Sendable {
    public let id: Int
    /// Left edge x in world points; decreases as the world scrolls left.
    public internal(set) var x: Double
    public let gapCenterY: Double
    /// Whether the player has already passed (and scored) this obstacle.
    public internal(set) var scored: Bool

    public init(id: Int, x: Double, gapCenterY: Double, scored: Bool = false) {
        self.id = id
        self.x = x
        self.gapCenterY = gapCenterY
        self.scored = scored
    }
}

/// Tunable constants — data, not magic numbers. Hand these to `balance-economist` to tune.
public struct Tuning: Sendable {
    public var worldWidth: Double
    public var worldHeight: Double
    public var playerX: Double
    public var playerRadius: Double
    public var gravity: Double  // points/s^2 (negative = down)
    public var flapImpulse: Double  // points/s (upward velocity set on flap)
    public var scrollSpeed: Double  // points/s the world moves left
    public var gapHeight: Double
    public var obstacleWidth: Double
    public var spawnInterval: Double  // seconds between obstacles
    public var edgeMargin: Double  // keep gaps away from floor/ceiling

    public init(
        worldWidth: Double = 400,
        worldHeight: Double = 700,
        playerX: Double = 100,
        playerRadius: Double = 18,
        gravity: Double = -1600,
        flapImpulse: Double = 520,
        scrollSpeed: Double = 220,
        gapHeight: Double = 220,
        obstacleWidth: Double = 70,
        spawnInterval: Double = 1.6,
        edgeMargin: Double = 60
    ) {
        self.worldWidth = worldWidth
        self.worldHeight = worldHeight
        self.playerX = playerX
        self.playerRadius = playerRadius
        self.gravity = gravity
        self.flapImpulse = flapImpulse
        self.scrollSpeed = scrollSpeed
        self.gapHeight = gapHeight
        self.obstacleWidth = obstacleWidth
        self.spawnInterval = spawnInterval
        self.edgeMargin = edgeMargin
    }
}
