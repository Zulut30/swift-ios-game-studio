//
//  MemoryGameTests.swift
//  MemoryMatchCoreTests
//
//  Unit tests for the pure model. Deterministic via seeded deals — no simulator needed.
//  Run: `swift test` from examples/MemoryMatch.
//
import Testing

@testable import MemoryMatchCore

// MARK: - Helpers

private extension MemoryGame {
    /// Two face-down card ids that share a symbol (a matching pair).
    func aMatchingPair() -> (Int, Int)? {
        for i in cards.indices where cards[i].state == .faceDown {
            for j in cards.indices
            where j != i && cards[j].state == .faceDown
                && cards[j].symbol == cards[i].symbol
            {
                return (cards[i].id, cards[j].id)
            }
        }
        return nil
    }

    /// Two face-down card ids with different symbols (a guaranteed mismatch).
    func aMismatchedPair() -> (Int, Int)? {
        guard let first = cards.first(where: { $0.state == .faceDown }) else { return nil }
        guard let other = cards.first(where: { $0.state == .faceDown && $0.symbol != first.symbol }) else {
            return nil
        }
        return (first.id, other.id)
    }

    /// Play every pair to completion (used to reach the win state).
    mutating func playToWin() {
        while !isWon {
            guard let (a, b) = aMatchingPair() else { break }
            choose(cardID: a)
            choose(cardID: b)
        }
    }
}

// MARK: - Dealing

@Test func dealCreatesPairsOfFaceDownCards() {
    let game = MemoryGame(pairCount: 6, seed: 1)
    #expect(game.cards.count == 12)
    #expect(game.pairCount == 6)
    #expect(game.cards.allSatisfy { $0.state == .faceDown })

    // Every symbol appears exactly twice.
    let counts = Dictionary(grouping: game.cards, by: \.symbol).mapValues(\.count)
    #expect(counts.count == 6)
    #expect(counts.values.allSatisfy { $0 == 2 })
}

@Test func sameSeedDealsIdentically() {
    let a = MemoryGame(pairCount: 8, seed: 42)
    let b = MemoryGame(pairCount: 8, seed: 42)
    #expect(a.cards.map(\.id) == b.cards.map(\.id))
    #expect(a.cards.map(\.symbol) == b.cards.map(\.symbol))
}

@Test func differentSeedsGenerallyDiffer() {
    let a = MemoryGame(pairCount: 8, seed: 1)
    let b = MemoryGame(pairCount: 8, seed: 2)
    // Same multiset of symbols, but the order should differ for these seeds.
    #expect(a.cards.map(\.symbol) != b.cards.map(\.symbol))
}

// MARK: - Choosing

@Test func firstChoiceTurnsOneCardFaceUp() {
    var game = MemoryGame(pairCount: 6, seed: 7)
    let id = game.cards[0].id
    let accepted = game.choose(cardID: id)
    #expect(accepted)
    #expect(game.cards.first { $0.id == id }?.state == .faceUp)
    #expect(game.moves == 0)  // moves count completed turns (the second card), not the first flip
    #expect(game.cards.filter { $0.state == .faceUp }.count == 1)
}

@Test func choosingSameCardAgainIsRejected() {
    var game = MemoryGame(pairCount: 6, seed: 7)
    let id = game.cards[0].id
    let first = game.choose(cardID: id)
    let second = game.choose(cardID: id)
    #expect(first)
    #expect(second == false)  // already face up
}

@Test func matchingPairBecomesMatched() throws {
    var game = MemoryGame(pairCount: 6, seed: 3)
    let (a, b) = try #require(game.aMatchingPair())
    game.choose(cardID: a)
    game.choose(cardID: b)
    #expect(game.cards.first { $0.id == a }?.state == .matched)
    #expect(game.cards.first { $0.id == b }?.state == .matched)
    #expect(game.moves == 1)
    #expect(game.matchedPairs == 1)
}

@Test func mismatchStaysFaceUpThenFlipsBackNextTurn() throws {
    var game = MemoryGame(pairCount: 6, seed: 5)
    let (a, b) = try #require(game.aMismatchedPair())
    game.choose(cardID: a)
    game.choose(cardID: b)
    // Both face up, neither matched.
    #expect(game.cards.first { $0.id == a }?.state == .faceUp)
    #expect(game.cards.first { $0.id == b }?.state == .faceUp)
    #expect(game.matchedPairs == 0)

    // Starting the next turn flips the leftover mismatched cards back down.
    let c = try #require(game.cards.first { $0.state == .faceDown })
    game.choose(cardID: c.id)
    #expect(game.cards.first { $0.id == a }?.state == .faceDown)
    #expect(game.cards.first { $0.id == b }?.state == .faceDown)
    #expect(game.cards.first { $0.id == c.id }?.state == .faceUp)
}

// MARK: - Winning

@Test func winsWhenAllPairsMatched() {
    var game = MemoryGame(pairCount: 6, seed: 9)
    #expect(!game.isWon)
    game.playToWin()
    #expect(game.isWon)
    #expect(game.phase == .won)
    #expect(game.matchedPairs == 6)
    #expect(game.cards.allSatisfy { $0.state == .matched })
}

@Test func choosingAfterWinIsRejected() {
    var game = MemoryGame(pairCount: 2, seed: 11)
    game.playToWin()
    #expect(game.isWon)
    // No face-down cards remain, and the game is won.
    let rejected = game.choose(cardID: game.cards[0].id)
    #expect(rejected == false)
}

@Test func minimalGameSinglePair() {
    var game = MemoryGame(pairCount: 1, seed: 0)
    #expect(game.cards.count == 2)
    game.choose(cardID: game.cards[0].id)
    game.choose(cardID: game.cards[1].id)
    #expect(game.isWon)
    #expect(game.moves == 1)
}
