// swift-tools-version: 6.0
//
//  MemoryMatchMacDemo — a runnable macOS window that reuses the iOS game's pure core
//  (`MemoryMatchCore`) so you can play it with `swift run`, no Xcode project needed.
//  It demonstrates the payoff of a UI-free core: the same tested rules drive iOS and macOS.
//
import PackageDescription

let package = Package(
    name: "MemoryMatchMacDemo",
    platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../MemoryMatch")],
    targets: [
        .executableTarget(
            name: "MemoryMatchMacDemo",
            dependencies: [.product(name: "MemoryMatchCore", package: "MemoryMatch")]
        )
    ]
)
