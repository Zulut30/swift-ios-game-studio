//
//  Persistence.swift  (template)
//  Swift iOS Game Studio — local-only SwiftData progress store (kids-safe)
//
//  Stores ONLY game progress/settings on-device. No PII, no CloudKit/iCloud sync, offline-first.
//  The pure core never imports SwiftData: it speaks `ProgressDTO` (a Sendable value type); the
//  `SaveStore` actor maps DTO <-> the `@Model` at the persistence seam. See
//  references/swiftdata-persistence.md and references/ios-game-architecture.md.
//
//  Reach for SwiftData only when you have many queryable records. For one small save blob, a
//  Codable file or UserDefaults is simpler and just as kid-safe — don't add a database by reflex.
//

import Foundation
import SwiftData

// MARK: - Value-type DTO (the seam the pure core sees)

/// What the game logic reads and writes. No SwiftData, no reference identity — safe to test,
/// diff, and pass across actors. Map to/from `GameProgress` only inside `SaveStore`.
struct ProgressDTO: Sendable, Equatable, Codable {
    var schemaVersion: Int = 1
    var levelsCompleted: Set<Int> = []
    /// levelID -> best time in seconds (lower is better). No timestamps, no PII.
    var bestTimes: [Int: Double] = [:]
    var soundEnabled: Bool = true
    var reduceMotionOverride: Bool = false

    /// Record a finished level and keep only the fastest time for it.
    mutating func record(level: Int, time: Double) {
        levelsCompleted.insert(level)
        bestTimes[level] = min(bestTimes[level] ?? .infinity, time)
    }
}

// MARK: - Persisted model (never leaves the persistence layer)

/// On-disk shape. A single row holds the player's local progress, keyed by a stable id so we
/// fetch/update instead of duplicating. SwiftData stores value types, so the time map is encoded
/// as a parallel pair of arrays and reassembled in `dto`.
@Model
final class GameProgress {
    @Attribute(.unique) var id: String
    var schemaVersion: Int
    var levelsCompleted: [Int]
    var bestTimeLevels: [Int]
    var bestTimeSeconds: [Double]
    var soundEnabled: Bool
    var reduceMotionOverride: Bool

    init(dto: ProgressDTO, id: String = "default") {
        self.id = id
        self.schemaVersion = dto.schemaVersion
        self.levelsCompleted = dto.levelsCompleted.sorted()
        let pairs = dto.bestTimes.sorted { $0.key < $1.key }
        self.bestTimeLevels = pairs.map(\.key)
        self.bestTimeSeconds = pairs.map(\.value)
        self.soundEnabled = dto.soundEnabled
        self.reduceMotionOverride = dto.reduceMotionOverride
    }

    /// Overwrite this row from a DTO (used when saving an updated snapshot).
    func apply(_ dto: ProgressDTO) {
        schemaVersion = dto.schemaVersion
        levelsCompleted = dto.levelsCompleted.sorted()
        let pairs = dto.bestTimes.sorted { $0.key < $1.key }
        bestTimeLevels = pairs.map(\.key)
        bestTimeSeconds = pairs.map(\.value)
        soundEnabled = dto.soundEnabled
        reduceMotionOverride = dto.reduceMotionOverride
    }

    /// Project back to the pure value type for the core.
    var dto: ProgressDTO {
        var times: [Int: Double] = [:]
        for (level, seconds) in zip(bestTimeLevels, bestTimeSeconds) {
            times[level] = seconds
        }
        return ProgressDTO(
            schemaVersion: schemaVersion,
            levelsCompleted: Set(levelsCompleted),
            bestTimes: times,
            soundEnabled: soundEnabled,
            reduceMotionOverride: reduceMotionOverride
        )
    }
}

// MARK: - Container factory (in-memory for tests, on-disk for the app; never CloudKit)

enum ProgressContainer {
    private static let schema = Schema([GameProgress.self])

    /// On-disk store in the app sandbox. `cloudKitDatabase: .none` makes "no iCloud sync" explicit
    /// and auditable; ship NO iCloud/CloudKit entitlement to guarantee it.
    static func onDisk() throws -> ModelContainer {
        try make(name: "Progress", inMemory: false)
    }

    /// Ephemeral store for unit tests and previews — nothing touches disk.
    static func inMemory() throws -> ModelContainer {
        try make(name: "ProgressTest", inMemory: true)
    }

    private static func make(name: String, inMemory: Bool) throws -> ModelContainer {
        let config = ModelConfiguration(
            name,
            schema: schema,
            isStoredInMemoryOnly: inMemory,
            cloudKitDatabase: .none
        )
        return try ModelContainer(for: schema, configurations: [config])
    }
}

// MARK: - SaveStore (thin actor over the context; maps at the seam)

/// Serializes all persistence on its own `ModelContext`. The rest of the app passes/gets
/// `ProgressDTO` only — `GameProgress` stays sealed inside here. Save at checkpoints (level
/// complete, settings change, scene phase background), never every frame.
actor SaveStore {
    private let context: ModelContext

    init(container: ModelContainer) {
        self.context = ModelContext(container)
    }

    /// Convenience: on-disk store for the running app.
    init() throws {
        self.init(container: try ProgressContainer.onDisk())
    }

    /// Load the single progress row, or a fresh default DTO if none exists yet.
    func load() throws -> ProgressDTO {
        try fetchRow()?.dto ?? ProgressDTO()
    }

    /// Persist a snapshot: update the existing row in place, or insert the first one.
    func save(_ dto: ProgressDTO) throws {
        if let row = try fetchRow() {
            row.apply(dto)
        } else {
            context.insert(GameProgress(dto: dto))
        }
        try context.save()
    }

    /// Wipe all local progress (e.g. a parental-gated "reset"). There is no PII to erase.
    func reset() throws {
        try context.delete(model: GameProgress.self)
        try context.save()
    }

    private func fetchRow() throws -> GameProgress? {
        let target = "default"
        let descriptor = FetchDescriptor<GameProgress>(
            predicate: #Predicate { $0.id == target }
        )
        return try context.fetch(descriptor).first
    }
}
