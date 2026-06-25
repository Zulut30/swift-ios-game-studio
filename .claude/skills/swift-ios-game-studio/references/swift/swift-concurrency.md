# Swift concurrency (async/await, actors, Swift 6 strict concurrency)

Games are mostly synchronous on the main thread, but loading, audio prep, and any I/O should be
concurrent and safe. Swift 6 enforces data-race safety at compile time — embrace it, don't fight it.

## Mental model
- **`async`/`await`** — suspendable functions; no callbacks, no completion handlers.
- **`Task`** — a unit of async work. `Task { }` inherits actor context; `Task.detached` does not.
- **Actors** — reference types that serialize access to their mutable state (no data races).
- **`@MainActor`** — isolates code to the main thread (all UI + most game state lives here).
- **`Sendable`** — a type safe to cross concurrency boundaries. Value types of `Sendable` members
  are automatically `Sendable`.

## The main rule for games
**Game state and UI run on `@MainActor`.** Keep the model, controller, scene, and views main-actor
isolated. Offload only genuinely independent work (decode a big level, prepare audio buffers) to a
background task, then hop back to the main actor to apply results.

```swift
@MainActor
@Observable
final class GameController {
    private(set) var level: LevelData?

    func loadLevel(_ id: String) {
        Task {                                  // runs on MainActor (inherited)
            let loaded = await Self.decode(id)  // hops off for the heavy work
            self.level = loaded                 // back on MainActor — safe to mutate
        }
    }

    // nonisolated + static so it can run off the main actor
    nonisolated static func decode(_ id: String) async -> LevelData {
        // pure, Sendable inputs/outputs; safe to run anywhere
        (try? LevelStore.load(id)) ?? .fallback
    }
}
```

## async/await basics
```swift
func preloadAssets() async throws {
    async let level = LevelStore.loadAsync("level_001")   // start concurrently
    async let audio = AudioBank.prepareAsync()
    self.level = try await level                          // await both
    self.audio = try await audio
}
```
- `async let` runs children concurrently and joins at `await`.
- `try await` combines error + suspension.

## Structured concurrency
- Prefer `async let` and `TaskGroup` over loose `Task {}` so work has a clear lifetime and cancels
  with its parent.

```swift
func loadAll(_ ids: [String]) async -> [LevelData] {
    await withTaskGroup(of: LevelData.self) { group in
        for id in ids { group.addTask { await Self.decode(id) } }
        var out: [LevelData] = []
        for await level in group { out.append(level) }
        return out
    }
}
```

## Actors for shared non-UI state
Use an actor when several tasks touch the same mutable state off the main actor (e.g. a download
cache, an analytics-free local stats store). UI/game state usually stays on `@MainActor` instead.

```swift
actor TextureCache {
    private var store: [String: Data] = [:]
    func data(for key: String) -> Data? { store[key] }
    func insert(_ data: Data, for key: String) { store[key] = data }
}
// await cache.insert(bytes, for: "atlas")   // calls into an actor are awaited
```

## Sendable & closures
- Make value-type models `Sendable` by conforming (often automatic). Mark game events/commands
  `Sendable` so they cross task boundaries cleanly.
- `@Sendable` closures capture only `Sendable` state. Avoid capturing a non-Sendable class.
- Swift 6 will *error* (not warn) on races. If you get a Sendable diagnostic, the fix is almost
  always: make the type a `Sendable` value type, or isolate the work to one actor — not `@unchecked`.

```swift
struct GameCommand: Sendable { let move: Move; let at: TimeInterval }
```

## Cancellation
- Cooperative: check `Task.isCancelled` / call `try Task.checkCancellation()` in long loops.
- Cancel a stored task on teardown (`task?.cancel()`), e.g. when leaving a level mid-load.

## Timers, animation, and the game loop
- For the **render loop**, use SpriteKit's `update(_:)` or SwiftUI `TimelineView(.animation)` —
  **not** async tasks (the loop must be frame-synced, not scheduled).
- For periodic *logic* (e.g. a once-per-second spawn outside SpriteKit), `AsyncTimerSequence`-style
  loops or `Task.sleep` are fine, but keep authoritative timing in the model via `dt`.

```swift
// One-shot delayed action without blocking:
Task { try? await Task.sleep(for: .seconds(0.6)); board.flipBackMismatched() }
```

## What NOT to do
- Don't reach for GCD (`DispatchQueue`) in new code — use `Task`/actors; they're checked.
- Don't sprinkle `@unchecked Sendable` to silence the compiler — fix the ownership instead.
- Don't mutate `@Observable`/UI state off the main actor.
- Don't run the game loop on a background queue; render and game state are main-actor concerns.
