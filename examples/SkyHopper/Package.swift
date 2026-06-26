// swift-tools-version: 6.0
//
//  SkyHopper — the SpriteKit + SwiftUI (hybrid) reference game for swift-ios-game-studio.
//
//  Like MemoryMatch, the package builds ONLY the pure, UI-free simulation core
//  (`SkyHopperCore`) and its tests, so `swift build` / `swift test` run anywhere with a Swift
//  toolchain. The model owns ALL gameplay (gravity, obstacles, collision, scoring) so it is fully
//  unit-tested without a simulator; the SpriteKit `SKScene` in `App/` is a thin renderer that
//  reads model state each frame, and the SwiftUI shell hosts it via `SpriteView`. That is the
//  "logic separated from rendering" doctrine applied to an action game.
//
import PackageDescription

let package = Package(
    name: "SkyHopper",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "SkyHopperCore", targets: ["SkyHopperCore"])
    ],
    targets: [
        .target(name: "SkyHopperCore"),
        .testTarget(name: "SkyHopperCoreTests", dependencies: ["SkyHopperCore"]),
    ]
)
