//
//  GameController.swift
//  MemoryMatch (app layer)
//
//  The @Observable, @MainActor bridge between the pure `MemoryGame` model and SwiftUI.
//  Views read its published-by-observation properties and call its intent methods.
//
//  NOTE: This file is part of the iOS app target, NOT the SPM package. Add it (and the other
//  files in App/) to an Xcode app target that depends on the MemoryMatchCore library.
//
import Foundation
import MemoryMatchCore

@MainActor
@Observable
final class GameController {
    private(set) var game: MemoryGame
    private let pairCount: Int
    private var nextSeed: UInt64

    init(pairCount: Int = 6, seed: UInt64 = 1) {
        self.pairCount = pairCount
        self.nextSeed = seed
        self.game = MemoryGame(pairCount: pairCount, seed: seed)
    }

    var cards: [Card] { game.cards }
    var moves: Int { game.moves }
    var isWon: Bool { game.isWon }
    var matchedPairs: Int { game.matchedPairs }
    var totalPairs: Int { game.pairCount }

    /// Forward a tap on a card. The model decides legality and matching.
    func choose(_ card: Card) {
        game.choose(card)
    }

    /// Start a fresh deal. In production you might randomize the seed; keep it deterministic in tests.
    func newGame() {
        nextSeed &+= 1
        game = MemoryGame(pairCount: pairCount, seed: nextSeed)
    }
}
