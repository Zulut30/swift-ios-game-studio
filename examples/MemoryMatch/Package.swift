// swift-tools-version: 6.0
//
//  MemoryMatch — reference game for the swift-ios-game-studio skill.
//
//  The package builds ONLY the pure, UI-free game core (`MemoryMatchCore`) and its tests, so
//  `swift build` / `swift test` run anywhere with a Swift toolchain — no simulator needed.
//  The SwiftUI/app layer lives in `App/` (outside the SPM targets) and is meant to be added to
//  an Xcode iOS app target. This is the "logic separated from rendering" pattern in practice.
//
import PackageDescription

let package = Package(
    name: "MemoryMatch",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "MemoryMatchCore", targets: ["MemoryMatchCore"]),
    ],
    targets: [
        .target(name: "MemoryMatchCore"),
        .testTarget(
            name: "MemoryMatchCoreTests",
            dependencies: ["MemoryMatchCore"]
        ),
    ]
)
