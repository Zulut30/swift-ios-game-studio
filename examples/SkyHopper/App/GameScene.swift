//
//  GameScene.swift
//  SkyHopper (app layer)
//
//  A THIN SpriteKit renderer. It owns no game rules: each frame it advances the pure model by a
//  clamped dt and mirrors model state (player + obstacles) onto nodes. Obstacle bar nodes are
//  pooled by obstacle id and recycled — no per-frame allocation churn. Input (tap) becomes a
//  `flap()` intent; the model decides everything.
//
//  The scene's coordinate space equals the model's world (points), so model y maps directly to
//  SpriteKit's y-up space with no conversion.
//
import SpriteKit
import SkyHopperCore

final class GameScene: SKScene {
    weak var controller: GameController?
    private let tuning = Tuning()

    private let player = SKShapeNode(circleOfRadius: Tuning().playerRadius)
    private var barPool: [Int: (top: SKSpriteNode, bottom: SKSpriteNode)] = [:]
    private var lastUpdate: TimeInterval = 0

    init(size: CGSize, controller: GameController) {
        self.controller = controller
        super.init(size: size)
        scaleMode = .aspectFit
        anchorPoint = .zero
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("use init(size:controller:)") }

    override func didMove(to view: SKView) {
        backgroundColor = SKColor(red: 0.62, green: 0.80, blue: 0.95, alpha: 1)
        player.fillColor = .systemOrange
        player.strokeColor = .clear
        player.zPosition = 10
        player.isAccessibilityElement = true
        player.accessibilityLabel = "Player"
        addChild(player)
        #if DEBUG
        view.showsFPS = true
        view.showsNodeCount = true
        #endif
        syncNodes()
    }

    // MARK: Input

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        controller?.flap()
    }

    // MARK: Game loop — advance the model, then mirror it to nodes

    override func update(_ currentTime: TimeInterval) {
        guard let controller else { return }
        if lastUpdate == 0 { lastUpdate = currentTime }
        var dt = currentTime - lastUpdate
        lastUpdate = currentTime
        dt = min(dt, 1.0 / 30.0)  // clamp to survive stalls
        controller.advance(by: dt)
        syncNodes()
    }

    // MARK: Rendering

    private func syncNodes() {
        guard let game = controller?.game else { return }
        player.position = CGPoint(x: tuning.playerX, y: game.playerY)

        var live = Set<Int>()
        for obstacle in game.obstacles {
            live.insert(obstacle.id)
            let pair = barPool[obstacle.id] ?? makeBarPair(for: obstacle.id)
            layout(pair, for: obstacle)
        }
        // Recycle bars whose obstacle has scrolled away (pooling, no churn).
        for (id, pair) in barPool where !live.contains(id) {
            pair.top.removeFromParent()
            pair.bottom.removeFromParent()
            barPool[id] = nil
        }
    }

    private func makeBarPair(for id: Int) -> (top: SKSpriteNode, bottom: SKSpriteNode) {
        let color = SKColor(red: 0.20, green: 0.55, blue: 0.30, alpha: 1)
        let top = SKSpriteNode(color: color, size: .zero)
        let bottom = SKSpriteNode(color: color, size: .zero)
        for node in [top, bottom] {
            node.anchorPoint = CGPoint(x: 0.5, y: 0.5)
            addChild(node)
        }
        let pair = (top: top, bottom: bottom)
        barPool[id] = pair
        return pair
    }

    private func layout(_ pair: (top: SKSpriteNode, bottom: SKSpriteNode), for obstacle: Obstacle) {
        let w = tuning.obstacleWidth
        let centerX = obstacle.x + w / 2
        let gapTop = obstacle.gapCenterY + tuning.gapHeight / 2
        let gapBottom = obstacle.gapCenterY - tuning.gapHeight / 2

        let topHeight = max(0, tuning.worldHeight - gapTop)
        pair.top.size = CGSize(width: w, height: topHeight)
        pair.top.position = CGPoint(x: centerX, y: gapTop + topHeight / 2)

        let bottomHeight = max(0, gapBottom)
        pair.bottom.size = CGSize(width: w, height: bottomHeight)
        pair.bottom.position = CGPoint(x: centerX, y: bottomHeight / 2)
    }
}
