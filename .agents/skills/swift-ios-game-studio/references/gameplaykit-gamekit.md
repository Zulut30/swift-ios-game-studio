# GameplayKit & GameKit (optional)

Two Apple frameworks you reach for only when they earn their place. **GameplayKit** structures
gameplay logic; **GameKit** adds Game Center (leaderboards/achievements/multiplayer). Both are
optional — a simple game ships without either. For kids' apps, GameKit needs special care.

---

## GameplayKit — structure for gameplay logic

Use the pieces that fit; ignore the rest. Everything here can live in the **pure model** layer
(no SpriteKit/SwiftUI imports), so it stays unit-testable.

### GKStateMachine — formal game states
An alternative to a hand-rolled `enum` state machine when transitions get complex (per-state
enter/exit logic, many states). For simple games a plain enum is usually enough.

```swift
import GameplayKit

final class PlayingState: GKState {
    override func isValidNextState(_ stateClass: AnyClass) -> Bool {
        stateClass == PausedState.self || stateClass == WonState.self || stateClass == LostState.self
    }
    override func didEnter(from previousState: GKState?) { /* resume systems */ }
    override func willExit(to nextState: GKState) { /* pause systems */ }
}

let machine = GKStateMachine(states: [MenuState(), PlayingState(), PausedState(), WonState(), LostState()])
machine.enter(PlayingState.self)
```
Rule of thumb: hand-rolled `enum` for ≤4 simple states; `GKStateMachine` when enter/exit hooks and
validation matter.

### GKRandomSource — deterministic randomness (recommended)
A first-class, seedable RNG. Equivalent to the skill's `SeededGenerator`, with handy distributions.
Prefer this (or `SeededGenerator`) over the global RNG so spawns/shuffles are testable.

```swift
let rng = GKMersenneTwisterRandomSource(seed: 42)
let die = GKRandomDistribution.d6(withSource: rng)   // 1...6, reproducible
let shuffled = rng.arrayByShufflingObjects(in: deck)
```

### GKEntity / GKComponent — ECS, if you need it
Component-based composition for entities with many shared behaviors. For most simple 2D games a
lightweight value-type "components" approach (see `references/swift/swift-protocols-generics.md`)
is simpler and stays value-typed. Reach for `GKEntity`/`GKComponent` only when an entity truly
needs many runtime-composed, reference-type systems.

### GKAgent / GKGoal — steering & simple AI
Autonomous movement (seek, flee, wander, avoid, flock). Useful for "enemies that chase" or ambient
critters. Overkill for puzzles/coloring/memory. Keep agent updates frame-rate-independent (`dt`).

### GKGraph / pathfinding
`GKGridGraph` / `GKObstacleGraph` for grid or polygon pathfinding (find a route around obstacles).
Use for maze/grid movement; not needed for static-board games.

### GKRuleSystem — fuzzy/declarative rules
Encode "if conditions then fact with weight" logic (e.g. difficulty adaptation). Niche; only when
you have genuinely rule-driven behavior worth externalizing.

### When to use GameplayKit at all
- ✅ Deterministic RNG (`GKRandomSource`) — almost always a good idea.
- ✅ Complex state machines, steering AI, or pathfinding that you'd otherwise write by hand.
- ❌ Simple turn-based/static games — a plain model + enum is smaller and clearer.

---

## GameKit (Game Center) — leaderboards, achievements, multiplayer

Adds online leaderboards, achievements, and matchmaking. **Optional and outward-facing** — treat
it as a feature with privacy and child-safety implications, not a default.

### Authentication
```swift
import GameKit
GKLocalPlayer.local.authenticateHandler = { viewController, error in
    if let vc = viewController { /* present sign-in */ }
    else if GKLocalPlayer.local.isAuthenticated { /* enable Game Center features */ }
    else { /* run offline; never block core play on sign-in */ }
}
```
- **Never gate core gameplay on Game Center sign-in.** Always playable offline.

### Leaderboards & achievements
```swift
try await GKLeaderboard.submitScore(score, context: 0, player: GKLocalPlayer.local,
                                    leaderboardIDs: ["best_time_level1"])
let a = GKAchievement(identifier: "first_win"); a.percentComplete = 100
try await GKAchievement.report([a])
```

### Child-safety & privacy rules for GameKit
- **Kids Category / under-13:** Apple restricts Game Center and external account features. Often
  you must **omit Game Center** entirely for a young-kids app, or put it behind a **parental gate**.
- Game Center is an Apple account feature → it involves identity/data. For a privacy-first kids app,
  the safe default is **no GameKit**: keep scores local (`UserDefaults`/Codable file).
- If you add it for an older audience: make it **opt-in**, never show other players' data to a child,
  no chat/UGC without moderation, and update `PrivacyInfo.xcprivacy` honestly.
- Multiplayer adds matchmaking, latency, and moderation concerns far beyond a simple game's scope —
  only with a strong, stated reason.

### Decision
- Default for kids: **local scores, no GameKit.**
- Older/general audience: GameKit is fine as an **optional, opt-in** layer behind a parental gate,
  with accurate privacy disclosure. Never a core dependency.

---

## Testing
- `GKRandomSource` with a fixed seed → deterministic, assertable tests.
- Keep GameplayKit logic in the model so it's unit-tested without a simulator.
- GameKit calls are I/O — wrap them behind a protocol seam (`Persisting`/`Leaderboarding`) so tests
  inject a fake and never hit the network. See `references/swift/swift-protocols-generics.md`.
