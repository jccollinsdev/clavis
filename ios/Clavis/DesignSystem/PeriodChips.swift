import SwiftUI

/// Segmented control sized for inline use. Default: 1D / 1W / 1M / 3M / 1Y / 5Y.
struct PeriodChips: View {
    @Binding var value: String
    var options: [String] = ["1D", "1W", "1M", "3M", "1Y", "5Y"]

    @Environment(\.theme) private var theme

    var body: some View {
        HStack(spacing: 0) {
            ForEach(options, id: \.self) { o in
                let isOn = o == value
                Text(o)
                    .font(CXFont.mono(11, weight: .semibold))
                    .tracking(0.3)
                    .padding(.vertical, 5)
                    .frame(maxWidth: .infinity)
                    .foregroundStyle(isOn ? theme.paper : theme.ink3)
                    .background(isOn ? theme.ink : .clear)
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                    .contentShape(Rectangle())
                    .onTapGesture { value = o }
                    .accessibilityLabel("Period \(o)")
                    .accessibilityAddTraits(isOn ? [.isSelected, .isButton] : [.isButton])
            }
        }
        .padding(2)
        .background(theme.paper)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(theme.rule, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

#if DEBUG
struct PeriodChips_Previews: PreviewProvider {
    struct Wrap: View {
        @State var v: String = "1M"
        var body: some View {
            PeriodChips(value: $v)
                .padding(20)
                .background(Color.cxPage)
        }
    }
    static var previews: some View { Wrap() }
}
#endif
