//
//  GameView.swift
//  SkyHopper (app layer)
//
//  The SwiftUI shell: hosts the SpriteKit gameplay via `SpriteView` and overlays a HUD, a
//  start prompt, and a game-over panel — the "hybrid SwiftUI + SpriteKit" mode. The shell owns
//  menus/HUD; the scene owns gameplay rendering; the model owns the rules.
//
import SwiftUI
import SpriteKit
import SkyHopperCore

struct GameView: View {
    @State private var controller: GameController
    @State private var scene: GameScene
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    init() {
        let c = GameController()
        _controller = State(initialValue: c)
        _scene = State(initialValue: GameScene(size: CGSize(width: 400, height: 700), controller: c))
    }

    var body: some View {
        ZStack {
            SpriteView(scene: scene, options: [.ignoresSiblingOrder])
                .ignoresSafeArea()
                .accessibilityLabel("Tap to flap")
                .accessibilityAddTraits(.allowsDirectInteraction)

            VStack {
                Text("\(controller.score)")
                    .font(.system(size: 56, weight: .heavy, design: .rounded))
                    .monospacedDigit()
                    .foregroundStyle(.white)
                    .shadow(radius: 4)
                    .padding(.top, 24)
                    .accessibilityLabel("Score \(controller.score)")
                Spacer()
            }

            switch controller.phase {
            case .ready:
                prompt("Tap to start")
            case .gameOver:
                gameOverPanel
            case .playing:
                EmptyView()
            }
        }
    }

    private func prompt(_ text: String) -> some View {
        Text(text)
            .font(.title2.weight(.semibold))
            .foregroundStyle(.white)
            .padding(.horizontal, 24)
            .padding(.vertical, 12)
            .background(.black.opacity(0.35), in: Capsule())
    }

    private var gameOverPanel: some View {
        VStack(spacing: 16) {
            Text("Game over").font(.largeTitle.bold())
            Text("Score \(controller.score) · Best \(controller.bestScore)")
                .foregroundStyle(.secondary)
            Button("Play again") { controller.restart() }
                .buttonStyle(.borderedProminent)
                .accessibilityLabel("Play again")
        }
        .padding(28)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 24))
        .accessibilityElement(children: .contain)
        .accessibilityAddTraits(.isModal)
    }
}

#Preview {
    GameView()
}
