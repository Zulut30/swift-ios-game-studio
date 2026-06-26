# SwiftData persistence

SwiftData (iOS 17+, `import SwiftData`) is the modern, Swift-native replacement for Core Data:
declare persistent types with `@Model`, store them in a `ModelContainer`, mutate them through a
`ModelContext`, and read them in SwiftUI with `@Query`. This file is about **where** it belongs in
a game: SwiftData lives at the **edge** as one persistence option, and the **pure logic core stays
value-typed and SwiftData-free**. The same logic-vs-rendering seam from `ios-game-architecture.md`
holds — `@Model` classes are framework-owned reference types, so they never enter `Models/` or the
state machine. They sit behind a `SaveStore`, and you map `@Model` ⇄ value type at that boundary.

See `ios-game-architecture.md` for the seam and the `Codable`/`UserDefaults` baseline, and
`apple-accounts-pay-and-data.md` for the on-device, no-tracking data posture.

> This is engineering guidance, not a compliance guarantee. "Local-only" means the code as written
> stores on device; verify the shipped configuration, entitlements, and privacy manifest match that
> claim (`apple-accounts-pay-and-data.md`) before release.

## When to use SwiftData (vs Codable file vs UserDefaults)

SwiftData is a **database** — it earns its weight only when you have many structured records you
query, sort, or relate, growing over time (a run history, per-level stars across hundreds of
levels, unlocked stickers, a local leaderboard). Most simple games don't need it. Pick the lightest
tool that fits.

| Shape of the data | Use | Why |
|---|---|---|
| A handful of settings (mute, last level, difficulty) | `UserDefaults` / `@AppStorage` | One line per key; no schema; ideal for tiny scalars |
| One save blob / a level pack loaded whole | `Codable` → JSON in Application Support | Simplest durable store; versionable with `schemaVersion`; trivial to test |
| Many records you query/sort/relate, growing over time | **SwiftData** | Indexed queries, relationships, live `@Query`, migrations |

**Rule of thumb:** lots of structured records + queries → SwiftData; a handful of settings →
UserDefaults/@AppStorage; one save blob → Codable. When unsure, start with a `Codable` file and
graduate to SwiftData only when querying or record count makes the file awkward. Don't add SwiftData
by reflex.

## Defining models with `@Model`

`@Model` is a macro on a **final class** (SwiftData stores reference types). Stored properties
become persistent columns automatically; mark derived state `@Transient`. Constrain identity so
re-saving the same logical record **updates** it instead of duplicating: `@Attribute(.unique)` for a
single property (iOS 17+), or — on **iOS 18+** only — the model-level `#Unique<Model>([\.a, \.b])`
for composite keys. This reference targets iOS 17, so the examples use `@Attribute(.unique)`.

```swift
// MARK: - Persistence Models (SwiftData)

import Foundation
import SwiftData

@Model
final class LevelProgress {
    @Attribute(.unique) var levelID: String  // one row per level (iOS 17+)
    var stars: Int
    var bestTimeSeconds: Double
    var updatedAt: Date

    // A level has many runs; deleting the level deletes its runs.
    @Relationship(deleteRule: .cascade, inverse: \RunRecord.level)
    var runs: [RunRecord] = []

    @Transient var isPerfect: Bool { stars == 3 }  // derived, never stored

    init(levelID: String, stars: Int = 0, bestTimeSeconds: Double = .infinity) {
        self.levelID = levelID
        self.stars = stars
        self.bestTimeSeconds = bestTimeSeconds
        self.updatedAt = .now
    }
}

@Model
final class RunRecord {
    var date: Date
    var durationSeconds: Double
    var score: Int
    var level: LevelProgress?  // inverse side of the relationship

    init(date: Date = .now, durationSeconds: Double, score: Int) {
        self.date = date
        self.durationSeconds = durationSeconds
        self.score = score
    }
}
```

- Supported types are the `Codable` value types you already use: `Int`, `Double`, `String`, `Bool`,
  `Date`, `UUID`, `Data`, raw/`Codable` enums, arrays of them, and small `Codable` structs stored
  inline.
