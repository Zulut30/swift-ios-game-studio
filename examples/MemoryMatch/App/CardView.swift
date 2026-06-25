//
//  CardView.swift
//  MemoryMatch (app layer)
//
//  A single card: a rounded tile that flips between face-down and face-up (an SF Symbol).
//  Placeholder vector art only — no copyrighted assets. Fully accessible.
//
import SwiftUI
import MemoryMatchCore

struct CardView: View {
    let card: Card
    var reduceMotion: Bool = false

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16)
                .fill(card.isFaceUp || card.isMatched ? Color(.systemBackground) : Color.accentColor)
                .overlay {
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.accentColor, lineWidth: card.isMatched ? 0 : 3)
                }

            if card.isFaceUp || card.isMatched {
                Image(systemName: card.symbol)
                    .resizable()
                    .scaledToFit()
                    .padding(20)
                    .foregroundStyle(Color.accentColor)
                    .transition(reduceMotion ? .opacity : .scale.combined(with: .opacity))
            }
        }
        .aspectRatio(1, contentMode: .fit)
        .opacity(card.isMatched ? 0.35 : 1)
        // Accessibility: don't rely on color/symbol alone — describe state.
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Card")
        .accessibilityValue(accessibilityValue)
        .accessibilityAddTraits(card.isMatched ? [] : .isButton)
        .accessibilityHint(card.isMatched ? "" : "Double-tap to flip")
    }

    private var accessibilityValue: String {
        switch card.state {
        case .faceDown: return "face down"
        case .faceUp:   return "showing \(card.symbol)"
        case .matched:  return "matched, \(card.symbol)"
        }
    }
}

#Preview("Faces") {
    HStack {
        CardView(card: Card(id: 0, symbol: "star.fill", state: .faceDown))
        CardView(card: Card(id: 1, symbol: "heart.fill", state: .faceUp))
        CardView(card: Card(id: 2, symbol: "leaf.fill", state: .matched))
    }
    .padding()
}
