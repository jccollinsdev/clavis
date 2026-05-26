import SwiftUI

struct ClavisStandardCard<Content: View>: View {
    let fill: Color
    let padding: CGFloat
    @ViewBuilder let content: Content

    init(fill: Color = .clavixPaper, padding: CGFloat = ClavisTheme.cardPadding, @ViewBuilder content: () -> Content) {
        self.fill = fill
        self.padding = padding
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            content
        }
        .padding(padding)
        .clavisCardStyle(fill: fill)
    }
}

struct ClavisFlushListCard<Content: View>: View {
    let fill: Color
    let padding: CGFloat
    @ViewBuilder let content: Content

    init(fill: Color = .clavixPaper, padding: CGFloat = 14, @ViewBuilder content: () -> Content) {
        self.fill = fill
        self.padding = padding
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            content
        }
        .padding(.horizontal, padding)
        .padding(.vertical, 2)
        .background(fill)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .stroke(Color.clavixRule, lineWidth: 1)
        )
    }
}

struct ClavisRaisedControlSurface<Content: View>: View {
    let padding: CGFloat
    @ViewBuilder let content: Content

    init(padding: CGFloat = 12, @ViewBuilder content: () -> Content) {
        self.padding = padding
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            content
        }
        .padding(padding)
        .background(Color.clavixPaper2)
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous)
                .stroke(Color.clavixRule, lineWidth: 1)
        )
    }
}

struct ClavisSelectablePill: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                .foregroundColor(isSelected ? .white : .clavixInk3)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 7)
                .background(isSelected ? Color.clavixAccent : Color.clear)
                .overlay(
                    RoundedRectangle(cornerRadius: 6, style: .continuous)
                        .stroke(isSelected ? Color.clavixAccent : Color.clavixRule, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
        }
        .buttonStyle(.plain)
    }
}
