# Swift mastery references

The language toolkit that makes the agent write **excellent** Swift for games. Read the file that
matches what you're writing; the SKILL.md workflow links here at the implement step.

| File | Read when you are… |
|---|---|
| [swift-language-essentials.md](swift-language-essentials.md) | writing any model/system: value vs reference types, optionals, enums, errors, collections, immutability, access control |
| [swift-api-design.md](swift-api-design.md) | naming a type/method/property; designing a public surface; making illegal states unrepresentable |
| [swift-protocols-generics.md](swift-protocols-generics.md) | adding seams (clock/RNG/persistence), reusable systems (pools), `some` vs `any`, conditional conformance |
| [swift-concurrency.md](swift-concurrency.md) | loading levels/assets, async work, actors, `@MainActor`, Swift 6 `Sendable`/strict concurrency |
| [swiftui-mastery.md](swiftui-mastery.md) | building menus/HUD/settings or a SwiftUI-only game: state, layout, animation, gestures, a11y, perf |
| [swift-memory-performance.md](swift-memory-performance.md) | tightening hot paths: ARC, retain cycles, COW, pooling, allocations, profiling |
| [swift-patterns-idioms.md](swift-patterns-idioms.md) | reaching for result builders, property wrappers, KeyPaths, Codable migration, seeded RNG, state machines |

## The Swift quality bar (apply to every file you write)
1. **Value types + single owner.** `struct`/`enum` for game state; `class` only for shared identity.
2. **Logic has no UI imports.** Models/rules are pure Swift; views/scenes are thin.
3. **Make illegal states unrepresentable.** Enums over contradictory booleans.
4. **No force-unwrap on external data.** `guard let`/`??`/throw instead.
5. **Names read as phrases** at the call site (Apple API Design Guidelines).
6. **Swift 6 strict concurrency clean.** Main-actor UI/state; `Sendable` value types; no `@unchecked`.
7. **No retain cycles.** `[weak self]` in closures/actions/tasks; `weak` delegates.
8. **Deterministic where tested.** Inject a seeded RNG/clock so tests are reproducible.
9. **Hot paths allocate nothing.** Pool objects; update HUD text only on change.
10. **Every interactive control is accessible.** Label/value/trait; Dynamic Type; Reduce Motion.
