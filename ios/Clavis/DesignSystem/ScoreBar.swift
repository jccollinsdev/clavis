import SwiftUI

/// Horizontal 0–100 bar with quarter-tick separators.
struct ScoreBar: View {
    let score: Int                // 0…100
    var height: CGFloat = 4
    var tone: Color? = nil        // pass `dimTone(score)` for grade-toned fill

    @Environment(\.theme) private var theme

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle().fill(theme.rule2)
                Rectangle()
                    .fill(tone ?? theme.ink)
                    .frame(width: geo.size.width * CGFloat(min(max(score, 0), 100)) / 100)
                ForEach([0.25, 0.5, 0.75], id: \.self) { t in
                    Rectangle()
                        .fill(theme.page)
                        .frame(width: 1)
                        .offset(x: geo.size.width * CGFloat(t))
                }
            }
        }
        .frame(height: height)
        .clipShape(RoundedRectangle(cornerRadius: 2))
        .accessibilityLabel("Score \(score) out of 100")
    }
}

/// Tone matching the 4-band grading: ≥75 good · 50…74 ink · 30…49 warn · <30 bad.
func dimTone(_ score: Int) -> Color {
    switch score {
    case 75...:   return .cxGood
    case 50..<75: return .cxInk
    case 30..<50: return .cxWarn
    default:      return .cxBad
    }
}

#if DEBUG
struct ScoreBar_Previews: PreviewProvider {
    static var previews: some View {
        VStack(alignment: .leading, spacing: 16) {
            ForEach([92, 72, 50, 38, 18], id: \.self) { s in
                VStack(alignment: .leading, spacing: 6) {
                    Text("Score \(s)")
                        .font(CXFont.mono(11, weight: .semibold))
                    ScoreBar(score: s, height: 4, tone: dimTone(s))
                }
            }
        }
        .padding(20)
        .background(Color.cxPage)
    }
}
#endif
