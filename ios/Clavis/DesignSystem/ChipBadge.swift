import SwiftUI

/// Outlined accent chip. Used for `★ PRO` and `★ PERSONALISED` micro-badges.
struct ChipBadge: View {
    let label: String
    enum Kind { case pro, personalised }
    var kind: Kind = .pro

    @Environment(\.theme) private var theme

    var body: some View {
        Text(label.uppercased())
            .font(CXFont.mono(10, weight: .bold))
            .tracking(0.4)
            .padding(.horizontal, 5).padding(.vertical, 2)
            .foregroundStyle(theme.accentColor)
            .overlay(
                RoundedRectangle(cornerRadius: 3)
                    .stroke(theme.accentColor, lineWidth: 1)
            )
    }
}

#if DEBUG
struct ChipBadge_Previews: PreviewProvider {
    static var previews: some View {
        HStack(spacing: 12) {
            ChipBadge(label: "★ PRO")
            ChipBadge(label: "★ PERSONALISED", kind: .personalised)
        }
        .padding(20)
        .background(Color.cxPage)
    }
}
#endif
