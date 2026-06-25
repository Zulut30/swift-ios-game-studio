//
//  MemoryMatchApp.swift
//  MemoryMatch (app layer)
//
//  App entry point. Universal (iPhone + iPad), offline, no tracking/analytics/accounts.
//  Add this file and the rest of App/ to an Xcode iOS app target that links MemoryMatchCore.
//
import SwiftUI

@main
struct MemoryMatchApp: App {
    var body: some Scene {
        WindowGroup {
            GameView()
        }
    }
}
