# Swift protocols & generics

Protocol-oriented design and generics keep game systems decoupled, reusable, and testable.
Use them to define seams (inject a renderer, a clock, an RNG) — not to over-abstract.

## Protocols define capability, not hierarchy
Prefer small protocols describing what a type can *do*. Compose them.

```swift
protocol Entity { var id: EntityID { get } }
protocol Positioned { var position: Vector2 { get set } }
protocol Collidable: Positioned { var radius: CGFloat { get } }

func collides(_ a: some Collidable, _ b: some Collidable) -> Bool {
    a.position.distance(to: b.position) < a.radius + b.radius
}
```

## Protocol-oriented systems (dependency injection seams)
Inject collaborators behind protocols so tests can substitute fakes. Classic game seams: clock,
RNG, persistence, audio.

```swift
protocol Clock { var now: TimeInterval { get } }
protocol Persisting { func save(_ p: Progress) throws; func load() -> Progress? }

final class GameController {
    private let clock: Clock
    private let store: Persisting
    init(clock: Clock, store: Persisting) { self.clock = clock; self.store = store }
}
// Tests inject a FakeClock and an in-memory store — no real time, no disk.
```

## Default implementations via extensions
Give protocols behavior; conformers override only what differs.

```swift
protocol Resettable { mutating func reset() }
extension Resettable where Self: DefaultInitializable { mutating func reset() { self = .init() } }
```

## Generics — write once, reuse with type safety
```swift
struct Pool<Element> {                 // object pool for runners/spawners
    private var free: [Element] = []
    private let make: () -> Element
    init(make: @escaping () -> Element) { self.make = make }
    mutating func obtain() -> Element { free.popLast() ?? make() }
    mutating func recycle(_ e: Element) { free.append(e) }
}
```

## Constraints & conditional conformance
Constrain generics to the capabilities you use; conform conditionally.

```swift
func nearest<T: Collidable>(to p: Vector2, in xs: [T]) -> T? {
    xs.min(by: { $0.position.distance(to: p) < $1.position.distance(to: p) })
}

extension Array: Resettable where Element: Resettable {
    mutating func reset() { for i in indices { self[i].reset() } }
}
```

## Associated types & primary associated types
```swift
protocol LevelSource {
    associatedtype Level
    func level(at index: Int) -> Level?
}
// Primary associated type enables `some LevelSource<LevelData>` constraints:
protocol Producer<Output> { associatedtype Output; func make() -> Output }
func build(_ p: some Producer<LevelData>) -> LevelData { p.make() }
```

## `some` vs `any` — opaque vs existential
- **`some P` (opaque):** one concrete type, known to the compiler — zero-cost, monomorphized.
  Default choice for parameters/returns: `func spawn() -> some Entity`.
- **`any P` (existential):** a box that can hold different concrete types at runtime — needed for
  **heterogeneous collections**, at a small dynamic-dispatch cost.

```swift
var entities: [any Entity] = [Player(), Coin(), Hazard()]   // mixed types -> any
func update(_ e: some Positioned) { /* single type -> some, cheaper */ }
```
Rule of thumb: `some` unless you must store mixed types together, then `any`.

## Protocol witnesses & performance
- Calls through `some` are statically dispatched (fast). Calls through `any` use a witness table
  (dynamic). In per-frame hot paths prefer `some`/concrete types; keep `any` for setup/config.

## When NOT to abstract
- Don't introduce a protocol for a single concrete type with no test seam — it's noise.
- Don't model an inheritance tree of entity classes; prefer composition (small protocols + structs,
  or an ECS-lite of components) which stays value-typed and testable.

## Equatable/Hashable/Comparable/Identifiable
Conform game value types to these to get free diffing, `Set`/`Dictionary` keys, sorting, and SwiftUI
`ForEach` identity:

```swift
struct Tile: Identifiable, Hashable { let id: Int; var kind: TileKind }
```