- Always name the `inverse` on `@Relationship` — omitting it creates a duplicate implicit
  relationship. `.cascade` deletes children with the parent; `.nullify` (default) only clears the
  link, which orphans children if you meant cascade.

## Container and context

Build one `ModelContainer` for the app and inject it with `.modelContainer(...)`. Configure it
**local-only** — `cloudKitDatabase: .none`, no sync — to honor the kids-safe, on-device rule.
`isStoredInMemoryOnly: true` makes a throwaway store for tests and previews.

```swift
// MARK: - App Entry

import SwiftData
import SwiftUI

@main
struct PuzzleGameApp: App {
    let container: ModelContainer = {
        let schema = Schema([LevelProgress.self, RunRecord.self])
        let config = ModelConfiguration(
            schema: schema,
            isStoredInMemoryOnly: false,
            cloudKitDatabase: .none  // on-device only, no account, no off-device sync
        )
        do {
            return try ModelContainer(for: schema, configurations: config)
        } catch {
            // Persisted data: never force-unwrap. Fail loud in dev so the cause is visible.
            fatalError("Could not create ModelContainer: \(error)")
        }
    }()

    var body: some Scene {
        WindowGroup { RootView() }
            .modelContainer(container)
    }
}
```

The `ModelContext` is the unit of work: it tracks inserts, edits, and deletes, then flushes them on
`save()`. The container's `mainContext` is bound to `@MainActor`; views read it via
`@Environment(\.modelContext)`. **A `ModelContext` is bound to the actor/thread that created it** —
even though current SDKs mark it `@unchecked Sendable`, never share one context across actors; give
each actor its own context. Only `ModelContainer` is safely `Sendable` and crosses actors.

## Reading with `@Query`

`@Query` fetches live results inside a `View` and re-renders when the store changes — no manual
reload. It exists **only** inside SwiftUI; outside it, use `context.fetch(_:)`. Filter with
`#Predicate`, order with `SortDescriptor`s.

```swift
// MARK: - Progress List View

import SwiftData
import SwiftUI

struct ProgressListView: View {
    @Query(sort: \LevelProgress.updatedAt, order: .reverse)
    private var levels: [LevelProgress]

    @Query(
        filter: #Predicate<LevelProgress> { $0.stars > 0 },
        sort: \LevelProgress.levelID
    )
    private var completed: [LevelProgress]

    var body: some View {
        List(levels) { level in
            LabeledContent(level.levelID, value: "\(level.stars)★")
        }
    }
}
```

## Insert / fetch / update / delete / save

Outside SwiftUI (a `SaveStore`, a coordinator, a test) drive the context directly. `insert` stages a
new object, mutating a stored property stages an edit, `delete` stages a removal, and `save()`
commits. `fetch(_:)` runs a one-shot query with a `FetchDescriptor`. **Inserts/edits/deletes only
stage — you must `save()`.** Guard with `hasChanges`, wrap in `do/catch`, never force-`try`.

```swift
// MARK: - SaveSystem (SwiftData seam)

import Foundation
import SwiftData

@MainActor
struct SaveSystem {
    let context: ModelContext

    // Upsert a level result; @Attribute(.unique) keeps it to one row per levelID.
    func recordResult(levelID: String, stars: Int, time: Double, score: Int) {
        let existing = fetchLevel(levelID)
        let level = existing ?? LevelProgress(levelID: levelID)
        level.stars = max(level.stars, stars)
        level.bestTimeSeconds = min(level.bestTimeSeconds, time)
        level.updatedAt = .now
        level.runs.append(RunRecord(durationSeconds: time, score: score))
        if existing == nil { context.insert(level) }  // insert only the new one
        commit()
    }

    func fetchLevel(_ id: String) -> LevelProgress? {
        var descriptor = FetchDescriptor<LevelProgress>(
            predicate: #Predicate { $0.levelID == id }
        )
        descriptor.fetchLimit = 1
        return (try? context.fetch(descriptor))?.first  // tolerate fetch failure
    }

    func resetProgress() {
        try? context.delete(model: LevelProgress.self)  // bulk delete by type (iOS 17+)
        commit()
    }

    private func commit() {
        guard context.hasChanges else { return }
        do {
            try context.save()
        } catch {
            // Surface to telemetry-free logging; never crash on a save failure in prod.
            assertionFailure("SwiftData save failed: \(error)")
        }
    }
}
```

