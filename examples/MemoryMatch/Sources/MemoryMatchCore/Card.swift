//
//  Card.swift
//  MemoryMatchCore
//
//  A single memory card. Value type; illegal states are unrepresentable via `CardState`
//  (a card can't be both face-down and matched).
//
import Foundation

/// The lifecycle of a card. Encodes the invariant that "matched" and "face down" are exclusive.
public enum CardState: Sendable, Equatable {
    case faceDown
    case faceUp
    case matched
}

/// One card on the board. `symbol` is the match key (cards with the same symbol form a pair).
public struct Card: Identifiable, Equatable, Sendable {
    public let id: Int
    /// Non-localized match key, e.g. an SF Symbol name. Two cards match iff symbols are equal.
    public let symbol: String
    public internal(set) var state: CardState

    public init(id: Int, symbol: String, state: CardState = .faceDown) {
        self.id = id
        self.symbol = symbol
        self.state = state
    }

    public var isFaceUp: Bool { state == .faceUp }
    public var isMatched: Bool { state == .matched }
}
