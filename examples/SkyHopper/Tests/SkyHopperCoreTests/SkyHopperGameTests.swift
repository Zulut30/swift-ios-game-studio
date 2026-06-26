//
//  SkyHopperGameTests.swift
//  SkyHopperCoreTests
//
//  Unit tests for the pure simulation. Deterministic via seeded spawns + fixed dt — no simulator.
//  Run: `swift test` from examples/SkyHopper.
//
import Testing

@testable import SkyHopperCore

private let dt = 1.0 / 120.0

// MARK: - Start / input

@Test func newGameStartsReadyAtCenter() {
    let game = SkyHopperGame(seed: 1)
    #expect(game.phase == .ready)
    #expect(game.score == 0)
    #expect(game.playerY == game.tuning.worldHeight / 2)
}

@Test func flapFromReadyStartsRunWithUpwardVelocity() {
    var game = SkyHopperGame(seed: 1)
    game.flap()
    #expect(game.phase == .playing)
    #expect(game.velocityY == game.tuning.flapImpulse)
}

@Test func gravityPullsThePlayerDownWhenNotFlapping() {
    var game = SkyHopperGame(seed: 1)
    game.start()
    let startY = game.playerY
    for _ in 0..<10 { game.step(by: dt) }
    #expect(game.playerY < startY)
    #expect(game.velocityY < 0)
}

@Test func flapReversesDownwardVelocity() {
    var game = SkyHopperGame(seed: 1)
    game.start()
    for _ in 0..<10 { game.step(by: dt) }  // build downward velocity
    #expect(game.velocityY < 0)
    game.flap()
    #expect(game.velocityY == game.tuning.flapImpulse)
    #expect(game.velocityY > 0)
}

// MARK: - Death

@Test func fallingIntoTheFloorEndsTheRun() {
    var game = SkyHopperGame(seed: 1)
    game.start()
    var steps = 0
    while game.phase == .playing && steps < 600 {
        game.step(by: dt)
        steps += 1
    }
    #expect(game.phase == .gameOver)
    #expect(game.playerY == game.tuning.playerRadius)  // clamped to the floor
}

@Test func stepDoesNothingAfterGameOver() {
    var game = SkyHopperGame(seed: 1)
    game.start()
    while game.phase == .playing { game.step(by: dt) }
    let frozen = game.playerY
    let scoreAtEnd = game.score
    game.step(by: dt)
    #expect(game.playerY == frozen)
    #expect(game.score == scoreAtEnd)
}

// MARK: - Determinism

@Test func sameSeedAndInputsReplayIdentically() {
    func run() -> (Double, Int, Int, RunPhase, [Double]) {
        var g = SkyHopperGame(seed: 777)
        g.start()
        for _ in 0..<600 {
            if g.playerY < g.tuning.worldHeight * 0.4 { g.flap() }  // hover so obstacles spawn
            g.step(by: dt)
        }
        return (g.playerY, g.score, g.spawnedCount, g.phase, g.obstacles.map(\.gapCenterY))
    }
    let a = run()
    let b = run()
    #expect(a.0 == b.0)
    #expect(a.1 == b.1)
    #expect(a.2 == b.2)
    #expect(a.3 == b.3)
    #expect(a.4 == b.4)
    #expect(a.2 > 0)  // obstacles actually spawned
}

@Test func differentSeedsProduceDifferentGaps() {
    func firstGap(seed: UInt64) -> Double {
        // No gravity/flap so the player can't die before the first obstacle spawns.
        var g = SkyHopperGame(seed: seed, tuning: Tuning(gravity: 0, flapImpulse: 0))
        g.start()
        var steps = 0
        while g.obstacles.isEmpty && steps < 2000 {
            g.step(by: dt)
            steps += 1
        }
        return g.obstacles.first?.gapCenterY ?? -1
    }
    #expect(firstGap(seed: 1) != firstGap(seed: 2))
}

// MARK: - Scoring

@Test func scoresEachPassedObstacleExactlyOnce() {
    // Gap forced to the world center (lower == upper) and no gravity, so the player sits in the
    // gap and never dies — isolating the scoring rule.
    let t = Tuning(gravity: 0, flapImpulse: 0, gapHeight: 300, edgeMargin: 200)
    var game = SkyHopperGame(seed: 1, tuning: t)
    game.start()
    for _ in 0..<1080 { game.step(by: dt) }  // 9.0s: obstacles spawn at 1.6,3.2,4.8,6.4 → score 4
    #expect(game.phase == .playing)
    #expect(game.score == 4)
}

// MARK: - Collision

@Test func collisionRuleMatchesGapAlignment() {
    let t = Tuning(gravity: 0, flapImpulse: 0, gapHeight: 120)
    var game = SkyHopperGame(seed: 12345, tuning: t)
    game.start()
    var steps = 0
    while game.obstacles.isEmpty && steps < 2000 {
        game.step(by: dt)
        steps += 1
    }
    let gap = try! #require(game.obstacles.first).gapCenterY
    let centerY = t.worldHeight / 2
    let r = t.playerRadius
    let half = t.gapHeight / 2
    let withinGap = (centerY + r <= gap + half) && (centerY - r >= gap - half)

    // Advance until obstacle 0 has passed the player or the run ends.
    while game.phase == .playing {
        if let o = game.obstacles.first(where: { $0.id == 0 }), o.scored { break }
        if game.obstacles.first(where: { $0.id == 0 }) == nil { break }
        game.step(by: dt)
        steps += 1
        if steps > 6000 { break }
    }
    if withinGap {
        #expect(game.phase == .playing)  // flew cleanly through the gap
    } else {
        #expect(game.phase == .gameOver)  // hit a barrier
    }
}