## Keep `@Model` out of the pure core — map at the seam

`@Model` classes are **persistence types**, not game types: reference-typed, context-bound, not
`Sendable`, with hidden lifecycle (faulting, change tracking, autosave). They must not leak into the
pure Swift model that holds your rules. **Map at the boundary** — convert `@Model` ⇄ a value-type DTO
inside the `SaveStore`, and let the core see only the DTO.

```swift
// MARK: - Value <-> Model mapping (the seam)

// Pure value type the core uses — no SwiftData import here.
struct LevelStat: Equatable, Sendable {
    let levelID: String
    let stars: Int
    let bestTimeSeconds: Double
}

extension LevelProgress {
    /// Project the persistent model down to a pure value the core can use.
    func toValue() -> LevelStat {
        LevelStat(levelID: levelID, stars: stars, bestTimeSeconds: bestTimeSeconds)
    }
}
```

Why the copy is worth it:

- **The core stays `Sendable` and pure** — it unit-tests with no container or simulator, and you can
  swap the backend (JSON file, `UserDefaults`) without touching game rules.
- **No accidental writes** — a live `@Model` mutated deep in game logic would autosave silently;
  mapping makes every persistence write an explicit call through the seam.
- **Determinism** — tests feed and assert value types; SwiftData's faulting, ordering, and autosave
  never enter a logic test.

Never return a `@Model` from a store method, store one on the `@Observable` controller, or compare
records by reference in rules — map to the value type first.

## Threading

- **UI / game state → the main-actor context.** The container's `mainContext` is `@MainActor`; the
  `SaveStore` the controller talks to is `@MainActor` and uses it. Right for the small reads/writes a
  simple game does (load progress, save a best time).
- **Background work → its own context, never the main one shared.** For a bulk import or migration,
  do it off the main actor with a context created **from the container** there, or a `@ModelActor`
  (which owns its own context). Hand results back across the boundary as **value types**. Never
  capture a `ModelContext` in a `Task` or pass one to another actor — only the `ModelContainer`
  crosses.

```swift
// MARK: - Bulk import isolated in a @ModelActor

import Foundation
import SwiftData

@ModelActor
actor ProgressImporter {
    // `modelContext` is provided by @ModelActor, isolated to this actor.
    func importAll(_ items: [LevelStat]) throws {
        for value in items {
            modelContext.insert(
                LevelProgress(
                    levelID: value.levelID,
                    stars: value.stars,
                    bestTimeSeconds: value.bestTimeSeconds
                )
            )
        }
        try modelContext.save()
    }
}
// let importer = ProgressImporter(modelContainer: container)  // container is Sendable
// try await importer.importAll(decodedValues)  // value types cross the boundary
```

## Migration: `VersionedSchema` + `SchemaMigrationPlan`

Every shipped store shape is a **named, versioned schema**. Don't reshape a `@Model` in place across
releases and hope — declare each version and a plan that connects them. This mirrors the `Codable`
`schemaVersion` discipline used elsewhere in the skill.

```swift
// MARK: - Versioned schemas + plan

import Foundation
import SwiftData

enum GameSchemaV1: VersionedSchema {
    static var versionIdentifier = Schema.Version(1, 0, 0)
    static var models: [any PersistentModel.Type] { [LevelProgress.self, RunRecord.self] }
}

enum GameSchemaV2: VersionedSchema {
    static var versionIdentifier = Schema.Version(2, 0, 0)
    static var models: [any PersistentModel.Type] { [LevelProgress.self, RunRecord.self] }
    // LevelProgress now also has `attemptCount: Int` (additive, defaulted).
}

enum GameMigrationPlan: SchemaMigrationPlan {
    static var schemas: [any VersionedSchema.Type] { [GameSchemaV1.self, GameSchemaV2.self] }
    static var stages: [MigrationStage] { [migrateV1toV2] }

    // Lightweight: SwiftData infers it. Use for additive/renamed fields with safe defaults.
    static let migrateV1toV2 = MigrationStage.lightweight(
        fromVersion: GameSchemaV1.self,
        toVersion: GameSchemaV2.self
    )
}
```

