# SwiftUI mastery (for game UI & SwiftUI-only games)

Patterns for menus, HUD, settings, and full SwiftUI-only games (coloring, memory, matching,
drag-and-drop, tap-reaction). Pair with swiftui-spritekit-patterns.md for SpriteKit interop.

## State ownership — pick the right tool
| Tool | Use for |
|---|---|
| `@State` | View-local, value-typed transient state (animation flags, drag offset) |
| `@Binding` | A child mutating state owned by a parent |
| `@Observable` class + `@State` | The game controller / model (iOS 17+, Observation framework) |
| `@Environment` | Cross-cutting injected values (controller, theme, settings) |
| `@AppStorage` | Tiny persisted settings (mute toggle, last level) |

```swift
@Observable final class GameController { var score = 0; var state: GameState = .menu }

struct GameContainer: View {
    @State private var controller = GameController()   // owns it
    var body: some View { PlayView().environment(controller) }
}

struct PlayView: View {
    @Environment(GameController.self) private var controller   // reads it
    var body: some View { Text("Score \(controller.score)") }  // auto-updates
}
```
- With `@Observable`, views automatically track only the properties they read — fewer redraws,
  no manual `@Published`.
- Pre-iOS-17 fallback: `ObservableObject` + `@Published` + `@StateObject`/`@EnvironmentObject`.

## View composition — small, focused views
- Break a screen into small `View` structs (`HUDView`, `BoardView`, `TileView`). Each `body`
  stays cheap and diffable.
- Extract subviews instead of giant `body`s; pass minimal data in.
- Keep heavy computation out of `body` (precompute, cache, or do it in the model).

## Identity & ForEach
- Give collection items stable identity (`Identifiable` or `id:`). Stable identity = correct
  animations and no needless rebuilds.

```swift
LazyVGrid(columns: cols) {
    ForEach(board.cards) { card in TileView(card: card) }   // card: Identifiable
}
```

## Layout
- Compose with `HStack`/`VStack`/`ZStack`/`Grid`/`LazyVGrid`. Use `Spacer`, `.frame`, `.padding`.
- `GeometryReader` for size-relative layout (game boards that scale to the device). Read size once,
  compute positions from it; avoid nesting many GeometryReaders.
- Adopt the `Layout` protocol only for genuinely custom arrangements (radial menus, fan of cards).
- Respect safe areas; use `.ignoresSafeArea()` deliberately for full-bleed game canvases.

## Drawing without a game loop
For static/turn-based games you rarely need per-frame rendering:
- `Shape`/`Path` for vector art (coloring regions, pieces).
- `Canvas` for many lightweight shapes drawn imperatively (cheaper than thousands of views).
- `.contentShape(...)` to make the whole intended area tappable (fixes hit-testing on shapes).

```swift
Path { p in p.addRoundedRect(in: rect, cornerSize: .init(width: 12, height: 12)) }
    .fill(tile.color)
    .contentShape(Rectangle())
    .onTapGesture { controller.tapTile(tile.id) }
```

## Animation
- Prefer `withAnimation { state change }` and `.animation(_, value:)` over manual timers.
- Use `.transition` for insert/remove; `matchedGeometryEffect` for card flips/moves.
- **Always gate large motion on Reduce Motion:**

```swift
@Environment(\.accessibilityReduceMotion) private var reduceMotion
.animation(reduceMotion ? nil : .snappy, value: controller.state)
```

## Gestures → model intents
- `TapGesture`, `LongPressGesture`, `DragGesture`. Translate them into model intents; the model
  decides legality/scoring (keep rules out of the view).

```swift
.gesture(DragGesture()
    .onChanged { controller.dragMoved(to: $0.location) }
    .onEnded   { controller.dragEnded(at: $0.location) })
```

## Lifecycle & scene phase
- Pause on backgrounding; resume on activation:

```swift
@Environment(\.scenePhase) private var scenePhase
.onChange(of: scenePhase) { _, phase in if phase != .active { controller.pause() } }
```

## Accessibility (first-class, not bolted on)
- `.accessibilityLabel/Value/AddTraits` on every interactive element; `.accessibilityHidden(true)`
  on decoration. Support Dynamic Type via text styles. See accessibility-child-safety.md.

## Performance
- Stable identity, small bodies, no allocation in `body`, `LazyV/HGrid` for large grids, `Canvas`
  for many primitives, `.drawingGroup()` (Metal) for expensive static composites. Profile, don't guess.

## Previews
- Add `#Preview` for each view with representative model state — fast visual iteration and a smoke
  test that the view compiles with realistic data.

```swift
#Preview { BoardView().environment(GameController.previewWon) }
```
