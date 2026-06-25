# Testing & release

How to test a simple Swift game and prepare an honest release checklist.

## What to test (priority order)
1. **Pure model rules** — the highest-value, easiest tests. Legal moves, scoring, win/lose,
   state transitions, level loading/decoding. No simulator needed.
2. **Systems** — spawn logic, collision verdicts, save/load round-trips, difficulty ramps.
3. **Determinism** — seeded RNG produces reproducible shuffles/spawns.
4. **View logic (light)** — only the non-trivial bits; avoid brittle pixel/UI snapshot tests
   for an MVP.

## Swift Testing (preferred, Xcode 16+)
```swift
import Testing
@testable import GameName

@Test func matchingPairStaysFaceUp() {
    var board = Board(seed: 42)
    board.flip(cardAt: 0)
    board.flip(cardAt: board.indexOfMatch(for: 0))
    #expect(board.cards.allSatisfy { !$0.isFaceUp || $0.isMatched })
}

@Test func winWhenAllMatched() {
    var board = Board(seed: 1)
    board.matchAllForTesting()
    #expect(board.isWin)
}
```

## XCTest (also fine)
```swift
import XCTest
@testable import GameName

final class ScoreTests: XCTestCase {
    func testTapWithinLifetimeScores() {
        var game = ReactionGame(seed: 7)
        let target = game.spawnTarget(now: 0)
        game.tap(targetID: target.id, now: target.lifetime - 0.1)
        XCTAssertEqual(game.score, 1)
    }
}
```

## Build & test commands
Prefer the helper: `scripts/verify-ios-project.sh` (discovers project/workspace & schemes,
runs a safe build/test when `SCHEME` and `DESTINATION` are provided).

Manual equivalents:
```bash
# Discover
xcodebuild -list -project GameName.xcodeproj
xcrun simctl list devicetypes | grep -i iphone

# Build
xcodebuild build \
  -project GameName.xcodeproj -scheme GameName \
  -destination 'platform=iOS Simulator,name=iPhone 15'

# Test
xcodebuild test \
  -project GameName.xcodeproj -scheme GameName \
  -destination 'platform=iOS Simulator,name=iPhone 15'
```
Use `-workspace GameName.xcworkspace` instead of `-project` when a workspace exists.

**Honesty rule:** only claim the build/tests passed if you actually ran them and saw it.
If there's no project or no toolchain, say "not built/tested here" and provide the commands.

## Manual QA pass (before calling it done)
- Launch, play the core loop start→finish, win and (if applicable) lose.
- Rotate device; check iPhone and iPad layouts; check safe areas/notch/Dynamic Island.
- Background/foreground mid-game: state preserved, no `dt` spike, audio pauses/resumes.
- VoiceOver on: can you navigate and play? Reduce Motion on: no jarring motion.
- Restart/replay works; persistence survives relaunch.

## Release checklist (honest, not a guarantee)
- [ ] App icon (all sizes) + launch screen.
- [ ] Supported orientations & devices set correctly in the target.
- [ ] Privacy: `PrivacyInfo.xcprivacy` accurate; "Data Not Collected" if true; no tracking.
- [ ] No prohibited content; age rating set; Kids Category rules met **if** targeting it.
- [ ] No external links / ads / analytics in a child-facing build.
- [ ] Permissions: only those used, each with a clear usage string.
- [ ] Builds for release, archives, and runs on a real device.
- [ ] Tests pass; no debug logging or placeholder text shipped.
- [ ] Version/build numbers set; screenshots prepared.

**Never assert guaranteed App Store / COPPA / Kids approval.** Present this checklist plus a
risk list and recommend the user verify against current App Store Review Guidelines.
