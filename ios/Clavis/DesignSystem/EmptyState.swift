import SwiftUI

/// Canonical empty-state layout: 60pt dim mark → serif title → 13pt ink-3 body → stacked CTAs.
struct CXEmptyState<Actions: View>: View {
    let icon: AnyView           // typically `AnyView(ClavixMark(size: 60, dim: true))`
    let title: String
    let bodyText: String
    @ViewBuilder var actions: Actions

    @Environment(\.theme) private var theme

    var body: some View {
        VStack(spacing: 12) {
            icon
            Text(title)
                .font(CXFont.serif(20, weight: .medium))
                .foregroundStyle(theme.ink)
                .padding(.top, 4)
            Text(bodyText)
                .font(CXFont.sans(13))
                .foregroundStyle(theme.ink3)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 230)
            VStack(spacing: 8) { actions }
                .padding(.top, 12)
        }
        .padding(.vertical, 52)
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity)
    }
}

extension CXEmptyState where Actions == EmptyView {
    init(icon: AnyView, title: String, bodyText: String) {
        self.icon = icon
        self.title = title
        self.bodyText = bodyText
        self.actions = { EmptyView() }()
    }
}

#if DEBUG
struct CXEmptyState_Previews: PreviewProvider {
    static var previews: some View {
        CXEmptyState(
            icon: AnyView(ClavixMark(size: 60, dim: true)),
            title: "No holdings yet",
            bodyText: "Add a ticker to see your first composite rating."
        ) {
            PrimaryButton(title: "Connect brokerage", full: true)
            SecondaryButton(title: "Add manually", full: true)
            GhostButton(title: "Browse universe")
        }
        .background(Color.cxPage)
    }
}
#endif
