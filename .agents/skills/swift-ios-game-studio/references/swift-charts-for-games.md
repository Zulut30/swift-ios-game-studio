# Swift Charts for game stats

Swift Charts (`import Charts`, iOS 16+) turns the numbers your game already tracks — scores, times,
accuracy, stars — into score history, per-run breakdowns, and end-of-run summaries. It is a
**view-layer** tool for **stats screens, not the game loop**: a `Chart` builds a fresh view tree and
re-lays out every mark on each value change, which is fine once per screen and ruinous every frame.

Two rules anchor everything below:

- **The model owns the stats; the chart only plots them.** Keep stats as plain `Codable`, `Sendable`
  value types (a `StatsSummary` / `[ScorePoint]`) that the pure model computes and unit-tests. If you
  are summing, averaging, bucketing, or capping inside a `Chart { … }` builder, that math belongs in
  the model — this is the logic-vs-rendering rule (ios-game-architecture.md) applied to charts. The
  files that import `Charts`/`SwiftUI` never import each other's concerns: stat types carry no UI,
  chart views carry no aggregation.
- **Charts live on `paused` / `win`/`lose` / a stats route — never on `playing`.** Never put a `Chart`
  in `SKScene.update(_:)`, a `TimelineView(.animation)` body, a `CADisplayLink` callback, or any
  per-frame path; for a live HUD readout use a single `Text` updated only on change (Swift quality bar
  rule 9). Feed charts pre-aggregated, bounded data with stable `Identifiable` ids so SwiftUI diffs
  marks instead of rebuilding the plot.

These charts are also how the **balance-economist** visualizes tuning curves offline — difficulty
ramps, XP/coin economy, drop rates, win-rate by level — turning a balance spreadsheet into a readable
plot. Same rules apply: it is an authoring/stats surface, never shipped into the live loop.

Accessibility and kids-privacy are non-negotiable: every mark gets a label, no meaning rides on color
alone, motion honors Reduce Motion, and a child's stats stay **local and on-device** — no
leaderboards, no network, no analytics, no streak-pressure dark patterns. See
accessibility-child-safety.md for the broader posture; this reference covers the chart-specific APIs.

> **Availability.** `LineMark`, `BarMark`, `PointMark`, `RuleMark`, `AreaMark` are iOS 16+.
> `SectorMark` (pie/donut) is **iOS 17+** — gate it with `if #available(iOS 17, *)` or fall back
> to a `BarMark` breakdown. Set the package/target deployment accordingly.

## charts-for-game-stats

Swift Charts (`import Charts`, iOS 16+) turns the numbers your game already tracks — scores,
times, accuracy — into score history, per-run breakdowns, and end-of-run summaries. It is a
**view-layer** tool. Charts read value-typed stats the model already computed; a chart never
computes a stat. If you find yourself summing, averaging, or bucketing inside a `Chart { … }`
builder, that math belongs in the model.

> **Availability.** `LineMark`, `BarMark`, `PointMark`, `RuleMark`, `AreaMark` are iOS 16+.
> `SectorMark` (pie/donut) is **iOS 17+** — gate it with `if #available(iOS 17, *)` or fall back
> to a `BarMark` breakdown. Set the package/target deployment accordingly.

### When a chart beats a number

A single number (`Best: 1240`) is clearer and cheaper than a chart — don't draw a chart to show
one value. Reach for a chart only when the **shape across many values** is the message:

| Use a chart when… | Mark | Skip it when… |
|---|---|---|
| Showing a trend across runs/days (improving? plateauing?) | `LineMark` (+ `PointMark`) | One latest value → just `Text` |
| Comparing parts of one run (time per level, points per stage) | `BarMark` | Two values → "12s vs 9s" reads fine |
| Showing composition/distribution (hits vs misses, star tiers) | `SectorMark` / stacked `BarMark` | A single percentage → a ring/`Gauge` |
| Marking a personal-best or target inside a series | `RuleMark` annotation | No reference point exists |

Kids skew young: prefer one chart with big marks and a short caption over a dense dashboard.

### The model owns the stats (value types only)

Define plain, `Codable`, `Sendable` value types. The model fills them; the view only plots them.
No `import Charts` and no `import SwiftUI` in this file.

