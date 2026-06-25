# Swift patterns & idioms

Reusable idioms that show up constantly in game code. Use them to keep code expressive and correct.

## Result builders (DSLs)
You already use one every day: SwiftUI's `body` is a `@ViewBuilder`. Reach for a custom result
builder only for a genuine mini-DSL (e.g. declaring a level or a sequence of actions).

```swift
@resultBuilder enum SequenceBuilder {
    static func buildBlock(_ steps: GameStep...) -> [GameStep] { steps }
}
func sequence(@SequenceBuilder _ make: () -> [GameStep]) -> [GameStep] { make() }
```

## Property wrappers
- Built-in: `@State`, `@Binding`, `@AppStorage`, `@Environment`.
- Custom wrappers for cross-cutting storage (e.g. a `@Clamped(0...1)` value). Keep them tiny and
  obvious; don't hide important logic inside a wrapper.

```swift
@propertyWrapper struct Clamped<T: Comparable> {
    private var value: T; let range: ClosedRange<T>
    init(wrappedValue: T, _ range: ClosedRange<T>) { self.range = range; value = min(max(wrappedValue, range.lowerBound), range.upperBound) }
    var wrappedValue: T { get { value } set { value = min(max(newValue, range.lowerBound), range.upperBound) } }
}
struct Tuning { @Clamped(0...1) var volume = 0.8 }
```

## KeyPaths
- Use `\Type.member` for generic, type-safe access — sorting, grouping, SwiftUI bindings.

```swift
let byScore = players.sorted(using: KeyPathComparator(\.score, order: .reverse))
let symbols = Dictionary(grouping: cards, by: \.symbol)
```

## Result & throwing bridges
- `Result<Success, Failure>` to store an outcome; `get()` to rethrow.
- `try?` to convert throw→optional, `try!` only for guaranteed invariants.

```swift
let outcome = Result { try loadLevel(id) }
level = (try? outcome.get()) ?? .fallback
```

## Codable patterns (levels & saves)
Default synthesized `Codable` covers most cases. For evolving formats:

```swift
struct SaveData: Codable {
    var schemaVersion: Int = 2
    var level: Int
    var bestTimes: [String: Double]

    enum CodingKeys: String, CodingKey { case schemaVersion, level, bestTimes }
    init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        schemaVersion = try c.decodeIfPresent(Int.self, forKey: .schemaVersion) ?? 1
        level = try c.decodeIfPresent(Int.self, forKey: .level) ?? 0     // tolerate missing keys
        bestTimes = try c.decodeIfPresent([String: Double].self, forKey: .bestTimes) ?? [:]
    }
}
// Migrate on load: if schemaVersion < current, transform then bump.
```

## Deterministic RNG (seedable) — essential for testable games
Inject a seeded `RandomNumberGenerator` so shuffles/spawns are reproducible in tests. A small
SplitMix64 is enough (the skill ships one as an asset: `assets/seeded-random.swift`).

```swift
struct SeededGenerator: RandomNumberGenerator {
    private var state: UInt64
    init(seed: UInt64) { state = seed == 0 ? 0x9E3779B97F4A7C15 : seed }
    mutating func next() -> UInt64 {
        state &+= 0x9E3779B97F4A7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        return z ^ (z >> 31)
    }
}
var rng = SeededGenerator(seed: 42)
cards.shuffle(using: &rng)                 // reproducible
let i = Int.random(in: 0..<cards.count, using: &rng)
```

## Small value types for geometry
Define a tiny `Vector2` for the model so it doesn't depend on CoreGraphics; convert at the edges.

```swift
struct Vector2: Equatable, Sendable {
    var x: Double, y: Double
    func distance(to o: Vector2) -> Double { (self - o).length }
    var length: Double { (x*x + y*y).squareRoot() }
    static func - (a: Vector2, b: Vector2) -> Vector2 { .init(x: a.x-b.x, y: a.y-b.y) }
}
```

## State machine as a pure function
Model transitions as `reduce(state, event) -> state`. Pure, exhaustive, trivially testable.

```swift
enum Phase { case menu, playing, paused, won, lost }
enum Event { case start, pause, resume, win, lose, reset }
func next(_ p: Phase, _ e: Event) -> Phase {
    switch (p, e) {
    case (_, .reset), (_, .start): return .playing
    case (.playing, .pause):       return .paused
    case (.paused, .resume):       return .playing
    case (.playing, .win):         return .won
    case (.playing, .lose):        return .lost
    default:                       return p
    }
}
```

## Extensions for clarity, not cleverness
- Group related helpers in focused extensions (`extension Board { /* queries */ }`).
- Add small conveniences (`Color(hex:)`, `CGPoint` math) but keep them discoverable and tested.

## Avoid these
- Force-unwrap (`!`) on external data; long `if`-pyramids (use `guard`); stringly-typed state
  (use enums); giant types (split by responsibility); premature protocols/abstractions.
