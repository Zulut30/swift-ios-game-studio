//
//  GameView.swift
//  MemoryMatch (app layer)
//
//  The board: an adaptive grid of cards (works on iPhone & iPad, portrait & landscape), a HUD,
//  and a win overlay. Thin view — all rules live in MemoryMatchCore via GameController.
//
import SwiftUI
import MemoryMatchCore

struct GameView: View {
    @State private var controller = GameController(pairCount: 6)
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    private let columns = [GridItem(.adaptive(minimum: 72, maximum: 140), spacing: 12)]

    var body: some View {
        VStack(spacing: 16) {
            hud
            ScrollView {
                LazyVGrid(columns: columns, spacing: 12) {
                    ForEach(controller.cards) { card in
                        CardView(card: card, reduceMotion: reduceMotion)
                            .onTapGesture { choose(card) }
                    }
                }
                .padding(.horizontal)
            }
        }
        .padding(.vertical)
        .overlay { if controller.isWon { winOverlay } }
        .animation(reduceMotion ? nil : .snappy, value: controller.cards.map(\.state))
    }

    private var hud: some View {
        HStack {
            Text("Pairs \(controller.matchedPairs)/\(controller.totalPairs)")
            Spacer()
            Text("Moves \(controller.moves)").monospacedDigit()
            Spacer()
            Button("New") { controller.newGame() }
                .buttonStyle(.bordered)
                .accessibilityLabel("New game")
        }
        .font(.headline)
        .padding(.horizontal)
    }

    private var winOverlay: some View {
        VStack(spacing: 20) {
            Image(systemName: "checkmark.seal.fill")
                .resizable().scaledToFit().frame(width: 80, height: 80)
                .foregroundStyle(.green)
                .accessibilityHidden(true)
            Text("You matched them all!").font(.title.bold())
            Text("\(controller.moves) moves").foregroundStyle(.secondary)
            Button("Play again") { controller.newGame() }
                .buttonStyle(.borderedProminent)
        }
        .padding(32)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 24))
        .accessibilityElement(children: .contain)
        .accessibilityAddTraits(.isModal)
    }

    private func choose(_ card: Card) {
        if reduceMotion {
            controller.choose(card)
        } else {
            withAnimation(.snappy) { controller.choose(card) }
        }
    }
}

#Preview {
    GameView()
}