```swift
//
//  GameStats.swift
//  Swift iOS Game Studio — value-typed stats for the view layer to plot
//
//  Pure Swift: no Charts/SwiftUI imports. All aggregation lives here so it is unit-testable
//  and the chart stays "dumb": it renders these structs, it does not compute them.
//

import Foundation

// MARK: - Score history (one point per completed run)

/// One finished run, ready to plot as a time series.
struct ScorePoint: Identifiable, Hashable, Codable, Sendable {
    let id: Int  // run index, stable & sortable
    let date: Date
    let score: Int
}

// MARK: - Per-run breakdown (one bar per level)

struct LevelResult: Identifiable, Hashable, Codable, Sendable {
    let id: Int  // level number
    var levelName: String
    var seconds: Double  // time spent on this level
}

// MARK: - Distribution (one slice per outcome category)

struct OutcomeSlice: Identifiable, Hashable, Codable, Sendable {
    let id: String  // "Perfect", "Good", "Missed"
    var count: Int
}

// MARK: - Aggregate that the stats screen reads

struct StatsSummary: Codable, Sendable {
    var history: [ScorePoint]
    var lastRun: [LevelResult]
    var outcomes: [OutcomeSlice]

    /// Best score so far — computed ONCE here, not inside the chart.
    var personalBest: Int { history.map(\.score).max() ?? 0 }
}
```

### Score history — `LineMark` with a personal-best `RuleMark`

A trend line answers "am I getting better?". Add a `PointMark` so single runs stay visible, and a
`RuleMark` to anchor the personal best. The view receives `[ScorePoint]` and a best `Int` already
computed by the model.

```swift
//
//  ScoreHistoryChart.swift
//  Swift iOS Game Studio — score-over-time view (reads model-supplied stats)
//

import Charts
import SwiftUI

// MARK: - Score history

struct ScoreHistoryChart: View {
    let history: [ScorePoint]
    let personalBest: Int

    var body: some View {
        Chart {
            ForEach(history) { point in
                LineMark(
                    x: .value("Run", point.id),
                    y: .value("Score", point.score)
                )
                .interpolationMethod(.catmullRom)

                PointMark(
                    x: .value("Run", point.id),
                    y: .value("Score", point.score)
                )
                .symbolSize(80)
            }

            RuleMark(y: .value("Best", personalBest))
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4]))
                .foregroundStyle(.secondary)
                .annotation(position: .top, alignment: .leading) {
                    Text("Best \(personalBest)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
        }
        .chartYScale(domain: 0...max(personalBest, 1))
        .chartXAxisLabel("Run")
        .chartYAxisLabel("Score")
        .frame(height: 220)
        .accessibilityLabel("Score history")
        .accessibilityValue("\(history.count) runs, best \(personalBest)")
    }
}
```

### Per-run breakdown — `BarMark`

One bar per level shows where time went this run. Color by category with `.foregroundStyle(by:)`
so the legend reads itself; never recompute the values here.

```swift
// MARK: - Per-run breakdown

struct RunBreakdownChart: View {
    let results: [LevelResult]

    var body: some View {
        Chart(results) { result in
            BarMark(
                x: .value("Level", result.levelName),
                y: .value("Seconds", result.seconds)
            )
            .foregroundStyle(by: .value("Level", result.levelName))
            .annotation(position: .top) {
                Text(result.seconds, format: .number.precision(.fractionLength(1)))
                    .font(.caption2)
            }
            // Per-mark accessibility so VoiceOver reads each bar.
            .accessibilityLabel(result.levelName)
            .accessibilityValue("\(result.seconds.formatted(.number.precision(.fractionLength(1)))) seconds")
        }
        .chartLegend(.hidden)
        .frame(height: 200)
        .accessibilityLabel("Time per level this run")
    }
}
```

### Distribution — `SectorMark` (iOS 17+) with a `BarMark` fallback

A pie/donut suits a small, fixed set of outcome buckets (Perfect / Good / Missed). Keep slices few
and labeled; gate on iOS 17 and degrade gracefully.

```swift
// MARK: - Outcome distribution

struct OutcomeChart: View {
    let outcomes: [OutcomeSlice]

    private var total: Int { outcomes.map(\.count).reduce(0, +) }

    var body: some View {
        Group {
            if #available(iOS 17, *) {
                Chart(outcomes) { slice in
                    SectorMark(
                        angle: .value("Count", slice.count),
                        innerRadius: .ratio(0.55),  // donut keeps a calm center
                        angularInset: 1.5
                    )
                    .foregroundStyle(by: .value("Outcome", slice.id))
                    .accessibilityLabel(slice.id)
                    .accessibilityValue("\(slice.count) of \(total)")
                }
            } else {
                // Fallback: a stacked bar conveys the same proportions on iOS 16.
                Chart(outcomes) { slice in
                    BarMark(x: .value("Count", slice.count))
                        .foregroundStyle(by: .value("Outcome", slice.id))
                }
                .chartXAxis(.hidden)
                .frame(height: 60)
            }
        }
        .frame(maxWidth: 260)
        .accessibilityLabel("Outcome distribution")
        .accessibilityValue("\(total) attempts")
    }
}
```

