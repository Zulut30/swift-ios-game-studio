//
//  MemoryGame.swift
//  MemoryMatchCore
//
//  The pure, testable game model for a memory/matching card game. No SwiftUI/SpriteKit imports.
//  This is the single source of truth: the view renders `cards`/`phase` and forwards `choose(_:)`.
//
//  Rules (classic two-up memory):
//   - Tap a face-down card to turn it face up.
//   - On the second face-up card of a turn, if symbols match, both become matched; otherwise both
//     stay face up until the next turn starts, when leftover mismatched cards flip back down.
//   - No-fail: there's no lose state, only "won when all cards are matched". `moves` is the score.
//
import Foundation

public enum GamePhase: Sendable, Equatable {
    case playing
    case won
}

public struct MemoryGame: Sendable {

    /// Default friendly symbols (SF Symbol names) — bright, recognizable, no reading required.
    public static let defaultSymbols = [
        "star.fill", "heart.fill", "bolt.fill", "leaf.fill", "moon.fill", "sun.max.fill",
        "cloud.fill", "flame.fill", "drop.fill", "snowflake", "tortoise.fill", "hare.fill",
    ]

    public private(set) var cards: [Card]
    public private(set) var moves = 0

    /// Index of the single face-up, unmatched card waiting for its pair (nil at turn start).
    private var indexOfFaceUpCard: Int?

    public var phase: GamePhase { cards.allSatisfy(\.isMatched) ? .won : .playing }
    public var isWon: Bool { phase == .won }
    public var matchedPairs: Int { cards.lazy.filter(\.isMatched).count / 2 }
    public var pairCount: Int { cards.count / 2 }

    /// Deal `pairCount` pairs, shuffled deterministically from `seed`.
    /// - Precondition: `1...symbols.count` pairs.
    public init(pairCount: Int, seed: UInt64, symbols: [String] = MemoryGame.defaultSymbols) {
        precondition(pairCount >= 1, "Need at least one pair")
        precondition(pairCount <= symbols.count, "Not enough distinct symbols for \(pairCount) pairs")

        var deck: [Card] = []
        deck.reserveCapacity(pairCount * 2)
        for pair in 0..<pairCount {
            let symbol = symbols[pair]
            deck.append(Card(id: pair * 2, symbol: symbol))
            deck.append(Card(id: pair * 2 + 1, symbol: symbol))
        }
        var rng = SeededGenerator(seed: seed)
        deck.shuffle(using: &rng)
        cards = deck
    }

    /// Forward a tap intent. The model decides what (if anything) happens.
    /// - Returns: `true` if the choice was accepted (card existed, was face-down, game not won).
    @discardableResult
    public mutating func choose(_ card: Card) -> Bool {
        choose(cardID: card.id)
    }

    @discardableResult
    public mutating func choose(cardID id: Int) -> Bool {
        guard phase == .playing,
              let chosen = cards.firstIndex(where: { $0.id == id }),
              cards[chosen].state == .faceDown
        else { return false }

        if let pending = indexOfFaceUpCard {
            // Second card of the turn.
            cards[chosen].state = .faceUp
            moves += 1
            if cards[chosen].symbol == cards[pending].symbol {
                cards[chosen].state = .matched
                cards[pending].state = .matched
            }
            indexOfFaceUpCard = nil
        } else {
            // First card of a new turn: flip any leftover mismatched cards back down.
            for i in cards.indices where cards[i].state == .faceUp {
                cards[i].state = .faceDown
            }
            cards[chosen].state = .faceUp
            indexOfFaceUpCard = chosen
        }
        return true
    }
}
