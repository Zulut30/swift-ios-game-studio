# Example prompts

Copy-and-paste prompts to drive the `swift-ios-game-studio` skill in Codex, Claude Code, or
Cursor. They're intentionally short — the skill fills in defaults and asks only high-value
questions.

## Starter prompts (one per template)

**coloring-shapes**
> Build a simple coloring book game for ages 4–6 on iPhone and iPad. Tap a region to fill it
> with the selected color, plus undo and clear. SwiftUI-only, placeholder vector shapes, no-fail.

**simple-platformer**
> Make a tiny platformer: run left/right and jump over gaps to reach a flag. One level, on-screen
> controls, SpriteKit inside a SwiftUI shell. Retry on falling. Placeholder shapes.

**drag-and-drop-puzzle**
> Create a drag-and-drop shape puzzle: drag pieces into matching slots; correct snaps and locks,
> wrong bounces back; celebrate when all placed. SwiftUI-only, ages 4–8.

**memory-cards**
> Build a memory match game: 4×3 grid, flip two cards, matches stay up, track moves and time,
> no fail. Seeded shuffle for testability. SwiftUI-only.

**shape-matching**
> Make a "match the shape" learning mini-game: show a target shape and 3 options; tapping the
> right one scores and advances. Don't rely on color alone. SwiftUI-only.

**endless-runner-lite**
> Build a lite endless runner: auto-run, tap to jump obstacles, speed ramps, one hit ends the
> run, score = distance. SpriteKit hybrid, object pooling, placeholder art.

**tap-reaction**
> Create a tap-reaction game: targets appear and shrink; tap before they vanish to score,
> expired = miss. 30-second rounds. SwiftUI or SpriteKit.

## More detailed prompt (shows the skill's full workflow)
> Design and implement an iPad-first educational matching game for ages 5–7 where kids match
> animals (placeholder vector silhouettes) to their habitats. Start with a one-page Mini-GDD,
> recommend SwiftUI-only vs hybrid, lay out a modular architecture with a pure testable model,
> implement an MVP for one round set, add unit tests for the matching/scoring logic, and finish
> with a child-safety/privacy/accessibility/performance review and a handoff. No copyrighted
> assets, no analytics, offline-only.

## Follow-up prompts
- "Add a settings screen with a mute toggle and a Reduce-Motion-friendly win animation."
- "Add 3 more levels as JSON data using the level schema; load them at runtime."
- "Write unit tests for win/lose and seeded shuffling; run them if a project exists."
- "Run the review checklist and list the top risks for the Kids Category (no guarantees)."
- "Scaffold a new module: `scripts/scaffold-game-module.py --name SpaceJump --type simple-platformer`."

## Tips
- State age + platform + orientation if you care; otherwise the skill defaults (ages 4–8,
  both orientations, no-fail, SwiftUI-only unless physics is needed) and documents assumptions.
- Ask for the Mini-GDD first if you want to review scope before code.
- Say "build and run the tests" explicitly if you want the skill to attempt `xcodebuild`.
