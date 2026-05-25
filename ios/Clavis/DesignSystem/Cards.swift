import SwiftUI

/// Base container: paper background, hairline border. `sunken` flips to paper2.
struct CXCard<Content: View>: View {
    @Environment(\.theme) private var theme
    var padding: CGFloat = 16
    var sunken: Bool = false
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .background(sunken ? theme.paper2 : theme.paper)
            .overlay(
                RoundedRectangle(cornerRadius: CXRadius.lg)
                    .stroke(theme.rule, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: CXRadius.lg))
    }
}

/// Accent-tinted card with a 3pt accent left-rule. For personalised / Pro CTAs.
struct AccentCard<Content: View>: View {
    @Environment(\.theme) private var theme
    var eyebrow: String? = nil
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: CXSpace.sm) {
            if let eyebrow { Eyebrow(text: eyebrow, tone: .accent) }
            content
        }
        .padding(CXSpace.lg)
        .background(theme.accentSoft)
        .overlay(
            Rectangle().fill(theme.accentColor).frame(width: 3),
            alignment: .leading
        )
        .clipShape(RoundedRectangle(cornerRadius: CXRadius.md))
    }
}

#if DEBUG
struct Cards_Previews: PreviewProvider {
    static var previews: some View {
        VStack(spacing: 16) {
            CXCard {
                VStack(alignment: .leading, spacing: 8) {
                    Eyebrow(text: "Composite")
                    Text("Portfolio rated BBB")
                        .font(CXFont.serif(22, weight: .medium))
                    Text("Composite fell from 73 to 64 over five sessions; News drove −7 of the change.")
                        .font(CXFont.sans(13))
                        .foregroundStyle(Color.cxInk3)
                }
            }
            AccentCard(eyebrow: "★ Personalised") {
                VStack(alignment: .leading, spacing: 4) {
                    Text("NVDA dragged the basket")
                        .font(CXFont.serif(20, weight: .medium))
                    Text("Largest negative contribution today, −9 to composite.")
                        .font(CXFont.sans(13))
                        .foregroundStyle(Color.cxAccentInk)
                }
            }
            CXCard(sunken: true) {
                Text("Sunken card · paper2 background")
                    .font(CXFont.sans(13))
            }
        }
        .padding(20)
        .background(Color.cxPage)
    }
}
#endif
