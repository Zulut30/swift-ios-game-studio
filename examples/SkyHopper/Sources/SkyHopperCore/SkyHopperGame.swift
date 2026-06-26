//
//  SkyHopperGame.swift
//  SkyHopperCore
//
//  The pure, testable simulation for a lite endless runner (tap-to-flap through gaps).
//  No SpriteKit/SwiftUI: the model owns gravity, scrolling, spawning, collision, and scoring;
//  the SKScene only renders `player`/`obstacles` each frame and forwards `flap()`.
//
//  Frame-rate independence: advance with `step(by: dt)` using a clamped dt. Determinism: obstacle
//  gaps come from an injected seeded RNG, so a given (seed, dt-sequence) always replays identically.
//
import Foundation

public struct SkyHopperGame: Sendable {

    public private(set) var phase: RunPhase = .ready
    public private(set) var playerY: Double
    public private(set) var velocityY: Double = 0
    public private(set) var score: Int = 0
    public private(set) var obstacles: [Obstacle] = []
    /// Total obstacles spawned this run (monotonic; useful for stats and tests).
    public private(set) var spawnedCount: Int = 0

    public let tuning: Tuning

    private var rng: SeededGenerator
    private let seed: UInt64
    private var timeSinceSpawn: Double = 0
    private var nextObstacleID: Int = 0

    public init(seed: UInt64, tuning: Tuning = Tuning()) {
        self.seed = seed
        self.tuning = tuning
        self.rng = SeededGenerator(seed: seed)
        self.playerY = tuning.worldHeight / 2
    }

    public var isPlaying: Bool { phase == .playing }
    public var isGameOver: Bool { phase == .gameOver }

    /// Begin a fresh run (resets all state, keeps the original seed for reproducibility).
    public mutating func start() {
        rng = SeededGenerator(seed: seed)
        phase = .playing
        playerY = tuning.worldHeight / 2
        velocityY = 0
        score = 0
        obstacles.removeAll(keepingCapacity: true)
        timeSinceSpawn = 0
        nextObstacleID = 0
        spawnedCount = 0
    }

    /// Tap intent. From `ready` it starts the run; while `playing` it applies an upward impulse.
    public mutating func flap() {
        switch phase {
        case .ready:
            start()
            velocityY = tuning.flapImpulse
        case .playing:
            velocityY = tuning.flapImpulse
        case .gameOver:
            break  // require an explicit restart() from the UI
        }
    }

    /// Restart after a game over.
    public mutating func restart() { start() }

    /// Advance the simulation by `dt` seconds. Callers should clamp `dt` (e.g. <= 1/30).
    public mutating func step(by dt: Double) {
        guard phase == .playing, dt > 0 else { return }

        // 1. Integrate the player (semi-implicit Euler).
        velocityY += tuning.gravity * dt
        playerY += velocityY * dt

        // 2. Floor / ceiling ends the run.
        let r = tuning.playerRadius
        if playerY <= r {
            playerY = r
            endRun()
            return
        }
        if playerY >= tuning.worldHeight - r {
            playerY = tuning.worldHeight - r
            endRun()
            return
        }

        // 3. Scroll obstacles left.
        for i in obstacles.indices {
            obstacles[i].x -= tuning.scrollSpeed * dt
        }

        // 4. Spawn on a fixed cadence.
        timeSinceSpawn += dt
        while timeSinceSpawn >= tuning.spawnInterval {
            timeSinceSpawn -= tuning.spawnInterval
            spawnObstacle()
        }

        // 5. Recycle off-screen obstacles.
        obstacles.removeAll { $0.x + tuning.obstacleWidth < 0 }

        // 6. Score when an obstacle's right edge passes the player.
        for i in obstacles.indices where !obstacles[i].scored {
            if obstacles[i].x + tuning.obstacleWidth < tuning.playerX {
                obstacles[i].scored = true
                score += 1
            }
        }

        // 7. Collision -> game over.
        if obstacles.contains(where: { collides(with: $0) }) {
            endRun()
        }
    }

    // MARK: - Helpers

    private mutating func endRun() {
        velocityY = 0
        phase = .gameOver
    }

    private mutating func spawnObstacle() {
        let lower = tuning.gapHeight / 2 + tuning.edgeMargin
        let upper = tuning.worldHeight - tuning.gapHeight / 2 - tuning.edgeMargin
        let gapCenterY =
            upper > lower ? Double.random(in: lower...upper, using: &rng) : tuning.worldHeight / 2
        obstacles.append(
            Obstacle(id: nextObstacleID, x: tuning.worldWidth + tuning.obstacleWidth, gapCenterY: gapCenterY)
        )
        nextObstacleID += 1
        spawnedCount += 1
    }

    /// Circle (player) vs the two barrier rectangles of an obstacle.
    private func collides(with o: Obstacle) -> Bool {
        let px = tuning.playerX
        let py = playerY
        let r = tuning.playerRadius
        let left = o.x
        let right = o.x + tuning.obstacleWidth
        // Quick reject when the player is not horizontally overlapping the obstacle.
        guard px + r > left, px - r < right else { return false }
        let gapTop = o.gapCenterY + tuning.gapHeight / 2
        let gapBottom = o.gapCenterY - tuning.gapHeight / 2
        // Player passes only if its circle stays within the gap vertically.
        return (py + r > gapTop) || (py - r < gapBottom)
    }
}
