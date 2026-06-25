# MemoryMatch — reference game

A complete, working example of the architecture the `swift-ios-game-studio` skill teaches:
**pure, testable game logic separated from rendering.** Copy this shape for new games.

## What it demonstrates
- A `MemoryMatch` memory/matching card game (template `memory-cards`), no-fail, kids-friendly.
- **Pure core** (`MemoryMatchCore`) with zero SwiftUI/SpriteKit imports → unit-tested with
  `swift test`, no simulator required.
- **Deterministic deal** via an injected seeded RNG (`SeededGenerator`) → reproducible tests.
- **Illegal states unrepresentable** (`CardState` enum, not contradictory booleans).
- **Thin SwiftUI layer** (`App/`): `@Observable` `@MainActor` controller, adaptive grid for
  iPhone/iPad, accessibility labels/values/traits, Reduce-Motion handling, win overlay.

## Layout
```
examples/MemoryMatch/
├─ Package.swift                 # builds ONLY the pure core + tests (runs anywhere)
├─ Sources/MemoryMatchCore/
│  ├─ SeededGenerator.swift      # deterministic RNG
│  ├─ Card.swift                 # Card + CardState (value types)
│  └─ MemoryGame.swift           # the rules: deal, choose, match, win  (single source of truth)
├─ Tests/MemoryMatchCoreTests/
│  └─ MemoryGameTests.swift      # 10 Swift Testing tests for the rules
└─ App/                          # iOS UI — NOT compiled by SwiftPM (add to an Xcode app target)
   ├─ MemoryMatchApp.swift       # @main App
   ├─ GameController.swift       # @Observable @MainActor bridge to the model
   ├─ GameView.swift             # adaptive board + HUD + win overlay
   └─ CardView.swift             # one accessible, flipping card
```

## Run the core + tests (works on any Mac with a Swift toolchain)
```bash
cd examples/MemoryMatch
swift build      # compiles MemoryMatchCore
swift test       # runs the 10 model tests
```
Expected: `Build complete!` and all tests pass. No Xcode project or simulator needed — that's the
payoff of keeping logic UI-free.

## Turn it into a runnable iOS app
The `App/` files are real iOS code but intentionally **outside** the SwiftPM targets (so `swift
test` stays fast and host-portable). To run the full game on a device/simulator:
1. In Xcode: **File ▸ New ▸ Project ▸ iOS App** (SwiftUI), name it `MemoryMatch`.
2. Add this package as a local dependency: **File ▸ Add Package Dependencies… ▸ Add Local…**,
   pick `examples/MemoryMatch`, and link the **MemoryMatchCore** library to the app target.
3. Add the four files from `App/` to the app target (delete the template `ContentView.swift`
   and the generated `@main` struct so `MemoryMatchApp` is the only entry point).
4. (Optional) Add `../../.agents/skills/swift-ios-game-studio/assets/PrivacyInfo.xcprivacy` to the
   app target for a privacy-first manifest.
5. Build & run on an iPhone/iPad simulator.

> Your editor may show "No such module 'MemoryMatchCore'" for files in `App/` until they're part
> of an Xcode target that links the library — expected, since SwiftPM doesn't compile `App/`.

## Why this structure
- The model is trivially testable and reusable; you could swap the SwiftUI view for a SpriteKit
  scene without touching a single rule.
- Determinism (seeded RNG) makes "random" behavior assertable in CI.
- The view is thin: it renders `cards`/`isWon` and forwards taps — no game rules leak into UI.