- **`.lightweight`** covers additive changes — new optional/defaulted properties, some renames.
  SwiftData derives the migration; you only declare the stage.
- **`.custom(fromVersion:toVersion:willMigrate:didMigrate:)`** is for transforms a schema diff can't
  express (recompute a value, split/merge records, dedupe). Keep the transform pure and
  deterministic; do the heavy fetch/rewrite in `didMigrate`, and never assume a record count.
- **Discipline:** one schema change ⇒ one new `VersionedSchema` with a bumped `Schema.Version` ⇒ one
  `MigrationStage`. Ship the container against the **current** schema with the plan attached. A
  missing stage between two shipped versions is a launch-time crash on a real device — there is no
  "skip a version."

Wire the plan into the container, still local-only:

```swift
@MainActor
func makeContainer() throws -> ModelContainer {
    let schema = Schema(versionedSchema: GameSchemaV2.self)
    let config = ModelConfiguration(
        schema: schema,
        isStoredInMemoryOnly: false,
        cloudKitDatabase: .none  // kids/privacy: on-device only, no CloudKit, no account
    )
    return try ModelContainer(
        for: schema,
        migrationPlan: GameMigrationPlan.self,
        configurations: config
    )
}
```

## Testing: inject an in-memory `ModelContainer`

Make the container an **injected dependency** so tests get a fresh, disk-free store with
`isStoredInMemoryOnly: true`. Production passes the disk container; tests pass the in-memory one —
same `SaveStore` code path either way. Assert on **value types** so no `@Model` leaks into the test.

```swift
import SwiftData
import Testing

@MainActor
func makeInMemoryContainer() throws -> ModelContainer {
    let config = ModelConfiguration(isStoredInMemoryOnly: true, cloudKitDatabase: .none)
    return try ModelContainer(for: LevelProgress.self, configurations: config)
}

@MainActor
@Test
func savesAndReloadsBestTimeAsValueType() throws {
    let store = SaveSystem(context: try makeInMemoryContainer().mainContext)
    store.recordResult(levelID: "level_001", stars: 3, time: 12.5, score: 900)

    let stat = store.fetchLevel("level_001")?.toValue()

    #expect(stat == LevelStat(levelID: "level_001", stars: 3, bestTimeSeconds: 12.5))
}
```

Test **migrations** explicitly by building a container against the old `VersionedSchema`, seeding
records, then opening a new in-memory container against the new schema **with the plan** and
asserting the migrated value types.

## Kids-safe & privacy

- **Local-only, always.** Build the container with `cloudKitDatabase: .none` and no sync — game saves
  never leave the device. Adding the iCloud/CloudKit capability (or a non-`.none` `cloudKitDatabase`)
  silently turns a kids store into a syncing one: off-device data movement plus an account
  dependency, both disallowed in the kids-safe default. To *guarantee* it, ship **no** iCloud/CloudKit
  entitlement. Cross-device save belongs behind the account/parental-gate rules in
  `apple-accounts-pay-and-data.md`, never in a child-facing flow.
- **Store only progress/settings.** Levels completed, best times, stars, chosen difficulty,
  Reduce-Motion override, audio on/off. **No** names, emails, age, location, contacts, photos, device
  IDs, or timestamps tied to a person — see `accessibility-child-safety.md`. A random `UUID` per
  profile is fine; a real identity is not.
- **Make it disposable.** Provide a "reset progress" path (parental-gated if it also clears settings)
  so a parent can wipe everything — there's nothing else to delete because there's no PII.
- **Save at checkpoints, not every frame** — level complete, settings change, scene phase background.

A ready-to-drop starter (a single `GameProgress` `@Model`, an on-disk/in-memory container factory,
and a thin `SaveStore` mapping to a `ProgressDTO`) lives at `assets/swiftdata-save-template.swift`.
