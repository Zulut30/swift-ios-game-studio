# Swift memory & performance

How Swift manages memory and how to write code that stays fast in a 60/120 fps game.
Pair with performance-checklist.md (engine-level) — this file is language-level.

## ARC & reference types
- Classes are reference-counted (ARC). Value types (struct/enum) are not — they're copied and
  freed deterministically. Default to value types to sidestep ARC overhead and cycles entirely.
- ARC retain/release has a cost in hot loops with many class instances; prefer structs for
  per-frame data (particles, tiles, vectors).

## Retain cycles — the #1 leak source
A cycle keeps objects alive forever. The usual culprits in games:
- **Closures capturing `self`** (callbacks, `SKAction`, `Task`, timers).
- **Parent ⇄ child class references** (scene ↔ controller, node ↔ owner).

Break with capture lists:
```swift
node.run(.run { [weak self] in self?.spawnCoin() })
audioTask = Task { [weak self] in await self?.preloadSounds() }
```
- **`weak`** — becomes `nil` when the target dies (use for delegate/parent back-references).
- **`unowned`** — assumes the target outlives the closure (faster, but crashes if wrong; use only
  when the lifetime relationship is guaranteed).
- Delegates are `weak var delegate:` by convention.

## Copy-on-write (COW)
- Swift's standard collections (`Array`, `Dictionary`, `Set`, `String`) are COW: copies are cheap
  until mutated. Passing arrays around is fine; mutating a shared copy triggers one real copy.
- Large custom value types copied frequently can be wrapped in a COW box if profiling shows it —
  but measure first; usually unnecessary.

## Allocation in hot paths
The render/update loop runs ~60–120×/sec. In it:
- **Don't allocate** new arrays/dictionaries/closures every frame. Hoist them out; reuse buffers.
- **Pool and recycle** transient objects (obstacles, coins, particles) instead of create/destroy.
- Avoid `String` formatting per frame (number-to-text); update HUD text only when it changes.
- Prefer `for` over chained `map/filter/reduce` **only** in proven hot loops — clarity elsewhere.

```swift
// Bad: allocates a closure + array each frame
let visible = entities.filter { $0.isOnScreen(camera) }   // every frame
// Better in a hot loop: iterate once, reuse a preallocated scratch buffer
scratch.removeAll(keepingCapacity: true)
for e in entities where e.isOnScreen(camera) { scratch.append(e) }
```

## Value semantics for safe, fast state
- Pure value-type model + single owner = no aliasing bugs, trivial to test, and the optimizer can
  stack-allocate and inline aggressively.
- Mark methods `mutating` to make state changes explicit; prefer returning new values for pure rules.

## Lazy & deferred work
- `lazy var` for expensive members computed on first use (an atlas, a parsed level).
- Defer non-essential setup off the launch path so the first frame ships fast.

## Inlining & generics
- Small, frequently-called helpers can be hinted `@inlinable`/`@inline(__always)` **only** in
  measured hot paths; usually let the optimizer decide. Generic code specializes well with `some`.

## Strings & Codable cost
- Decoding JSON levels is not free; do it once per level (cache parsed `LevelData`), off the main
  actor for big files (see swift-concurrency.md), then reuse.

## Memory footprint
- Right-size textures; release atlases/levels you're done with. Vector/placeholder art keeps
  texture memory tiny. Watch a long session for monotonic growth (a leak signal).

## Measure, don't guess
- Instruments: **Time Profiler** (CPU hotspots), **Allocations**/**Leaks** (growth & cycles),
  **Animation Hitches** / Core Animation FPS. SpriteKit debug overlays: `showsFPS`,
  `showsNodeCount`, `showsDrawCount`.
- Optimize the thing the profiler points at — micro-optimizing cold code wastes effort and hurts
  readability.

## Quick checklist
- [ ] Value types for per-frame data; classes only for shared identity.
- [ ] No `self`-capturing closures without `[weak self]`/`[unowned self]`.
- [ ] No allocations / string formatting in the update loop.
- [ ] Pools for spawned objects; HUD text updated only on change.
- [ ] Heavy decode/setup cached and/or off the main actor.
- [ ] Verified with Instruments on the oldest target device.
