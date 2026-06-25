#!/usr/bin/env python3
"""
scaffold-game-module.py — create a small, modular folder/module skeleton for a requested
game type. NON-DESTRUCTIVE: it never overwrites existing files; it only creates what's missing
and reports what it skipped.

Usage:
    scripts/scaffold-game-module.py --name SpaceJump --type simple-platformer
    scripts/scaffold-game-module.py --name ColorPals --type coloring-shapes --dest ./Sources
    scripts/scaffold-game-module.py --list-types

Supported types:
    coloring-shapes, simple-platformer, drag-and-drop-puzzle, memory-cards,
    shape-matching, endless-runner-lite, tap-reaction

It creates:
    <dest>/<Name>/
      App/         Models/        Systems/
      Scenes/      Views/         Resources/Levels/   Tests/
    plus a few starter Swift files and a README describing the module.

This is a starting point only; adapt the generated files to the real game.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SUPPORTED_TYPES = [
    "coloring-shapes",
    "simple-platformer",
    "drag-and-drop-puzzle",
    "memory-cards",
    "shape-matching",
    "endless-runner-lite",
    "tap-reaction",
]

# Types that need continuous motion/physics -> SpriteKit (hybrid). Others -> SwiftUI-only.
SPRITEKIT_TYPES = {"simple-platformer", "endless-runner-lite"}

SUBDIRS = ["App", "Models", "Systems", "Scenes", "Views", "Resources/Levels", "Tests"]


def model_stub(name: str, gtype: str) -> str:
    return f"""//
//  {name}Model.swift
//  Pure, testable game logic for the {gtype} game. No SwiftUI/SpriteKit imports here.
//

import Foundation

enum {name}State {{ case menu, playing, paused, won, lost }}

/// The single source of truth for {name}. Keep all rules here so they are unit-testable.
struct {name}Model {{
    private(set) var score = 0
    var state: {name}State = .menu

    mutating func start() {{ score = 0; state = .playing }}

    /// Advance time-based systems. Frame-rate independent via dt.
    mutating func advance(by dt: TimeInterval) {{
        guard state == .playing else {{ return }}
        // TODO: advance spawners/timers/difficulty here.
    }}

    // TODO: add genre rules: legal moves, scoring, win/lose for {gtype}.
}}
"""


def tests_stub(name: str) -> str:
    return f"""//
//  {name}ModelTests.swift
//  Unit tests for the pure model. Prefer Swift Testing; XCTest also fine.
//

import Testing
@testable import {name}

@Test func startsInPlayingWithZeroScore() {{
    var model = {name}Model()
    model.start()
    #expect(model.state == .playing)
    #expect(model.score == 0)
}}
"""


def readme_stub(name: str, gtype: str, mode: str) -> str:
    return f"""# {name}

Scaffolded {gtype} game module.

- **Implementation mode:** {mode}
- **Source of truth:** `Models/{name}Model.swift` (pure Swift, unit-tested).

## Folders
- `App/` — @main App, root view, app config.
- `Models/` — pure rules/state (no SwiftUI/SpriteKit).
- `Systems/` — input, score, spawn, collision, audio, save.
- `Scenes/` — SKScene subclasses (SpriteKit/hybrid only).
- `Views/` — SwiftUI views: menu, HUD, settings, game container.
- `Resources/Levels/` — level JSON (see the skill's level-schema-template.json).
- `Tests/` — unit tests for Models + Systems.

## Next steps
1. Flesh out `{name}Model` with the {gtype} rules (legal moves, scoring, win/lose).
2. Add the view/scene from the skill's assets templates.
3. Add level data; wire persistence for progress/settings only.
4. Run the review checklist (child safety, privacy, a11y, performance).

> No copyrighted assets. Use placeholder vector shapes or user-owned assets only.
"""


def create_file(path: Path, content: str, created: list[str], skipped: list[str]) -> None:
    if path.exists():
        skipped.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(str(path))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Scaffold a non-destructive game module skeleton.")
    parser.add_argument("--name", help="Module/game name in UpperCamelCase, e.g. SpaceJump.")
    parser.add_argument("--type", dest="gtype", help="Game type (see --list-types).")
    parser.add_argument("--dest", default=".", help="Destination directory (default: current dir).")
    parser.add_argument("--list-types", action="store_true", help="List supported game types and exit.")
    args = parser.parse_args(argv)

    if args.list_types:
        print("Supported types:")
        for t in SUPPORTED_TYPES:
            mode = "SpriteKit (hybrid)" if t in SPRITEKIT_TYPES else "SwiftUI-only"
            print(f"  - {t:<22} -> {mode}")
        return 0

    if not args.name or not args.gtype:
        parser.error("--name and --type are required (or use --list-types)")

    if args.gtype not in SUPPORTED_TYPES:
        print(f"error: unknown type '{args.gtype}'. Use --list-types.", file=sys.stderr)
        return 2

    name = args.name
    gtype = args.gtype
    mode = "SpriteKit (hybrid)" if gtype in SPRITEKIT_TYPES else "SwiftUI-only"
    root = Path(args.dest).expanduser().resolve() / name

    created: list[str] = []
    skipped: list[str] = []

    # Folders (mkdir is inherently non-destructive).
    for sub in SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)

    # Starter files (never overwritten).
    create_file(root / "Models" / f"{name}Model.swift", model_stub(name, gtype), created, skipped)
    create_file(root / "Tests" / f"{name}ModelTests.swift", tests_stub(name), created, skipped)
    create_file(root / "README.md", readme_stub(name, gtype, mode), created, skipped)

    print(f"Scaffolded '{name}' ({gtype}, {mode}) at: {root}")
    if created:
        print("\nCreated:")
        for p in created:
            print(f"  + {p}")
    if skipped:
        print("\nSkipped (already exist, left untouched):")
        for p in skipped:
            print(f"  = {p}")
    print("\nNext: flesh out the model, add views/scenes from the skill assets, then run the review checklist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