### End-of-run summary & a stats screen

The end-of-run card shows *this run* (breakdown + outcomes); the stats screen shows *history*. Both
take the model's `StatsSummary` — they read, they don't compute. Lead with the headline number, then
the chart that explains it.

```swift
// MARK: - End-of-run summary card

struct RunSummaryCard: View {
    let summary: StatsSummary
    let thisRunScore: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Score \(thisRunScore)")
                .font(.largeTitle.bold())
                .accessibilityAddTraits(.isHeader)

            RunBreakdownChart(results: summary.lastRun)
            OutcomeChart(outcomes: summary.outcomes)
        }
        .padding()
    }
}

// MARK: - Stats screen (history over time)

struct StatsScreen: View {
    let summary: StatsSummary

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Your progress").font(.title2.bold())
                    .accessibilityAddTraits(.isHeader)

                if summary.history.count < 2 {
                    // A trend needs at least two points; a number is better here.
                    ContentUnavailableView(
                        "Play a few rounds",
                        systemImage: "chart.line.uptrend.xyaxis",
                        description: Text("Your score history shows up after more runs.")
                    )
                } else {
                    ScoreHistoryChart(
                        history: summary.history,
                        personalBest: summary.personalBest
                    )
                }
            }
            .padding()
        }
    }
}
```

### Accessibility

- **Audio Graphs come almost free.** Add `.accessibilityChartDescriptor(...)` or rely on per-mark
  `.accessibilityLabel`/`.accessibilityValue` so VoiceOver users get a sonified, navigable chart.
  Label *every* mark — a chart with no per-mark labels is opaque to VoiceOver.
- **Never encode meaning in color alone** (quality bar #10). Pair `.foregroundStyle(by:)` with a
  legend, axis labels, or value annotations; distinguish series by `.symbol(by:)` too.
- **Honor Dynamic Type** — annotations and axis text use text styles (`.caption`, `.caption2`), not
  fixed point sizes; verify at the largest accessibility sizes.
- **Reduce Motion** — if you animate a chart on appear, gate it:
  `@Environment(\.accessibilityReduceMotion)` → skip the animation when true.
- Provide a **non-chart summary line** ("Best 1240, up from 980") so the data is reachable without
  reading the chart at all.

### Kids notes

- **Keep stats local and on-device.** History persists via the model's `Codable` save (UserDefaults
  or a JSON file). **No streaks-as-pressure, no leaderboards, no network, no analytics** — these are
  the child's own numbers, shown only to them. (See accessibility-child-safety.md.)
- **No dark patterns in stat framing.** Don't weaponize "you missed your daily streak" or nag toward
  purchases; a stats screen is for encouragement, not retention manipulation.
- **Big, few, friendly marks.** Large symbols, 3–5 bars/slices max, plain-language captions; avoid
  dense multi-series dashboards for young players.
- **Format numbers and dates with the user's locale** (`.formatted(...)`) so the screen reads
  naturally everywhere, with no hardcoded English strings.

## charts-accessibility

A score chart or progress dashboard is UI like any other: it must be readable without sight,
without color discrimination, and without fast motion — and for kids' games it must stay simple and
keep all data on device. Swift Charts gives you per-mark accessibility plus a full **Audio Graph**
(VoiceOver "hears" the data as a tone sweep). Wire both. See accessibility-child-safety.md for the
broader child-safety posture; this section covers the chart-specific APIs.

### Never encode meaning in color alone
Color-only series are invisible to color-blind players and to VoiceOver. Pair every series with a
**second channel** — a `symbol`/shape, a dash style, or a direct label — and a color-blind-safe
palette. `foregroundStyle(by:)` + `symbol(by:)` keyed on the *same* field gives one legend that
carries both cues.

