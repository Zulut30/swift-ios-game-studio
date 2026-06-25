//
//  GameView.swift  (template)
//  Swift iOS Game Studio — SwiftUI game starter
//
//  A SwiftUI shell driving a PURE, testable model through an @Observable controller.
//  Works as a SwiftUI-only game (memory/matching/drag-drop/coloring) OR as the shell that
//  hosts a SpriteKit scene via SpriteView. Replace `GameController`/`GameModel` with yours.
//

import SwiftUI
// import SpriteKit  // uncomment for the hybrid SpriteView path

// MARK: - Observable controller (single source of truth for the view layer)

@Observable
final class GameController {
    /// The model is the single source of truth; the view reads it via these passthroughs
    /// and mutates it only through intent methods below.
    private(set) var model = GameModel()

    var score: Int { model.score }
    var state: GameState { model.state }

    func start() { model.reset(); model.state = .playing }
    func pause() { if model.state == .playing { model.state = .paused } }
    func resume() { if model.state == .paused { model.state = .playing } }

    /// Forward a tap intent; the model decides what happens.
    func tapTile(_ id: Int) { model.tapTile(id) }
}

// MARK: - Root container

struct GameContainerView: View {
    @State private var controller = GameController()
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        ZStack {
            switch controller.state {
            case .menu:
                MenuView { controller.start() }
            case .playing, .paused:
                PlayfieldView(controller: controller, reduceMotion: reduceMotion)
                    .overlay(alignment: .top) { HUDView(score: controller.score) }
                    .overlay { if controller.state == .paused { PausedOverlay { controller.resume() } } }
            case .won:
                ResultView(title: "You did it!", action: controller.start)
            case .lost:
                ResultView(title: "Try again", action: controller.start)
            }
        }
        .animation(reduceMotion ? nil : .snappy, value: controller.state)
        .onChange(of: scenePhase) { _, phase in
            if phase != .active { controller.pause() }
        }
    }
}

// MARK: - Subviews (placeholders — adapt per genre)

private struct MenuView: View {
    let onPlay: () -> Void
    var body: some View {
        VStack(spacing: 24) {
            Text("Game Title").font(.largeTitle.bold())
            Button(action: onPlay) { Text("Play").font(.title2).padding(.horizontal, 40).padding(.vertical, 12) }
                .buttonStyle(.borderedProminent)
                .accessibilityLabel("Play")
        }
        .padding()
    }
}

private struct PlayfieldView: View {
    let controller: GameController
    let reduceMotion: Bool
    private let columns = [GridItem(.adaptive(minimum: 80), spacing: 12)]

    var body: some View {
        // Example: a tappable grid of placeholder tiles. Replace with your real board.
        ScrollView {
            LazyVGrid(columns: columns, spacing: 12) {
                ForEach(0..<controller.model.tileCount, id: \.self) { id in
                    RoundedRectangle(cornerRadius: 16)
                        .fill(controller.model.color(forTile: id))
                        .frame(height: 80)
                        .overlay { if controller.model.isMatched(id) { Image(systemName: "checkmark") } }
                        .onTapGesture { controller.tapTile(id) }
                        .accessibilityElement()
                        .accessibilityLabel("Tile \(id + 1)")
                        .accessibilityValue(controller.model.isMatched(id) ? "matched" : "open")
                        .accessibilityAddTraits(.isButton)
                }
            }
            .padding()
        }
    }
}

private struct HUDView: View {
    let score: Int
    var body: some View {
        HStack {
            Text("Score \(score)").font(.headline.monospacedDigit())
            Spacer()
        }
        .padding()
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Score \(score)")
    }
}

private struct PausedOverlay: View {
    let onResume: () -> Void
    var body: some View {
        ZStack {
            Color.black.opacity(0.4).ignoresSafeArea()
            Button("Resume", action: onResume)
                .buttonStyle(.borderedProminent)
        }
    }
}

private struct ResultView: View {
    let title: String
    let action: () -> Void
    var body: some View {
        VStack(spacing: 20) {
            Text(title).font(.largeTitle.bold())
            Button("Play again", action: action).buttonStyle(.borderedProminent)
        }
    }
}

// MARK: - Placeholder pure model (replace with your real, testable model)

enum GameState { case menu, playing, paused, won, lost }

struct GameModel {
    private(set) var score = 0
    var state: GameState = .menu

    let tileCount = 12
    private var matched: Set<Int> = []
    private let palette: [Color] = [.red, .orange, .yellow, .green, .blue, .purple]

    func color(forTile id: Int) -> Color { palette[id % palette.count] }
    func isMatched(_ id: Int) -> Bool { matched.contains(id) }

    mutating func tapTile(_ id: Int) {
        guard state == .playing, !matched.contains(id) else { return }
        matched.insert(id)
        score += 1
        if matched.count == tileCount { state = .won }
    }

    mutating func reset() {
        score = 0
        matched.removeAll()
    }
}
