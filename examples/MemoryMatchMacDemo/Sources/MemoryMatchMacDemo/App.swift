//
//  App.swift
//  MemoryMatchMacDemo
//
//  A thin macOS SwiftUI shell over the shared `MemoryMatchCore` rules. Run with:
//      swift run --package-path examples/MemoryMatchMacDemo
//
import AppKit
import MemoryMatchCore
import SwiftUI

@MainActor
@Observable
final class DemoController {
    private(set) var game: MemoryGame
    private var seed: UInt64

    init(seed: UInt64 = 1) {
        self.seed = seed
        self.game = MemoryGame(pairCount: 6, seed: seed)
    }

    var cards: [Card] { game.cards }
    var moves: Int { game.moves }
    var isWon: Bool { game.isWon }
    var matchedPairs: Int { game.matchedPairs }
    var totalPairs: Int { game.pairCount }

    func choose(_ card: Card) { game.choose(card) }

    func newGame() {
        seed &+= 1
        game = MemoryGame(pairCount: 6, seed: seed)
    }
}

struct CardView: View {
    let card: Card

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 14)
                .fill(card.isFaceUp || card.isMatched ? Color(white: 0.97) : Color.accentColor)
                .overlay {
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color.accentColor, lineWidth: card.isMatched ? 0 : 2)
                }
            if card.isFaceUp || card.isMatched {
                Image(systemName: card.symbol)
                    .resizable()
                    .scaledToFit()
                    .padding(18)
                    .foregroundStyle(Color.accentColor)
            }
        }
        .frame(height: 104)
        .opacity(card.isMatched ? 0.4 : 1)
        .accessibilityElement()
        .accessibilityLabel("Card")
        .accessibilityValue(
            card.isMatched ? "matched, \(card.symbol)" : (card.isFaceUp ? card.symbol : "face down")
        )
        .accessibilityAddTraits(card.isMatched ? [] : .isButton)
        .accessibilityHint(card.isMatched ? "" : "Double-tap to flip")
    }
}

struct ContentView: View {
    @State private var controller = DemoController()
    private let columns = [GridItem(.adaptive(minimum: 92, maximum: 130), spacing: 12)]

    var body: some View {
        VStack(spacing: 16) {
            HStack {
                Text("Pairs \(controller.matchedPairs)/\(controller.totalPairs)")
                Spacer()
                Text("Moves \(controller.moves)").monospacedDigit()
                Spacer()
                Button("New game") { withAnimation(.snappy) { controller.newGame() } }
            }
            .font(.headline)
            .padding(.horizontal)

            LazyVGrid(columns: columns, spacing: 12) {
                ForEach(controller.cards) { card in
                    CardView(card: card)
                        .onTapGesture { withAnimation(.snappy) { controller.choose(card) } }
                }
            }
            .padding(.horizontal)

            if controller.isWon {
                Text("You matched them all in \(controller.moves) moves!")
                    .font(.title3.bold())
                    .foregroundStyle(.green)
            }
            Spacer(minLength: 0)
        }
        .padding(.vertical)
        .frame(minWidth: 480, minHeight: 560)
        .onAppear {
            NSApp.setActivationPolicy(.regular)
            NSApp.activate(ignoringOtherApps: true)
        }
    }
}

@main
struct MemoryMatchMacDemoApp: App {
    var body: some Scene {
        WindowGroup("Memory Match") {
            ContentView()
        }
        .defaultSize(width: 520, height: 640)
    }
}
