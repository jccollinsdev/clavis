import SwiftUI

/// 1pt rule. Use `inset` for indented dividers (typical: leading icon column).
struct Hairline: View {
    @Environment(\.theme) private var theme
    var inset: CGFloat = 0

    var body: some View {
        Rectangle()
            .fill(theme.rule)
            .frame(height: 1)
            .padding(.horizontal, inset)
    }
}

#if DEBUG
struct Hairline_Previews: PreviewProvider {
    static var previews: some View {
        VStack(spacing: 12) {
            Hairline()
            Hairline(inset: 20)
        }
        .padding(20)
        .background(Color.cxPage)
    }
}
#endif
