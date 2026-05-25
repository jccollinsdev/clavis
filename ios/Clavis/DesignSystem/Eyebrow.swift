import SwiftUI

/// Mono, uppercase, ink-3. Used above every screen title and card title.
struct Eyebrow: View {
    let text: String
    enum Tone { case neutral, accent, good, warn, bad }
    var tone: Tone = .neutral

    @Environment(\.theme) private var theme

    var body: some View {
        Text(text.uppercased())
            .font(CXFont.mono(10, weight: .bold))
            .tracking(0.7)
            .foregroundStyle(color)
    }

    private var color: Color {
        switch tone {
        case .neutral: return theme.ink3
        case .accent:  return theme.accentColor
        case .good:    return .cxGood
        case .warn:    return .cxWarn
        case .bad:     return .cxBad
        }
    }
}

#if DEBUG
struct Eyebrow_Previews: PreviewProvider {
    static var previews: some View {
        VStack(alignment: .leading, spacing: 8) {
            Eyebrow(text: "Morning Report · May 9")
            Eyebrow(text: "Personalised", tone: .accent)
            Eyebrow(text: "AAA-grade", tone: .good)
            Eyebrow(text: "Pressure", tone: .warn)
            Eyebrow(text: "Downgrade", tone: .bad)
        }
        .padding(20)
        .background(Color.cxPage)
    }
}
#endif
