//
//  ScoreHistoryChart.swift  (template)
//  Swift iOS Game Studio — stats-screen score chart
//
//  A reusable SwiftUI stats chart. NOT for the per-frame HUD: a `Chart` rebuilds and
//  relays out its marks on every value change, so it belongs on paused / results / stats
//  screens, never inside `SKScene.update(_:)`, `TimelineView(.animation)`, or a render loop.
//  `ScoreSample` is a value type the PURE model fills (aggregate there); this view only plots.
//

import Charts
import SwiftUI

// MARK: - Model (value type — the model fills it, the chart never computes it)

/// One immutable, already-aggregated sample. A stable `id` lets Charts diff marks across
/// redraws instead of rebuilding the plot, so animations stay correct and relayout is cheap.
struct ScoreSample: Identifiable, Equatable, Codable, Sendable {
    let id: Int  // run index, stable & sortable
    let session: Int
    let score: Int
}

extension Array where Element == ScoreSample {
    /// Keep only the most recent `limit` samples so the chart never draws thousands of marks
    /// (which would tank scrolling and flood VoiceOver). Cap once here, not inside `body`.
    func capped(to limit: Int = 30) -> [ScoreSample] {
        suffix(limit).map { $0 }
    }
}

// MARK: - View

/// Line chart of recent scores with an optional personal-best rule. Pass already-aggregated,
/// capped data — see the file header. The view reads precomputed values; it does no math.
struct ScoreHistoryChart: View {
    let points: [ScoreSample]
    var best: Int?

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// One-line, non-visual summary so the whole chart reads as a sentence under VoiceOver.
    private var summary: String {
        guard let last = points.last else { return "No scores yet." }
        let bestText = best.map { ", best \($0)" } ?? ""
        return "Latest score \(last.score) over \(points.count) sessions\(bestText)."
    }

    var body: some View {
        Chart(points) { point in
            LineMark(
                x: .value("Session", point.session),
                y: .value("Score", point.score)
            )
            .interpolationMethod(.monotone)

            PointMark(
                x: .value("Session", point.session),
                y: .value("Score", point.score)
            )
            .symbolSize(80)
            .accessibilityLabel("Session \(point.session)")
            .accessibilityValue("\(point.score) points")

            if let best {
                RuleMark(y: .value("Best", best))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4]))
                    .foregroundStyle(.secondary)
                    .annotation(position: .top, alignment: .leading) {
                        Text("Best \(best)").font(.caption2).foregroundStyle(.secondary)
                    }
            }
        }
        .chartYScale(domain: .automatic(includesZero: true))
        .chartXAxisLabel("Session")
        .chartYAxisLabel("Score")
        .frame(minHeight: 180)
        .animation(reduceMotion ? nil : .default, value: points)
        .accessibilityLabel("Score history")
        .accessibilityValue(summary)
    }
}

// MARK: - Preview

#Preview {
    let sample = (0..<12).map { ScoreSample(id: $0, session: $0 + 1, score: 40 + $0 * 7) }
    return ScoreHistoryChart(points: sample.capped(), best: 130)
        .padding()
}