```swift
import Charts
import SwiftUI

/// Okabe–Ito palette: distinguishable under the common color-vision deficiencies.
private let seriesPalette: [Color] = [
    Color(red: 0.00, green: 0.45, blue: 0.70),  // blue
    Color(red: 0.90, green: 0.62, blue: 0.00),  // orange
    Color(red: 0.00, green: 0.62, blue: 0.45),  // green
    Color(red: 0.80, green: 0.47, blue: 0.65),  // purple
]

Chart(runs) { run in
    LineMark(x: .value("Day", run.day), y: .value("Stars", run.stars))
        .foregroundStyle(by: .value("Player", run.player))  // color cue
        .symbol(by: .value("Player", run.player))  // shape cue (redundant on purpose)
        .interpolationMethod(.monotone)
}
.chartForegroundStyleScale(range: seriesPalette)
```

- For bars, distinguish by `symbol`-style overlays, pattern, or a value label, not hue alone.
- Keep strong contrast (WCAG AA: 3:1 for graphic objects); don't put pale marks on a pale canvas.

### Label every mark, axis, and series
`.value("Name", data)` already names the dimension — that string flows into VoiceOver. Add a
**per-mark** label/value so each data point reads as a full sentence, and keep axes explicitly
labeled rather than relying on bare numbers.

```swift
BarMark(x: .value("Level", level.name), y: .value("Stars", level.stars))
    .accessibilityLabel(level.name)
    .accessibilityValue("\(level.stars) of 3 stars")  // spoken, kid-readable
```

```swift
.chartXAxis { AxisMarks { AxisValueLabel().font(.caption) } }  // honors Dynamic Type
.chartYAxis { AxisMarks(values: .stride(by: 1)) { AxisValueLabel() } }
.chartXAxisLabel("Level", position: .bottom)
.chartYAxisLabel("Stars earned", position: .leading)
```

### VoiceOver Audio Graph (`AXChartDescriptor`)
Conform to `AXChartDescriptorRepresentable` and attach with `.accessibilityChartDescriptor(self)`.
VoiceOver then offers **"Describe Chart"** and an audio sweep that maps Y to pitch — powerful for a
child who can't see the screen. Define each axis once; map your data into series.

```swift
struct StarsChart: View, AXChartDescriptorRepresentable {
    let runs: [Run]

    var body: some View {
        Chart(runs) { run in
            LineMark(x: .value("Day", run.day), y: .value("Stars", run.stars))
                .symbol(by: .value("Player", run.player))
        }
        .accessibilityChartDescriptor(self)  // enables the Audio Graph
    }

    func makeChartDescriptor() -> AXChartDescriptor {
        let days = runs.map(\.day)
        let xAxis = AXNumericDataAxisDescriptor(
            title: "Day",
            range: Double(days.min() ?? 0)...Double(days.max() ?? 1),
            gridlinePositions: []
        ) { "Day \(Int($0))" }

        let yAxis = AXNumericDataAxisDescriptor(
            title: "Stars",
            range: 0...3,
            gridlinePositions: []
        ) { "\(Int($0)) stars" }

        let series = AXDataSeriesDescriptor(
            name: "Stars per day",
            isContinuous: true,
            dataPoints: runs.map {
                AXDataPoint(x: Double($0.day), y: Double($0.stars))
            }
        )

        return AXChartDescriptor(
            title: "Stars earned per day",
            summary: "Daily stars, 0 to 3.",
            xAxis: xAxis,
            yAxis: yAxis,
            additionalAxes: [],
            series: [series]
        )
    }
}
```

- The closures format spoken values — return kid-friendly text ("3 stars"), not raw doubles.
- For categorical X (level names) use `AXCategoricalDataAxisDescriptor(title:categoryOrder:)`.
- Keep `summary` to one short sentence; it's the first thing VoiceOver speaks.

### Dynamic Type
Use text styles (`.caption`, `.footnote`) for axis and annotation labels so they scale, and verify
the chart still reads at the largest accessibility sizes — give labels room or thin them with
`AxisMarks(values:)` rather than letting them overlap.

```swift
.chartXAxis { AxisMarks { AxisValueLabel().font(.caption) } }
```

### Reduce Motion — no animated draw-in
A chart that sweeps or grows on appear is motion. Gate any draw-in animation on Reduce Motion and
render the final state immediately when it's set.

```swift
@Environment(\.accessibilityReduceMotion) private var reduceMotion

Chart(runs) { run in
    BarMark(x: .value("Level", run.level), y: .value("Stars", run.stars))
}
.animation(reduceMotion ? nil : .easeOut(duration: 0.4), value: runs)
```

