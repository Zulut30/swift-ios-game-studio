# Swift API design

Distilled from Apple's Swift API Design Guidelines, with game examples. Good names make game code
read like prose and cut comments. Apply these to every type, method, and property you add.

## Clarity at the point of use is the goal
Code is read far more than written. Optimize the **call site**, not the declaration.

```swift
board.flip(cardAt: 3)              // reads as a sentence
level.entities(ofKind: .coin)      // clear what comes back
player.move(by: .init(x: 1, y: 0)) // argument label carries meaning
```

## Naming
- **Types & protocols:** `UpperCamelCase`. Protocols describing a capability often end in
  `-able`/`-ing` (`Collidable`, `Resettable`, `Persisting`); protocols describing a thing are nouns
  (`Entity`, `LevelSource`).
- **Methods, properties, cases:** `lowerCamelCase`.
- **Booleans assert:** `isMatched`, `hasWon`, `canAcceptInput`, `isOnScreen`.
- **Non-mutating vs mutating verb pairs:** `sorted()`/`sort()`, `flipped()`/`flip()`. The mutating
  form is the imperative verb; the non-mutating form is the `-ed/-ing` participle.

## Argument labels
- First argument: include a label when it clarifies (`flip(cardAt:)`); omit when the name already
  says it (`contains(_:)`, `add(_:)`).
- Read the full call as a phrase: `place(piece, in: slot)`, `advance(by: dt)`,
  `spawn(_ kind: EntityKind, at: Vector2)`.
- Prepositions belong in labels: `move(to:)`, `move(by:)`, `damage(from:)`.

## Prefer methods/properties over free functions
- Behavior on a type belongs on the type. Free functions only for genuinely type-agnostic ops.
- Computed properties for cheap, side-effect-free derived values (`var isWin: Bool`).
- Methods for actions or anything non-trivial / side-effecting (`mutating func flip(...)`).

## Defaulted parameters over overloads
One method with sensible defaults beats five overloads.

```swift
func spawnCoin(at p: Vector2, value: Int = 1, animated: Bool = true) { ... }
```

## Make illegal states unrepresentable
Encode invariants in the type system so bad states can't compile:

```swift
// Instead of isFaceUp + isMatched booleans that can contradict:
enum CardState { case faceDown, faceUp, matched }
```

## Value-typed, immutable-by-default public surface
- Expose `let`/`private(set)` and computed reads; mutate through intent methods. Callers can't
  corrupt invariants.
- Return value types; let the caller decide ownership.

## Documentation comments
- Use `///` doc comments on public types/methods: a one-line summary, then `- Parameters:` /
  `- Returns:` / `- Throws:` when non-obvious. Keep them about *why/contract*, not restating code.

```swift
/// Flips the card at `id`, applying the two-up matching rule.
/// - Returns: `true` if the flip was accepted (board not locked, card face-down).
@discardableResult mutating func flip(cardAt id: Int) -> Bool { ... }
```

## Errors are part of the API
- Throw a documented domain error enum; name cases for the failure (`LevelError.notFound(id)`).
- Don't return sentinel values (`-1`, empty) to signal failure — throw or return optional/`Result`.

## Mutation & side effects are explicit
- `mutating` on structs, `@discardableResult` when ignoring the result is legitimate, `inout` only
  when truly needed (prefer returning new values). No hidden global state.

## Consistency beats novelty
- Mirror Apple's conventions (`count`, `isEmpty`, `first(where:)`, `map`, `contains`). A reader who
  knows the standard library should immediately understand your API.

## Quick review checklist for any new symbol
- [ ] Does the call site read as a clear phrase?
- [ ] Boolean reads as an assertion; verb pair correct (mutating vs non-mutating)?
- [ ] Labels carry prepositions/meaning; no redundant words?
- [ ] Could an illegal state be made unrepresentable instead of validated at runtime?
- [ ] Public surface is value-typed/immutable; mutation goes through intent methods?
- [ ] Failures throw a documented error (no sentinels)?
- [ ] One responsibility; consistent with the standard library?
