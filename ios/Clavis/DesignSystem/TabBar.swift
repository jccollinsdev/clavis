import SwiftUI

/// 5-tab bottom navigation. Today · Holdings · Search · Alerts · Settings.
enum CXTab: String, CaseIterable, Identifiable {
    case today, holdings, search, alerts, settings

    var id: String { rawValue }
    var label: String { rawValue.capitalized }

    var systemIcon: String {
        switch self {
        case .today:    return "doc.text"
        case .holdings: return "list.bullet.rectangle"
        case .search:   return "magnifyingglass"
        case .alerts:   return "bell"
        case .settings: return "gearshape"
        }
    }
}

struct CXTabBar: View {
    @Binding var active: CXTab
    @Environment(\.theme) private var theme

    var body: some View {
        HStack(spacing: 0) {
            ForEach(CXTab.allCases) { t in
                let isOn = active == t
                Button { active = t } label: {
                    VStack(spacing: 3) {
                        Image(systemName: t.systemIcon)
                            .font(.system(size: 18, weight: .regular))
                        Text(t.label)
                            .font(CXFont.sans(10, weight: isOn ? .semibold : .medium))
                    }
                    .foregroundStyle(isOn ? theme.accentColor : theme.ink4)
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(t.label)
                .accessibilityAddTraits(isOn ? [.isSelected, .isButton] : [.isButton])
            }
        }
        .padding(.top, 8).padding(.bottom, 4)
        .background(theme.paper)
        .overlay(Rectangle().fill(theme.rule).frame(height: 1), alignment: .top)
    }
}

#if DEBUG
struct CXTabBar_Previews: PreviewProvider {
    struct Wrap: View {
        @State var t: CXTab = .today
        var body: some View {
            VStack {
                Spacer()
                CXTabBar(active: $t)
            }
            .background(Color.cxPage)
        }
    }
    static var previews: some View { Wrap() }
}
#endif
