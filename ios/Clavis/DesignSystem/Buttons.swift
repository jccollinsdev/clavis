import SwiftUI

/// Ink-filled call-to-action. 48pt tall.
struct PrimaryButton: View {
    let title: String
    var full: Bool = false
    var action: () -> Void = {}

    @Environment(\.theme) private var theme

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(CXFont.sans(15, weight: .semibold))
                .frame(maxWidth: full ? .infinity : nil)
                .frame(height: 48)
                .padding(.horizontal, full ? 0 : 24)
                .foregroundStyle(theme.paper)
                .background(theme.ink)
                .clipShape(RoundedRectangle(cornerRadius: CXRadius.md))
        }
        .buttonStyle(.plain)
    }
}

/// Outlined neutral button. 48pt tall.
struct SecondaryButton: View {
    let title: String
    var full: Bool = false
    var action: () -> Void = {}

    @Environment(\.theme) private var theme

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(CXFont.sans(15, weight: .medium))
                .frame(maxWidth: full ? .infinity : nil)
                .frame(height: 48)
                .padding(.horizontal, full ? 0 : 24)
                .foregroundStyle(theme.ink)
                .overlay(
                    RoundedRectangle(cornerRadius: CXRadius.md)
                        .stroke(theme.rule, lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
    }
}

/// Tertiary accent-text button. No background.
struct GhostButton: View {
    let title: String
    var action: () -> Void = {}

    @Environment(\.theme) private var theme

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(CXFont.sans(14, weight: .medium))
                .foregroundStyle(theme.accentColor)
        }
        .buttonStyle(.plain)
    }
}

#if DEBUG
struct Buttons_Previews: PreviewProvider {
    static var previews: some View {
        VStack(spacing: 12) {
            PrimaryButton(title: "Continue", full: true)
            SecondaryButton(title: "Skip for now", full: true)
            HStack {
                PrimaryButton(title: "Confirm")
                SecondaryButton(title: "Cancel")
            }
            GhostButton(title: "Forgot password?")
        }
        .padding(20)
        .background(Color.cxPage)
    }
}
#endif
