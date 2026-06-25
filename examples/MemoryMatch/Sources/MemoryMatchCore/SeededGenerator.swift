//
//  SeededGenerator.swift
//  MemoryMatchCore
//
//  Deterministic RNG (SplitMix64) so the deal is reproducible in tests.
//  Mirrors assets/seeded-random.swift from the skill.
//
import Foundation

/// A deterministic `RandomNumberGenerator`. Same `seed` → same sequence.
public struct SeededGenerator: RandomNumberGenerator, Sendable {
    private var state: UInt64

    public init(seed: UInt64) {
        state = seed == 0 ? 0x9E3779B97F4A7C15 : seed
    }

    public mutating func next() -> UInt64 {
        state &+= 0x9E37_79B9_7F4A_7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }
}
