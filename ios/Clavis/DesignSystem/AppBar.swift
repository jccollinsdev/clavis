import SwiftUI

/// Hero header used on root screens (Today, Holdings).
/// Mono eyebrow → serif 32pt title → optional subtitle, with trailing actions.
struct LargeAppBar<Trailing: View>: View {
    let eyebrow: String
    let title: String
    var subtitle: String? = nil
    @ViewBuilder var trailing: Trailing

    @Environment(\.theme) private var theme

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Eyebrow(text: eyebrow)
                Spacer()
                HStack(spacing: 14) { trailing }
                    .foregroundStyle(theme.ink)
            }
            .frame(minHeight: 32)

            Text(title)
                .font(CXFont.serif(32, weight: .medium))
                .tracking(-0.6)
                .foregroundStyle(theme.ink)
                .padding(.top, 4)

            if let subtitle {
                Text(subtitle)
                    .font(CXFont.sans(13))
                    .foregroundStyle(theme.ink3)
            }
        }
        .padding(.horizontal, CXSpace.xl)
        .padding(.top, 4)
        .padding(.bottom, 14)
        .background(theme.page)
    }
}

extension LargeAppBar where Trailing == EmptyView {
    init(eyebrow: String, title: String, subtitle: String? = nil) {
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.trailing = { EmptyView() }()
    }
}

#if DEBUG
struct LargeAppBar_Previews: PreviewProvider {
    static var previews: some View {
        VStack(spacing: 0) {
            LargeAppBar(
                eyebrow: "Morning Report · May 9",
                title: "Composite holding at BBB",
                subtitle: "Five sessions of erosion; news the primary driver."
            ) {
                Image(systemName: "bell")
            }
            Spacer()
        }
        .background(Color.cxPage)
        .frame(width: 360, height: 220)
    }
}
#endif
