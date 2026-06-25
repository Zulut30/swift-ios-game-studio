//
//  SeededGenerator.swift
//  Swift iOS Game Studio — drop-in deterministic RNG
//
//  A seedable RandomNumberGenerator (SplitMix64) so shuffles, spawns, and any randomness are
//  REPRODUCIBLE in tests. Inject it everywhere you'd otherwise call the global RNG.
//
//  Why: the global `SystemRandomNumberGenerator` is non-deterministic, so tests that rely on
//  "random" outcomes can't assert anything stable. With a seed, the same seed → the same sequence.
//
//  Usage:
//      var rng = SeededGenerator(seed: 42)
//      cards.shuffle(using: &rng)
//      let i = Int.random(in: 0..<cards.count, using: &rng)
//      let x = Double.random(in: 0...1, using: &rng)
//
//  In a model, store the generator and pass it to APIs that take `using:`:
//      struct Board { var rng: SeededGenerator; mutating func deal() { cards.shuffle(using: &rng) } }
//

import Foundation

/// A deterministic `RandomNumberGenerator` based on SplitMix64.
/// Same `seed` always produces the same sequence — ideal for testable game logic.
struct SeededGenerator: RandomNumberGenerator, Sendable {
    private var state: UInt64

    /// - Parameter seed: any 64-bit seed; `0` is remapped so it never degenerates.
    init(seed: UInt64) {
        state = seed == 0 ? 0x9E3779B97F4A7C15 : seed
    }

    mutating func next() -> UInt64 {
        state &+= 0x9E37_79B9_7F4A_7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }
}

// MARK: - Convenience

extension SeededGenerator {
    /// A generator seeded from the current time. Use ONLY in production where determinism isn't
    /// needed; never in tests (it defeats reproducibility).
    static func random() -> SeededGenerator {
        SeededGenerator(seed: UInt64(Date().timeIntervalSince1970.bitPattern))
    }
}
