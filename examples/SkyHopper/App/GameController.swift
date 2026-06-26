//
//  GameController.swift
//  SkyHopper (app layer)
//
//  The @Observable, @MainActor bridge between the pure `SkyHopperGame` simulation and the UI.
//  The model stays the single source of truth; the SpriteKit scene drives it each frame via
//  `advance(by:)` and the SwiftUI shell reads `phase`/`score`/`bestScore`.
//
//  NOTE: part of the iOS app target, NOT the SPM package. Add App/ to an Xcode app target that
//  links the SkyHopperCore library.
//
import Foundation
import SkyHopperCore

@MainActor
@Observable
final class GameController {
    private(set) var game: SkyHopperGame
    private(set) var bestScore = 0
    private var seed: UInt64

    init(seed: UInt64 = 1) {
        self.seed = seed
        self.game = SkyHopperGame(seed: seed)
    }

    var phase: RunPhase { game.phase }
    var score: Int { game.score }

    /// Tap intent — starts the run from `ready`, flaps while `playing`.
    func flap() { game.flap() }

    /// Advance the simulation by a clamped delta (called from the scene's update loop).
    func advance(by dt: Double) {
        game.step(by: dt)
        if game.score > bestScore { bestScore = game.score }
    }

    /// Start a fresh run with a new seed so obstacle layouts vary between attempts.
    func restart() {
        seed &+= 1
        game = SkyHopperGame(seed: seed)
        game.start()
    }
}
