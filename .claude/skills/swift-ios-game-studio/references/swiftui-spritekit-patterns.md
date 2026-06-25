# SwiftUI + SpriteKit patterns

Concrete interop, game-loop, and input patterns. Copyable snippets; adapt names to the project.

## Hosting SpriteKit inside SwiftUI
Use `SpriteView` to embed an `SKScene` in a SwiftUI hierarchy. The SwiftUI shell owns menus,
HUD, and settings; the scene owns gameplay.

```swift
import SwiftUI
import SpriteKit

struct GameContainerView: View {
    @State private var scene = GameScene(size: CGSize(width: 750, height: 1334))

    var body: some View {
        SpriteView(scene: scene, options: [.ignoresSiblingOrder])
            .ignoresSafeArea()
            .overlay(alignment: .top) { HUDView(score: scene.score) }
    }
}
```

- Create the scene once (`@State`), don't rebuild it on every redraw.
- Set `scene.scaleMode = .resizeFill` (fills, may crop) or `.aspectFit` (letterbox) in `didMove`.
- Use `.ignoresSiblingOrder` for performance; only drop it if z-order via add-order matters.

## Bridging scene → SwiftUI state
Expose observable properties on the scene or, better, route through a shared controller the
scene mutates and SwiftUI observes.

```swift
@Observable
final class GameController {
    var score = 0
    var state: GameState = .menu
}

final class GameScene: SKScene {
    var controller: GameController!
    override func update(_ currentTime: TimeInterval) {
        // advance pure model by dt, then mirror results to controller
    }
}
```

## The game loop (SpriteKit)
```swift
final class GameScene: SKScene {
    private var lastUpdate: TimeInterval = 0

    override func update(_ currentTime: TimeInterval) {
        if lastUpdate == 0 { lastUpdate = currentTime }
        var dt = currentTime - lastUpdate
        lastUpdate = currentTime
        dt = min(dt, 1.0 / 30.0)          // clamp to survive frame stalls
        model.advance(by: dt)              // pure logic
        render(from: model)                // mirror model → nodes
    }
}
```

## Physics (SpriteKit)
- Use category bitmasks for collision groups; set `contactDelegate = self` and implement
  `didBegin(_:)`. Keep the *decision* (did the player die? did we score?) in the model.
- Prefer `SKPhysicsBody(rectangleOf:)` / `(circleOfRadius:)` over per-pixel bodies for perf.
- Gravity, restitution, and friction belong to tuning data, not magic numbers in the scene.

```swift
enum Category: UInt32 { case player = 1, ground = 2, hazard = 4, coin = 8 }
```

## SwiftUI-only game loop (when you really need frames)
```swift
TimelineView(.animation) { timeline in
    Canvas { ctx, size in render(ctx, size, at: timeline.date) }
}
```
For most SwiftUI games (memory, matching, drag-drop) you do **not** need a per-frame loop —
use state changes + `withAnimation`.

## Input → intents
SwiftUI:
```swift
.gesture(DragGesture()
    .onChanged { controller.dragMoved(to: $0.location) }
    .onEnded   { controller.dragEnded(at: $0.location) })
```
SpriteKit:
```swift
override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
    guard let p = touches.first?.location(in: self) else { return }
    model.handleTap(at: p)   // model decides; scene reflects
}
```

## Drag-and-drop & snapping (SwiftUI)
- Track a `dragging: PieceID?` and an offset; on `onEnded`, ask the model for the nearest valid
  slot and snap (animate) or bounce back. Keep "is this placement valid" in the model.

## Adapting to iPhone & iPad
- Drive layout from a design canvas size and scale to the safe area; don't hardcode points.
- Use `GeometryReader` / size classes for SwiftUI; use `scene.scaleMode` + camera for SpriteKit.
- Support portrait and landscape; recompute layout on size change, never assume one orientation.

## Pausing
- On `scenePhase` → `.inactive`/`.background`, set `scene.isPaused = true` and pause audio.
- Pause the model clock too, so `dt` doesn't spike when returning to foreground.

## Audio
- Short SFX: `SKAction.playSoundFileNamed` (SpriteKit) or `AVAudioPlayer` (SwiftUI).
- Always provide a mute toggle; respect the silent switch for non-essential sound.
