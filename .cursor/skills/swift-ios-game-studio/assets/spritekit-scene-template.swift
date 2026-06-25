//
//  GameScene.swift  (template)
//  Swift iOS Game Studio — SpriteKit scene starter
//
//  A thin SKScene that renders a PURE game model and forwards input as intents.
//  Keep game rules in the model (no SpriteKit imports there) so they stay unit-testable.
//  Replace `GameModel` with your real model and adapt categories/nodes to your genre.
//

import SpriteKit
import GameplayKit // optional; remove if unused

// MARK: - Physics categories (adapt per game)

enum PhysicsCategory {
    static let none: UInt32   = 0
    static let player: UInt32 = 1 << 0
    static let ground: UInt32 = 1 << 1
    static let hazard: UInt32 = 1 << 2
    static let goal: UInt32   = 1 << 3
    static let coin: UInt32   = 1 << 4
}

// MARK: - Scene

final class GameScene: SKScene, SKPhysicsContactDelegate {

    /// Shared, observable controller the SwiftUI shell reads (score, state). Inject from the host.
    weak var controller: GameController?

    /// Pure, testable game model. Replace with your concrete type.
    private var model = GameModel()

    private var lastUpdate: TimeInterval = 0
    private let player = SKShapeNode(circleOfRadius: 22) // placeholder vector art

    // MARK: Lifecycle

    override func didMove(to view: SKView) {
        backgroundColor = SKColor(white: 0.96, alpha: 1)
        scaleMode = .resizeFill
        physicsWorld.gravity = CGVector(dx: 0, dy: -9.8)
        physicsWorld.contactDelegate = self

        setUpPlayer()
        setUpBoundsAndLevel()
        configureAccessibility()
    }

    private func setUpPlayer() {
        player.fillColor = .systemOrange
        player.strokeColor = .clear
        player.position = CGPoint(x: size.width * 0.2, y: size.height * 0.5)
        let body = SKPhysicsBody(circleOfRadius: 22)
        body.categoryBitMask = PhysicsCategory.player
        body.contactTestBitMask = PhysicsCategory.hazard | PhysicsCategory.goal | PhysicsCategory.coin
        body.collisionBitMask = PhysicsCategory.ground
        body.allowsRotation = false
        player.physicsBody = body
        addChild(player)
    }

    private func setUpBoundsAndLevel() {
        // Floor so the player doesn't fall forever. Replace with real level geometry.
        let floor = SKNode()
        floor.position = CGPoint(x: 0, y: 40)
        let floorBody = SKPhysicsBody(edgeFrom: .zero, to: CGPoint(x: size.width, y: 0))
        floorBody.categoryBitMask = PhysicsCategory.ground
        floor.physicsBody = floorBody
        addChild(floor)
    }

    private func configureAccessibility() {
        player.isAccessibilityElement = true
        player.accessibilityLabel = "Player"
    }

    // MARK: Input — translate touches into model intents

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard model.canAcceptInput else { return }
        // Example: tap to jump. The model decides legality; the scene applies the effect.
        if model.requestJump() {
            player.physicsBody?.applyImpulse(CGVector(dx: 0, dy: 90))
        }
    }

    // MARK: Game loop

    override func update(_ currentTime: TimeInterval) {
        if lastUpdate == 0 { lastUpdate = currentTime }
        var dt = currentTime - lastUpdate
        lastUpdate = currentTime
        dt = min(dt, 1.0 / 30.0) // clamp to survive stalls

        model.advance(by: dt)

        // Mirror authoritative model state to the SwiftUI-facing controller.
        controller?.score = model.score
        controller?.state = model.state

        if model.state == .won || model.state == .lost {
            isPaused = false // let win/lose UI handle transition; pause if you prefer
        }
    }

    // MARK: Contacts — record events; let the model decide outcomes

    func didBegin(_ contact: SKPhysicsContact) {
        let mask = contact.bodyA.categoryBitMask | contact.bodyB.categoryBitMask
        if mask & PhysicsCategory.goal != 0 {
            model.handleEvent(.reachedGoal)
        } else if mask & PhysicsCategory.hazard != 0 {
            model.handleEvent(.hitHazard)
        } else if mask & PhysicsCategory.coin != 0 {
            model.handleEvent(.collectedCoin)
            // remove the specific coin node here if you track it
        }
    }
}

// MARK: - Placeholder pure model (replace with your real, testable model)

enum GameState { case menu, playing, paused, won, lost }

struct GameModel {
    enum Event { case reachedGoal, hitHazard, collectedCoin }

    private(set) var state: GameState = .playing
    private(set) var score = 0
    var canAcceptInput: Bool { state == .playing }

    mutating func requestJump() -> Bool {
        // Gate on real ground-contact state in your implementation.
        return state == .playing
    }

    mutating func advance(by dt: TimeInterval) {
        // Advance timers, difficulty ramp, spawners, etc. Frame-rate independent via dt.
    }

    mutating func handleEvent(_ event: Event) {
        switch event {
        case .reachedGoal: state = .won
        case .hitHazard:   state = .lost
        case .collectedCoin: score += 1
        }
    }
}
