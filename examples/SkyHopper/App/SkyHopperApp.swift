//
//  SkyHopperApp.swift
//  SkyHopper (app layer)
//
//  App entry point. Universal (iPhone + iPad), offline, no tracking/analytics/accounts.
//  Add App/ to an Xcode iOS app target that links the SkyHopperCore library.
//
import SwiftUI

@main
struct SkyHopperApp: App {
    var body: some Scene {
        WindowGroup {
            GameView()
        }
    }
}
