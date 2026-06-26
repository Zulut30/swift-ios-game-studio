# SkyHopper — SpriteKit + SwiftUI (hybrid) reference game

The companion to [MemoryMatch](../MemoryMatch/) (SwiftUI-only). SkyHopper is a lite endless runner
(tap-to-flap through gaps) that demonstrates the **hybrid** mode: SpriteKit gameplay hosted inside
a SwiftUI shell, with the same discipline — **all rules in a pure, tested core; rendering is thin.**

## What it demonstrates
- **Model owns the simulation.** `SkyHopperCore` computes gravity, scrolling, spawning, collision,
  and scoring in plain Swift (no SpriteKit/SwiftUI). It is unit-tested with `swift test`, no
  simulator. SpriteKit is a *renderer*, not the source of truth — there's no `SKPhysics` at all.
- **Frame-rate independence & determinism.** The scene advances the model by a clamped `dt`;
  obstacle gaps come from an injected seeded RNG, so a `(seed, dt-sequence)` replays identically
  (see `sameSeedAndInputsReplayIdentically`).
- **Thin SpriteKit scene.** `GameScene` mirrors model state onto nodes each frame and **pools**
  obstacle bars by id (no per-frame allocation/`addChild` churn). Tap → `flap()` intent.
- **SwiftUI shell.** `GameView` hosts the scene via `SpriteView` and overlays HUD / start prompt /
  game-over panel — real SwiftUI UI around SpriteKit gameplay.

## Layout
```
examples/SkyHopper/
├─ Package.swift                       # builds ONLY the pure core + tests (runs anywhere)
├─ Sources/SkyHopperCore/
│  ├─ SeededGenerator.swift            # deterministic RNG
│  ├─ Model.swift                      # RunPhase, Obstacle, Tuning (value types)
│  └─ SkyHopperGame.swift              # the simulation: gravity, spawn, collision, scoring
├─ Tests/SkyHopperCoreTests/
│  └─ SkyHopperGameTests.swift         # 10 deterministic Swift Testing tests
└─ App/                                # iOS UI — NOT compiled by SwiftPM (add to an Xcode target)
   ├─ SkyHopperApp.swift               # @main App
   ├─ GameController.swift             # @Observable @MainActor bridge to the model
   ├─ GameScene.swift                  # thin SpriteKit renderer (pooled nodes, clamped dt)
   └─ GameView.swift                   # SwiftUI shell: SpriteView + HUD + game over
```

## Run the core + tests
```bash
cd examples/SkyHopper
swift build      # compiles SkyHopperCore
swift test       # runs the 10 model tests
```
No Xcode or simulator needed — the payoff of keeping the simulation UI-free.

## Turn it into a runnable iOS app
Same recipe as MemoryMatch: create an Xcode iOS App, add this folder as a **local Swift package**
dependency, link **SkyHopperCore**, add the four files from `App/` to the app target (remove the
template `ContentView`/`@main`), then build & run. The `App/` files show "No such module
'SkyHopperCore'" in a plain editor until they're in a target that links the library — expected.

## Why two examples
- **MemoryMatch** = SwiftUI-only (static/turn-based) path.
- **SkyHopper** = SpriteKit + SwiftUI hybrid (continuous motion) path.
Together they cover both rendering modes the skill recommends, each proving the same architecture:
pure testable core, thin renderer, deterministic logic, accessible UI.