If you animate by clamping a `drawProgress` value (e.g. trimming the line), set it straight to its
final value under Reduce Motion instead of tweening it.

### Kids: keep dashboards simple, keep data on device
- **One idea per chart.** Stars per level, or attempts per day — not a multi-axis analytics panel.
  Few series, clear labels, big touch/inspect targets. Prefer concrete units a child knows ("stars",
  "tries") over percentages and rates.
- **No data leaves the device.** Charts render purely local progress (`Codable` saves in the app
  sandbox / `UserDefaults`). No analytics SDK, no network upload of play history, no leaderboards
  that transmit a child's stats. Aggregate stats are still personal data — keep them offline.
- **No comparison pressure.** Avoid ranking a child against others or against a "you're behind" bar;
  frame progress as the child's own growth.
- **Gate any export.** If a parent can share or export a progress chart, put it behind the parental
  gate — never in the child-facing flow.

## charts-perf-and-template

`Charts` is for **stats screens**, not the game loop. A `Chart` builds a fresh view tree and
re-lays out marks on every value change — fine once per screen, ruinous every frame.

### Never chart inside the game loop
- **Never** put a `Chart` inside `SKScene.update(_:)`, a `TimelineView(.animation)` body, a
  `CADisplayLink` callback, or any per-frame path. Charts is a layout-heavy SwiftUI view, not a
  HUD primitive. For a live score readout use a single `Text` updated only on change (quality bar
  rule 9); reserve charts for the pause/results/progress screen where the player is *reading*, not
  *playing*.
- The boundary is the state machine: charts belong to `paused` / `win`/`lose` / a stats route —
  never to `playing`.

### Aggregate and cap the data
- Feed the chart **pre-aggregated, bounded** data, not a raw event log. Cap to the last *N*
  samples (e.g. 30 sessions) or bucket by day/level; thousands of marks tank scroll performance
  and overwhelm VoiceOver.
- Aggregate in the pure model (testable, no UI imports), pass the finished `[ScorePoint]` in. Do
  the `suffix`/bucketing once, not in `body`.

### Stable identity → redraw only when stats change
- Make the data point `Identifiable` with a **stable** `id` so SwiftUI/Charts diff marks instead
  of rebuilding the plot — correct animations, fewer relayouts (quality bar rule, and matches the
  `ForEach` identity rule in swiftui-mastery.md).
- The chart redraws only when its input value changes. Hold stats in `@Observable` model state and
  gate animation on Reduce Motion. Don't bind a chart to per-frame state.

### Tie-in: balance-economist
The **balance-economist** uses this view to visualize tuning curves offline — difficulty ramps,
XP/coin economy, drop rates, win-rate by level — turning a balance spreadsheet into a readable
plot. Same rules: it's an authoring/stats surface, never shipped into the live loop.

### Reusable template (`ScoreHistoryChart`)
The full, verified template lives at `assets/stats-chart-template.swift` (parses clean with the
Swift 6 frontend; no line > 110 chars; 4-space indent; no force-unwrap on the optional `best`).
A condensed version:

```swift
//
//  ScoreHistoryChart.swift
//  Reusable stats-screen chart. NOT for per-frame HUD — see redraw note.
//

import Charts
import SwiftUI

// MARK: - Model

/// One immutable sample for the stats screen. `id` keeps marks stable across redraws.
struct ScorePoint: Identifiable, Equatable {
    let id: Int
    let session: Int
    let score: Int
}

// MARK: - View

/// Line chart of recent scores. Pass already-aggregated, capped data — see header.
struct ScoreHistoryChart: View {
    let points: [ScorePoint]
    var best: Int?

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var summary: String {
        guard let last = points.last else { return "No scores yet." }
        return "Latest score \(last.score) over \(points.count) sessions."
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

            if let best {
                RuleMark(y: .value("Best", best))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4]))
                    .annotation(position: .top, alignment: .leading) {
                        Text("Best \(best)")
                            .font(.caption2)
                    }
            }
        }
        .chartYScale(domain: .automatic(includesZero: true))
        .frame(minHeight: 180)
        .animation(reduceMotion ? nil : .default, value: points)
        .accessibilityLabel("Score history")
        .accessibilityValue(summary)
    }
}

// MARK: - Aggregation

extension Array where Element == ScorePoint {
    /// Keep the most recent `limit` samples so the chart never draws thousands of marks.
    func capped(to limit: Int = 30) -> [ScorePoint] {
        suffix(limit).map { $0 }
    }
}

// MARK: - Preview

#Preview {
    let sample = (0..<12).map { ScorePoint(id: $0, session: $0 + 1, score: 40 + $0 * 7) }
    return ScoreHistoryChart(points: sample, best: 130)
        .padding()
}
```

