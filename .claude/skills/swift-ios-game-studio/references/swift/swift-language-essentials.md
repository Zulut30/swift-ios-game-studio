# Swift language essentials (Swift 6)

The core language toolkit for writing clean, correct game code. Targets Swift 6 with strict
concurrency. Examples are game-flavored. This is the baseline every model/system file should meet.

## Value vs reference types — default to value
- **`struct` / `enum` are value types** (copied on assignment, thread-friendly, no shared mutation).
  Default to them for game state: `Board`, `Card`, `Vector2`, `LevelData`, `Score`.
- **`class` is a reference type** (shared identity, ARC-managed). Use only when you need shared
  mutable identity or reference semantics: the game controller, a scene, a long-lived system.
- Value semantics + a single owner = predictable state and trivial unit tests.

```swift
struct Card: Equatable, Identifiable {        // value type, free Equatable/Hashable
    let id: Int
    let symbol: String
    var isFaceUp = false
    var isMatched = false
}
```

## Optionals — model "absence", never crash on it
- Use optionals to express "maybe no value"; unwrap deliberately.
- Prefer `guard let` for early exit, `if let` for local use, `??` for defaults, optional chaining `?.`.
- **Never** force-unwrap (`!`) game data you don't control (level files, user input, lookups).
  Force-unwrap only invariants you guarantee in code, and even then prefer `guard`.

```swift
guard let level = levels[id] else { return .invalid }   // early exit, no nesting
let title = level.name ?? "Untitled"
let firstCoin = entities.first(where: { $0.kind == .coin })?.position
```

## Enums with associated values & exhaustive switch
Model game states and events as enums; `switch` exhaustively (no `default` so the compiler forces
you to handle new cases).

```swift
enum GameState: Equatable { case menu, playing, paused, won(score: Int), lost }

enum Move { case flip(cardID: Int), restart, pause }

func reduce(_ state: GameState, _ move: Move) -> GameState {
    switch state {
    case .playing where move == .restart: return .playing
    case .paused:                         return .playing
    default:                              return state
    }
}
```

## Error handling — typed, recoverable, no silent failure
- Use `throws` + `Result` for recoverable failure (level decode, save/load). Reserve `fatalError`
  for truly-impossible programmer errors.
- Define a domain error enum; surface it, don't swallow it.

```swift
enum LevelError: Error { case notFound(String), badSchema(Int), corrupt }

func loadLevel(_ id: String) throws -> LevelData {
    guard let url = bundleURL(id) else { throw LevelError.notFound(id) }
    let data = try Data(contentsOf: url)
    return try JSONDecoder().decode(LevelData.self, from: data)
}

// Call site
do { level = try loadLevel("level_001") }
catch { log("level load failed: \(error)"); level = .fallback }
```

## Control flow that reads well
- `guard` for preconditions and early exit (keeps the happy path un-indented).
- `defer` for cleanup that must run on every exit.
- Pattern matching in `switch`/`if case`/`for case` to destructure.

```swift
for case let .coin(value) in tile.contents { score += value }
```

## Collections & functional transforms
- Prefer `map`/`filter`/`reduce`/`compactMap`/`first(where:)` over manual loops for clarity.
- Use `Set`/`Dictionary` for O(1) membership/lookups (matched cards, occupied slots).
- Be mindful of allocations in per-frame code (see swift-memory-performance.md) — clarity in the
  model, tightness in the hot loop.

```swift
let allMatched = cards.allSatisfy { $0.isMatched }
let openIndices = cards.indices.filter { !cards[$0].isMatched }
let symbols = Dictionary(grouping: cards, by: \.symbol)
```

## Immutability by default
- `let` everywhere you can; `var` only for genuine mutation. The compiler optimizes and reviewers
  trust `let`. Mutating methods on structs make intent explicit:

```swift
struct Board {
    private(set) var cards: [Card]
    mutating func flip(_ id: Int) { /* mutate self */ }
}
```

## Codable for all game data
- Conform level/save models to `Codable`; keep a `schemaVersion`; tolerate missing keys with
  defaults. See swift-patterns-idioms.md for custom coding & migration.

## Access control
- `private` by default; widen to `internal` only when another type (or `@testable` tests) needs it;
  `public` only for a real module boundary. `private(set)` exposes read, hides write.

## String & localization
- User-facing text goes through `String(localized:)` / `LocalizedStringKey`, never hardcoded for
  shipping. Keep gameplay identifiers (symbol names, keys) as non-localized constants.

## Style baseline (match Apple's API Design Guidelines)
- Types `UpperCamelCase`, members `lowerCamelCase`. Name for clarity at the call site.
- Booleans read as assertions: `isMatched`, `canAcceptInput`, `hasWon`.
- Methods read as phrases: `flip(cardAt:)`, `place(_:in:)`, `advance(by:)`.
- One responsibility per type/file. Small is good.
