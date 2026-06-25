# iOS game architecture

How to structure a simple Swift game so it stays testable, adaptable, and small.

## Core principle: separate logic from rendering
Put all rules and mutable state in **plain Swift** with no `import SwiftUI` /
`import SpriteKit`. Rendering reads from the model and forwards input back to it. This makes
the model unit-testable without a simulator and lets you swap the renderer (SwiftUI ⇄ SpriteKit).

```
┌─────────────┐     intents/input      ┌──────────────────┐
│  View layer │ ─────────────────────► │   Game model     │  (pure Swift)
│ SwiftUI /   │ ◄───────────────────── │  state + rules   │
│ SpriteKit   │     observable state   │  state machine   │
└─────────────┘                        └──────────────────┘
```

## Layers
1. **Model** — value types where possible: `Board`, `Card`, `Piece`, `LevelData`, `Score`.
   Pure functions: `apply(move:) -> Result`, `isWin`, `isLose`, `legalMoves`.
2. **Game state machine** — explicit `enum GameState { case menu, playing, paused, won, lost }`
   plus a controller (an `@Observable` class or `ObservableObject`) that owns transitions.
   For SpriteKit, GameplayKit's `GKStateMachine` is optional — a plain enum is usually enough.
3. **Systems** — focused units: `InputSystem`, `SpawnSystem`, `ScoreSystem`, `CollisionSystem`,
   `AudioSystem`, `SaveSystem`. Each does one job and is independently testable where practical.
4. **View / Scene** — SwiftUI views or `SKScene` subclasses. Thin: bind to model, render,
   translate gestures/touches into model intents. No game rules here.
5. **Persistence** — small `Codable` save model written to `UserDefaults` or a JSON file in
   Application Support. Keep it versioned (`schemaVersion`) and tolerant of missing keys.

## Decision rule: SwiftUI vs SpriteKit vs Hybrid
| Need | Mode |
|---|---|
| Turn-based / static board, tap & drag, no per-frame motion | SwiftUI-only |
| Continuous motion, physics, collisions, particles, many sprites | SpriteKit |
| Action gameplay **and** rich menus/HUD/settings/transitions | Hybrid (`SpriteView` in SwiftUI shell) |

When unsure, prefer the simpler mode that still delivers the core loop at 60 fps.

## Recommended folder layout
```
GameName/
├─ App/                 // @main App, root view, app-level config
├─ Models/              // pure Swift: rules, entities, level data, save model
├─ Systems/             // input, spawn, score, collision, audio, save
├─ Scenes/              // SKScene subclasses (SpriteKit / hybrid only)
├─ Views/               // SwiftUI views: menu, HUD, settings, game container
├─ Resources/           // Assets.xcassets, level JSON, sounds (user-provided/placeholder)
└─ Tests/               // unit tests for Models + Systems
```

## State & observation
- Modern: mark the controller `@Observable` (Observation framework, iOS 17+) and read it in
  views directly. Older targets: `ObservableObject` + `@Published` + `@StateObject`.
- Keep a single source of truth for game state. Views derive from it; they don't fork it.
- Drive SpriteKit from the model in `update(_:)`; never let the scene hold authoritative rules.

## Time and the loop
- SpriteKit calls `update(_ currentTime:)` each frame — compute `dt` from the previous time,
  clamp it (e.g. ≤ 1/30) to survive stalls, and advance systems by `dt`.
- SwiftUI continuous animation: use `TimelineView(.animation)` or a `CADisplayLink`-backed
  driver only when you truly need per-frame updates; otherwise prefer state + `withAnimation`.

## Input
- SwiftUI: gestures (`TapGesture`, `DragGesture`) → translate to model intents.
- SpriteKit: `touchesBegan/Moved/Ended` or `UIGestureRecognizer` on the view → intents.
- Normalize coordinates and keep hit-testing in the scene/view; keep the verdict (legal? scored?)
  in the model.

See `swiftui-spritekit-patterns.md` for concrete interop and loop code.