### Accessibility & kids notes
- Charts emits VoiceOver descriptions per mark; capping the data keeps that navigable. Add a
  one-line `.accessibilityLabel` + `.accessibilityValue` summary (above) so the whole chart reads
  as a single sentence first — Dynamic Type applies to the labels and annotation `Text`.
- Don't rely on color alone for series — use distinct symbols/positions (color-blind-safe), per
  art-and-graphics-pipeline.md.
- Kids apps: stats are **local and anonymous** — sourced from on-device persistence, never a
  leaderboard or network call, no identifiers, no analytics (see CLAUDE.md kids rules and
  apple-accounts-pay-and-data.md). A "score history" screen must not become a tracking surface.

## Common pitfalls

- **Computing stats inside the `Chart` builder.** Summing/averaging/bucketing/capping belongs in the
  pure-Swift model (a value-typed `StatsSummary` / `[ScorePoint]`); the chart must only plot
  precomputed structs. This is logic-vs-rendering applied to charts.
- **Charting inside the game loop.** A `Chart` in `SKScene.update(_:)`, a `TimelineView(.animation)`
  body, a `CADisplayLink`, or any per-frame path rebuilds and relays out every frame. Use a single
  `Text` for the live HUD; charts live only on paused/results/stats screens.
- **Feeding a raw, unbounded event log.** Thousands of marks tank scrolling and flood VoiceOver. Cap
  to the last *N* or bucket by day/level in the pure model, once — not in `body`.
- **Unstable or index-derived ids.** Without a stable `Identifiable` id, Charts rebuilds marks instead
  of diffing them — broken animations and extra relayout. Give `ScorePoint` a stable `id`.
- **Using `SectorMark` without an availability gate.** `SectorMark` (pie/donut) is iOS 17+, while
  `LineMark`/`BarMark`/`PointMark`/`RuleMark` are iOS 16+. Wrap it in `if #available(iOS 17, *)` and
  fall back to a stacked `BarMark`, or the package won't build on a 16.x deployment target.
- **Encoding category meaning in color alone.** `.foregroundStyle(by:)` on its own fails colorblind
  users and quality-bar #10; add a legend, axis label, value annotation, or `.symbol(by:)` — keyed on
  the *same* `.value` field so they merge into one legend.
- **Omitting per-mark `.accessibilityLabel`/`.accessibilityValue`.** Without them VoiceOver and Audio
  Graphs can't describe individual marks; a chart with only a container label is opaque.
- **Drawing a chart for one value or a <2-point series.** A number (or `Gauge`) beats a chart for one
  value; a trend `LineMark` needs ≥2 points — guard with `ContentUnavailableView` until enough runs
  exist.
- **Force-unwrapping the optional `best`/threshold.** Use `if let best` / `map` (quality bar rule 4).
- **Wrong accessibility names.** The protocol is `AXChartDescriptorRepresentable` (not `...Provider`);
  the modifier is `.accessibilityChartDescriptor(_:)`; the required method is `makeChartDescriptor()`.
  The numeric axis's value-formatting closure is required, not optional.
- **Reduce Motion half-honored.** Set the final chart state immediately (`.animation(nil, …)` or
  jumping `drawProgress` to its end value) — a fast sweep is still motion. Don't bind the chart to
  per-frame state so it animates constantly.
- **Adding leaderboards, network sync, analytics, or streak-pressure to a kids stats screen.** Stats
  stay local/on-device (`Codable` save), anonymous, with no retention dark patterns and any export
  behind a parental gate, per child-safety defaults.
- **Compliance is not automatic.** These are privacy-first defaults (data stays on device); don't
  claim COPPA / Kids-Category compliance — that still needs the user's own legal review per CLAUDE.md.

> **Verification.** The shipped `assets/stats-chart-template.swift` was checked with
> `swift -frontend -parse` (exit 0) and hand-verified against `.swift-format` (lineLength 110,
> 4-space indent, no tabs, no force-unwrap). `swift-format` is not installed in this environment;
> run `swift format lint --strict` in CI to confirm before relying on it.