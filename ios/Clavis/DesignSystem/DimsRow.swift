import SwiftUI

/// Signature methodology entry-point: 5 tappable dimension cells in a strip.
/// Each cell opens its audit screen via `onTap`.
struct CXDimension: Identifiable {
    let id = UUID()
    let name: String       // "Financial Health"
    let abbrev: String     // "FIN"
    let score: Int         // 0…100
    let delta: Int         // grade delta vs yesterday
}

struct DimsRow: View {
    let dims: [CXDimension]
    var onTap: (CXDimension) -> Void = { _ in }

    @Environment(\.theme) private var theme

    var body: some View {
        HStack(spacing: 0) {
            ForEach(Array(dims.enumerated()), id: \.element.id) { idx, d in
                if idx > 0 {
                    Rectangle().fill(theme.rule).frame(width: 1)
                }
                Button { onTap(d) } label: {
                    VStack(alignment: .leading, spacing: 8) {
                        Eyebrow(text: d.abbrev)
                        Text("\(d.score)")
                            .font(CXFont.mono(18, weight: .semibold))
                            .foregroundStyle(theme.ink)
                        ScoreBar(score: d.score, height: 3, tone: dimTone(d.score))
                    }
                    .padding(.vertical, 12)
                    .padding(.horizontal, 8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("\(d.name), score \(d.score) of 100, delta \(d.delta)")
            }
        }
        .overlay(Rectangle().fill(theme.rule).frame(height: 1), alignment: .top)
    }
}

#if DEBUG
struct DimsRow_Previews: PreviewProvider {
    static var previews: some View {
        DimsRow(dims: [
            .init(name: "Financial Health", abbrev: "FIN", score: 82, delta: 1),
            .init(name: "News Sentiment",   abbrev: "NEWS", score: 41, delta: -2),
            .init(name: "Sector Exposure",  abbrev: "SEC", score: 68, delta: 0),
            .init(name: "Macro",            abbrev: "MAC", score: 55, delta: 0),
            .init(name: "Volatility",       abbrev: "VOL", score: 29, delta: -1),
        ])
        .padding(.horizontal, 20)
        .background(Color.cxPage)
    }
}
#endif
