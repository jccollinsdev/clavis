import SwiftUI

// MARK: - Theme Constants

enum ClavisTheme {
    static let cornerRadius: CGFloat = 4          // v2 sharp-box system
    static let innerCornerRadius: CGFloat = 0     // controls and inline surfaces
    static let sectionSpacing: CGFloat = 12
    static let cardPadding: CGFloat = 16
    static let screenPadding: CGFloat = 16
    static let microSpacing: CGFloat = 4
    static let smallSpacing: CGFloat = 8
    static let mediumSpacing: CGFloat = 16
    static let largeSpacing: CGFloat = 16
    static let extraLargeSpacing: CGFloat = 24
    static let topBarSpacing: CGFloat = 14
    static let floatingTabInset: CGFloat = 16
    static let floatingTabHeight: CGFloat = 74
}

// MARK: - Typography

enum ClavisTypography {
    // Inter — UI text
    static func inter(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        Font.custom("Inter", size: size).weight(weight)
    }
    // JetBrains Mono — all data and numbers
    static func mono(_ size: CGFloat) -> Font {
        Font.custom("JetBrainsMono-Regular", size: size)
    }

    // Spec-defined styles
    static let portfolioScore = mono(52)                     // portfolio hero score
    static let h1             = inter(28, weight: .semibold)  // screen title
    static let h2             = inter(20, weight: .semibold)  // section header
    static let dataNumber     = mono(22)                     // data/number display
    static let gradeTag       = mono(13)                     // grade badge label
    static let label          = inter(11, weight: .semibold)  // UPPERCASE labels
    static let rowTicker      = inter(13, weight: .semibold)   // ticker in rows
    static let rowScore       = mono(13)                     // score in rows
    static let bodySmall      = inter(13, weight: .regular)

    // Backward-compat aliases — existing views compile without changes
    static func appFont(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        inter(size, weight: weight)
    }
    static let dashboardTitle    = h1
    static let pageTitle         = h1
    static let sectionTitle      = h2
    static let cardTitle         = inter(15, weight: .semibold)
    static let body              = inter(15, weight: .regular)
    static let bodyStrong        = inter(15, weight: .semibold)
    static let bodyEmphasis      = inter(15, weight: .semibold)
    static let footnote          = inter(12, weight: .regular)
    static let footnoteEmphasis  = inter(12, weight: .semibold)
    static let metric            = mono(32)
    static let grade             = mono(36)
    static let heroNumber        = mono(48)
    static let heroLabel         = inter(24, weight: .medium)
    static let interpretation    = inter(15, weight: .regular)
    static let action            = inter(15, weight: .medium)
    static let topBarTitle       = h1
    static let eyebrow           = label
    static let brandTitle        = inter(18, weight: .bold)
    static let brandWordmark     = inter(18, weight: .bold)
}

// MARK: - Color Palette

extension Color {
    // MARK: V2 dark surfaces
    static let backgroundPrimary = Color(hex: "#0B0D12")
    static let surface           = Color(hex: "#14171E")
    static let surfaceElevated   = Color(hex: "#1B1F28")
    static let surfaceMuted      = Color(hex: "#101319")
    static let border            = Color(hex: "#242934")
    static let borderSubtleTone  = Color(hex: "#1E232D")

    // MARK: V2 typography colors
    static let textPrimary   = Color(hex: "#EEF1F5")
    static let textSecondary = Color(hex: "#8A93A3")
    static let textTertiary  = Color(hex: "#5A6374")

    // MARK: Wireframe token aliases
    static let ink        = textPrimary
    static let ink2       = Color(hex: "#CDD3DD")
    static let ink3       = textSecondary
    static let ink4       = Color(hex: "#9AA1AB")
    static let rule       = border
    static let rule2      = borderSubtleTone
    static let paper      = surface
    static let paper2     = surfaceElevated

    // MARK: V2 accent + semantic states
    static let accentBurnt = Color(hex: "#C2410C")
    static let accentSoft  = Color(hex: "#3D241A")
    static let accentInk   = Color(hex: "#F7E5D8")
    static let good        = Color(hex: "#1F6F43")
    static let goodSoft    = Color(hex: "#173124")
    static let warn        = Color(hex: "#A35A00")
    static let warnSoft    = Color(hex: "#382714")
    static let bad         = Color(hex: "#9A1D1D")
    static let badSoft     = Color(hex: "#341719")
    static let brandCream  = accentBurnt

    // MARK: Informational (non-risk blue — never near score displays)
    static let informational = Color(hex: "#3B82C4")

    // MARK: Risk Scale — 10-grade bond-rating closed set
    static let gradeCAAA = Color(hex: "#0C5E3A")  // Deep green  — AAA
    static let gradeCAA  = Color(hex: "#1D9E75")  // Green       — AA
    static let gradeCA   = Color(hex: "#45B88E")  // Light green — A
    static let gradeCBBB = Color(hex: "#3B8C8C")  // Teal        — BBB
    static let gradeCBB  = Color(hex: "#B39229")  // Amber       — BB
    static let gradeCB   = Color(hex: "#BA7517")  // Dark amber  — B
    static let gradeCCCC = Color(hex: "#D86A20")  // Orange      — CCC
    static let gradeCCC  = Color(hex: "#D85A30")  // Deep orange — CC
    static let gradeCC   = Color(hex: "#C83B30")  // Red         — C
    static let gradeCF   = Color(hex: "#A02020")  // Deep red    — F

    // MARK: Grade Tag Surfaces — 10-grade background/text pairs
    static let gradeAAABg   = Color(hex: "#D4EFE3")
    static let gradeAAAText = Color(hex: "#085041")
    static let gradeAABg    = Color(hex: "#DCF5E6")
    static let gradeAAText  = Color(hex: "#085041")
    static let gradeABg     = Color(hex: "#E1F5EE")
    static let gradeAText   = Color(hex: "#126B5C")
    static let gradeBBBBg   = Color(hex: "#DFF0EF")
    static let gradeBBBText = Color(hex: "#10555A")
    static let gradeBBBg    = Color(hex: "#FCF2E2")
    static let gradeBBText  = Color(hex: "#634B10")
    static let gradeBBg     = Color(hex: "#FAEEDA")
    static let gradeBText   = Color(hex: "#633806")
    static let gradeCCCBg   = Color(hex: "#FDEBDE")
    static let gradeCCCText = Color(hex: "#783A14")
    static let gradeCCBg    = Color(hex: "#FAECE7")
    static let gradeCCText  = Color(hex: "#712B13")
    static let gradeCBg     = Color(hex: "#FCEBEB")
    static let gradeCText   = Color(hex: "#791F1F")
    static let gradeFBg     = Color(hex: "#FADEDE")
    static let gradeFText   = Color(hex: "#6B1515")

    // MARK: Backward-compat aliases — legacy 5-state names
    static let riskA = gradeCAA   // old A → AA green
    static let riskB = gradeCA    // old B → A green  
    static let riskC = gradeCBB   // old C → BB amber
    static let riskD = gradeCCCC  // old D → CCC orange
    static let riskF = gradeCF    // old F → F red
    static let accentBlue         = informational
    static let accent             = accentBurnt
    static let canvasBackground   = backgroundPrimary
    static let cardBackground     = surface
    static let elevatedBackground = surfaceElevated
    static let appBackground      = backgroundPrimary
    static let surfacePrimary     = surface
    static let surfaceSecondary   = surfaceElevated
    static let borderSubtle       = borderSubtleTone
    static let borderStrong       = border
    static let successTone        = gradeCAA
    static let warningTone        = gradeCBB
    static let criticalTone       = gradeCF
    static let mint               = gradeCA
    static let trustNavy          = informational
    static let neutralSurface     = surfaceElevated
    static let clavisCardBorder   = border
    static let clavisShadow       = Color.clear
    static let clavisAlertText    = gradeCF
    static let clavisAlertBg      = gradeCF.opacity(0.12)
    static let successSurface     = gradeCAA.opacity(0.12)
    static let warningSurface     = gradeCBB.opacity(0.12)
    static let dangerSurface      = gradeCF.opacity(0.12)
    static let decisionSafe       = gradeCAA
    static let decisionElevated   = gradeCBB
    static let decisionReduce     = gradeCF
    static let decisionInfo       = textSecondary
    static let semanticGreen      = gradeCAA
    static let semanticAmber      = gradeCBB
    static let semanticRed        = gradeCF
    static let semanticBlue       = informational
    static let semanticGray       = textSecondary

    // Slate scale (backward compat — mapped to dark equivalents)
    static let slate900 = Color(hex: "#E8ECF0")
    static let slate700 = Color(hex: "#7A8799")
    static let slate500 = Color(hex: "#7A8799")
    static let slate300 = Color(hex: "#2A3140")
    static let slate200 = Color(hex: "#2A3140")
    static let slate100 = Color(hex: "#1E2530")

    // MARK: Hex initializer
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3:
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - Grade Style

enum ClavisGradeStyle {
    static func riskColor(for grade: String?) -> Color {
        switch grade {
        case "AAA": return .gradeCAAA
        case "AA":  return .gradeCAA
        case "A":   return .gradeCA
        case "BBB": return .gradeCBBB
        case "BB":  return .gradeCBB
        case "B":   return .gradeCB
        case "CCC": return .gradeCCCC
        case "CC":  return .gradeCCC
        case "C":   return .gradeCC
        case "F":   return .gradeCF
        default:    return .textSecondary
        }
    }

    /// Backward-compat alias
    static func color(for grade: String?) -> Color { riskColor(for: grade) }

    static func gradeBandBg(for grade: String?) -> Color {
        switch grade {
        case "AAA": return .gradeAAABg
        case "AA":  return .gradeAABg
        case "A":   return .gradeABg
        case "BBB": return .gradeBBBBg
        case "BB":  return .gradeBBBg
        case "B":   return .gradeBBg
        case "CCC": return .gradeCCCBg
        case "CC":  return .gradeCCBg
        case "C":   return .gradeCBg
        case "F":   return .gradeFBg
        default:    return .surfaceElevated
        }
    }

    static func gradeBandText(for grade: String?) -> Color {
        switch grade {
        case "AAA": return .gradeAAAText
        case "AA":  return .gradeAAText
        case "A":   return .gradeAText
        case "BBB": return .gradeBBBText
        case "BB":  return .gradeBBText
        case "B":   return .gradeBText
        case "CCC": return .gradeCCCText
        case "CC":  return .gradeCCText
        case "C":   return .gradeCText
        case "F":   return .gradeFText
        default:    return .textSecondary
        }
    }

    static func gradeBandLabel(for grade: String?) -> String {
        switch grade {
        case "AAA": return "Investment Grade (90\u{2013}100)"
        case "AA":  return "Strong (80\u{2013}89)"
        case "A":   return "Sound (70\u{2013}79)"
        case "BBB": return "Adequate (60\u{2013}69)"
        case "BB":  return "Speculative (50\u{2013}59)"
        case "B":   return "Vulnerable (40\u{2013}49)"
        case "CCC": return "Weak (30\u{2013}39)"
        case "CC":  return "Distressed (20\u{2013}29)"
        case "C":   return "Near Default (10\u{2013}19)"
        case "F":   return "Default (0\u{2013}9)"
        default:    return "\u{2014}"
        }
    }
}

// MARK: - View Modifiers

extension View {
    func clavisCardStyle(fill: Color = .surface) -> some View {
        background(fill)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .stroke(Color.border, lineWidth: 1)
            )
    }

    func clavisHeroCardStyle(fill: Color = .surface) -> some View {
        background(fill)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .stroke(Color.border, lineWidth: 1.5)
            )
    }

    func clavisSecondaryCardStyle(fill: Color = .surfaceElevated) -> some View {
        background(fill)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}

// MARK: - Atmosphere Background (flat dark — no gradient)

struct ClavisAtmosphereBackground: View {
    var body: some View {
        Color.backgroundPrimary
            .ignoresSafeArea()
    }
}

// MARK: - Grade Badge

enum GradeBadgeSize {
    case compact
    case standard
    case large
}

struct GradeBadge: View {
    let grade: String
    var size: GradeBadgeSize = .standard

    private var width: CGFloat {
        switch size {
        case .compact:  return 26
        case .standard: return 34
        case .large:    return 76
        }
    }

    private var height: CGFloat {
        switch size {
        case .compact:  return 20
        case .standard: return 26
        case .large:    return 76
        }
    }

    private var fontSize: CGFloat {
        switch size {
        case .compact:  return 13
        case .standard: return 13
        case .large:    return 40
        }
    }

    var body: some View {
        Text(grade)
            .font(.system(size: fontSize, weight: .bold, design: .monospaced))
            .foregroundColor(ClavisGradeStyle.gradeBandText(for: grade))
            .frame(width: width, height: height, alignment: .center)
            .background(ClavisGradeStyle.gradeBandBg(for: grade))
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}

// MARK: - Risk Direction Label

struct RiskDirectionLabel: View {
    let trend: RiskTrend

    private var color: Color {
        switch trend {
        case .worsening:  return .bad
        case .improving:  return .good
        case .stable:     return .textSecondary
        }
    }

    private var label: String {
        switch trend {
        case .worsening:  return "↓ worsening"
        case .improving:  return "↑ improving"
        case .stable:     return "→ stable"
        }
    }

    var body: some View {
        Text(label)
            .font(.system(size: 12, weight: .semibold, design: .monospaced))
            .foregroundColor(color)
            .accessibilityLabel(label.replacingOccurrences(of: "↑", with: "improving")
                .replacingOccurrences(of: "↓", with: "worsening")
                .replacingOccurrences(of: "→", with: "stable"))
    }
}

// MARK: - Evidence Dots

struct EvidenceDots: View {
    let evidence: EvidenceStrength
    var grade: String? = nil

    private var dotColor: Color {
        if let grade {
            return ClavisGradeStyle.riskColor(for: grade).opacity(0.4)
        }
        return .textSecondary.opacity(0.4)
    }

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3, id: \.self) { index in
                Circle()
                    .fill(index < evidence.dotCount ? dotColor : dotColor.opacity(0.25))
                    .frame(width: 5, height: 5)
                    .overlay(
                        Circle()
                            .stroke(dotColor, lineWidth: 0.5)
                            .frame(width: 5, height: 5)
                    )
            }
        }
        .accessibilityLabel("\(evidence.rawValue) evidence")
    }
}

struct CX2NavBar: View {
    let title: String?
    let subtitle: String?
    let transparent: Bool
    let showBorder: Bool
    private let leading: AnyView
    private let trailing: AnyView

    init(
        title: String? = nil,
        subtitle: String? = nil,
        transparent: Bool = false,
        showBorder: Bool = true,
        @ViewBuilder leading: () -> some View = { EmptyView() },
        @ViewBuilder trailing: () -> some View = { EmptyView() }
    ) {
        self.title = title
        self.subtitle = subtitle
        self.transparent = transparent
        self.showBorder = showBorder
        self.leading = AnyView(leading())
        self.trailing = AnyView(trailing())
    }

    var body: some View {
        HStack(alignment: .center, spacing: 8) {
            HStack {
                leading
            }
            .frame(width: 64, alignment: .leading)

            VStack(spacing: 1) {
                if let title, !title.isEmpty {
                    Text(title)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(.textPrimary)
                        .lineLimit(1)
                }

                if let subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .font(.system(size: 11, weight: .regular))
                        .foregroundColor(.textSecondary)
                        .lineLimit(1)
                }
            }
            .frame(maxWidth: .infinity)

            HStack(spacing: 6) {
                trailing
            }
            .frame(width: 64, alignment: .trailing)
        }
        .padding(.top, 18)
        .padding(.horizontal, 16)
        .padding(.bottom, 4)
        .background(transparent ? Color.clear : Color.backgroundPrimary)
        .overlay(alignment: .bottom) {
            if showBorder {
                Rectangle()
                    .fill(Color.borderSubtle)
                    .frame(height: 1)
            }
        }
    }
}

struct CX2LargeTitle: View {
    let title: String
    private let trailing: AnyView

    init(_ title: String, @ViewBuilder trailing: () -> some View = { EmptyView() }) {
        self.title = title
        self.trailing = AnyView(trailing())
    }

    var body: some View {
        HStack(alignment: .lastTextBaseline, spacing: 12) {
            Text(title)
                .font(.system(size: 28, weight: .semibold))
                .foregroundColor(.textPrimary)
                .tracking(-0.3)

            Spacer(minLength: 12)

            trailing
                .padding(.bottom, 2)
        }
        .padding(.horizontal, 16)
        .padding(.top, 4)
        .padding(.bottom, 6)
    }
}

struct CX2IconButton<Content: View>: View {
    let size: CGFloat
    let action: () -> Void
    @ViewBuilder let content: Content

    init(size: CGFloat = 32, action: @escaping () -> Void, @ViewBuilder content: () -> Content) {
        self.size = size
        self.action = action
        self.content = content()
    }

    var body: some View {
        Button(action: action) {
            content
                .frame(width: size, height: size)
                .foregroundColor(.textPrimary)
        }
        .buttonStyle(.plain)
    }
}

struct CX2SectionLabel: View {
    let text: String

    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 11, weight: .semibold))
            .foregroundColor(.textSecondary)
            .tracking(0.8)
    }
}

struct CX2Chevron: View {
    var body: some View {
        Image(systemName: "chevron.right")
            .font(.system(size: 11, weight: .semibold))
            .foregroundColor(.textTertiary)
    }
}

struct CX2Toggle: View {
    @Binding var isOn: Bool

    var body: some View {
        ZStack(alignment: isOn ? .trailing : .leading) {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(isOn ? Color.riskA : Color.border)
                .frame(width: 40, height: 24)

            Circle()
                .fill(Color.white)
                .frame(width: 20, height: 20)
                .padding(2)
        }
        .animation(.easeInOut(duration: 0.15), value: isOn)
    }
}

// MARK: - Risk Bar

/// 4px-height data bar. Filled to score% in risk color. No pill ends.
struct RiskBar: View {
    let score: Double
    let grade: String

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle()
                    .fill(Color.border)
                    .frame(height: 4)
                Rectangle()
                    .fill(ClavisGradeStyle.riskColor(for: grade))
                    .frame(width: geo.size.width * CGFloat(max(0, min(score, 100)) / 100), height: 4)
            }
        }
        .frame(height: 4)
    }
}

// MARK: - Brand Mark

struct ClavisBrandMark: View {
    var body: some View {
        Image("AppLogo")
            .resizable()
            .scaledToFit()
            .accessibilityHidden(true)
    }
}

// MARK: - Monogram

/// Brand monogram used on Login and Welcome when the full AppLogo is unnecessary.
struct ClavisMonogram: View {
    var size: CGFloat = 64
    var cornerRadius: CGFloat = 16

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .fill(Color.surface)
                .overlay(
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .stroke(Color.border, lineWidth: 1)
                )
                .frame(width: size, height: size)

            Text("C")
                .font(.system(size: size * 0.46, weight: .bold, design: .monospaced))
                .foregroundColor(.brandCream)
        }
        .accessibilityHidden(true)
    }
}

// MARK: - Primary / Secondary buttons (shared)

struct ClavisPrimaryButton: View {
    let title: String
    var isLoading: Bool = false
    var isEnabled: Bool = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack {
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .fill(isEnabled ? Color.textPrimary : Color.surfaceElevated)
                    .frame(height: 50)
                    .overlay(
                        RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                            .stroke(isEnabled ? Color.clear : Color.border, lineWidth: 1)
                    )

                if isLoading {
                    ProgressView()
                        .tint(.backgroundPrimary)
                } else {
                    Text(title)
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(isEnabled ? .backgroundPrimary : .textTertiary)
                }
            }
        }
        .buttonStyle(.plain)
        .disabled(!isEnabled || isLoading)
    }
}

enum ClavisSmallButtonKind {
    case neutral
    case prominent
}

struct ClavisSmallButton: View {
    let title: String
    var systemImage: String? = nil
    var kind: ClavisSmallButtonKind = .neutral
    var isEnabled: Bool = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 5) {
                if let systemImage {
                    Image(systemName: systemImage)
                        .font(.system(size: 11, weight: .semibold))
                }
                Text(title)
            }
            .font(.system(size: 12, weight: .medium))
            .foregroundColor(foreground)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(background)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous)
                    .stroke(border, lineWidth: 1)
            )
            .opacity(isEnabled ? 1 : 0.5)
        }
        .buttonStyle(.plain)
        .disabled(!isEnabled)
    }

    private var foreground: Color {
        switch kind {
        case .neutral:    return .textPrimary
        case .prominent:  return .backgroundPrimary
        }
    }

    private var background: Color {
        switch kind {
        case .neutral:    return Color.surface
        case .prominent:  return Color.textPrimary
        }
    }

    private var border: Color {
        switch kind {
        case .neutral:    return Color.border
        case .prominent:  return Color.clear
        }
    }
}

struct ClavisSecondaryButton: View {
    let title: String
    var isEnabled: Bool = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 15, weight: .medium))
                .foregroundColor(isEnabled ? .textSecondary : .textTertiary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
        }
        .buttonStyle(.plain)
        .disabled(!isEnabled)
    }
}

// MARK: - Brand Header

struct ClavixWordmarkHeader<Accessory: View>: View {
    let subtitle: String?
    @ViewBuilder let accessory: Accessory

    init(subtitle: String? = nil, @ViewBuilder accessory: () -> Accessory = { EmptyView() }) {
        self.subtitle = subtitle
        self.accessory = accessory()
    }

    var body: some View {
            HStack(alignment: .center, spacing: 12) {
                ClavisBrandMark()
                    .frame(width: 68, height: 68)

            VStack(alignment: .leading, spacing: 2) {
                Text("CLAVIX")
                    .font(ClavisTypography.brandWordmark)
                    .foregroundColor(.brandCream)
                    .kerning(2.1)
                if let subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .font(ClavisTypography.label)
                        .foregroundColor(.textSecondary)
                }
            }

            Spacer(minLength: 12)

            accessory
        }
    }
}

struct ClavixPageHeader<Accessory: View>: View {
    let title: String
    let subtitle: String?
    @ViewBuilder let accessory: Accessory

    init(
        title: String,
        subtitle: String? = nil,
        @ViewBuilder accessory: () -> Accessory = { EmptyView() }
    ) {
        self.title = title
        self.subtitle = subtitle
        self.accessory = accessory()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ClavixWordmarkHeader(accessory: { accessory })

            HStack(alignment: .firstTextBaseline, spacing: 12) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(title)
                        .font(.system(size: 28, weight: .semibold))
                        .foregroundColor(.textPrimary)
                        .tracking(-0.3)

                    if let subtitle, !subtitle.isEmpty {
                        Text(subtitle)
                            .font(.system(size: 13, weight: .regular))
                            .foregroundColor(.textSecondary)
                    }
                }

                Spacer(minLength: 12)
            }
        }
    }

    var stickyHeader: some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                ClavixWordmarkHeader(accessory: { accessory })

                Text(title)
                    .font(.system(size: 28, weight: .semibold))
                    .foregroundColor(.textPrimary)
                    .tracking(-0.3)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.top, 8)
            .padding(.bottom, 6)
        }
        .background(
            Color.backgroundPrimary.opacity(0.9)
                .background(.ultraThinMaterial)
                .ignoresSafeArea(edges: .top)
        )
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(Color.border.opacity(0.5))
                .frame(height: 0.5)
        }
    }
}

// MARK: - Top Bar

struct ClavisTopBar<MenuContent: View>: View {
    let title: String
    let onLogoTap: () -> Void
    @ViewBuilder let menuContent: () -> MenuContent

    init(
        title: String = "CLAVIS",
        onLogoTap: @escaping () -> Void,
        @ViewBuilder menuContent: @escaping () -> MenuContent
    ) {
        self.title = title
        self.onLogoTap = onLogoTap
        self.menuContent = menuContent
    }

    var body: some View {
        ZStack {
            HStack {
                Button(action: onLogoTap) {
                    ClavisBrandMark()
                        .frame(width: 72, height: 72)
                        .frame(width: 80, height: 72, alignment: .leading)
                }
                .buttonStyle(.plain)

                Spacer()

                Menu {
                    menuContent()
                } label: {
                    Image(systemName: "line.3.horizontal")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(.textPrimary)
                        .frame(width: 40, height: 40)
                }
                .menuStyle(.borderlessButton)
            }

            Text(title)
                .font(.custom("Inter", size: 20).weight(.bold))
                .foregroundColor(.textPrimary)
                .kerning(2.1)
        }
    }
}

// MARK: - Circle Button

struct ClavisCircleButton<Content: View>: View {
    let size: CGFloat
    let action: () -> Void
    @ViewBuilder let content: Content

    init(size: CGFloat = 52, action: @escaping () -> Void, @ViewBuilder content: () -> Content) {
        self.size = size
        self.action = action
        self.content = content()
    }

    var body: some View {
        Button(action: action) {
            content
                .frame(width: size, height: size)
                .background(Color.surface)
                .clipShape(Circle())
                .overlay(Circle().stroke(Color.border, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Eyebrow Header

struct ClavisEyebrowHeader: View {
    let eyebrow: String
    let title: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(eyebrow.uppercased())
                .font(ClavisTypography.label)
                .kerning(0.88)
                .foregroundColor(.textSecondary)
            Text(title)
                .font(ClavisTypography.dashboardTitle)
                .foregroundColor(.textPrimary)
        }
    }
}

// MARK: - Clavix Mark

struct ClavynxMark: View {
    var body: some View {
        if let uiImage = UIImage(named: "clavix_logo") {
            Image(uiImage: uiImage)
                .resizable()
                .scaledToFit()
                .frame(height: 48)
        } else {
            // Fallback: three sharp risk-colored bars
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.surface)
                    .frame(width: 88, height: 88)
                VStack(spacing: 0) {
                    HStack(alignment: .bottom, spacing: 6) {
                        Rectangle().fill(Color.riskA).frame(width: 18, height: 36)
                        Rectangle().fill(Color.riskC).frame(width: 18, height: 52)
                        Rectangle().fill(Color.riskF).frame(width: 18, height: 68)
                    }
                    Rectangle().fill(Color.textPrimary).frame(width: 70, height: 1.5)
                }
            }
        }
    }
}

// MARK: - Screen Header

struct ClavisScreenHeader: View {
    let title: String
    let subtitle: String?

    init(title: String, subtitle: String? = nil) {
        self.title = title
        self.subtitle = subtitle
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(ClavisTypography.pageTitle)
                .foregroundColor(.textPrimary)
            if let subtitle, !subtitle.isEmpty {
                Text(subtitle)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
            }
        }
    }
}

// MARK: - Glass Header

struct ClavisGlassHeader: View {
    let eyebrow: String
    let title: String
    let subtitle: String
    let grade: String?

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    Text(eyebrow.uppercased())
                        .font(ClavisTypography.label)
                        .kerning(0.88)
                        .foregroundColor(.textSecondary)
                    Text(title)
                        .font(ClavisTypography.dashboardTitle)
                        .foregroundColor(.textPrimary)
                    Text(subtitle)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 16)
                if let grade {
                    GradeBadge(grade: grade)
                }
            }
        }
        .padding(ClavisTheme.largeSpacing)
        .clavisCardStyle()
    }
}

// MARK: - Section Header

struct ClavisSectionHeader<Accessory: View>: View {
    let title: String
    let subtitle: String?
    @ViewBuilder let accessory: Accessory

    init(
        _ title: String,
        subtitle: String? = nil,
        @ViewBuilder accessory: () -> Accessory = { EmptyView() }
    ) {
        self.title = title
        self.subtitle = subtitle
        self.accessory = accessory()
    }

    var body: some View {
        HStack(alignment: .bottom, spacing: 16) {
            VStack(alignment: .leading, spacing: ClavisTheme.microSpacing) {
                Text(title.uppercased())
                    .font(ClavisTypography.label)
                    .kerning(0.88)
                    .foregroundColor(.textSecondary)
                if let subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
            }
            Spacer(minLength: 0)
            accessory
        }
    }
}

// MARK: - Loading Card

struct ClavisLoadingCard: View {
    let title: String
    let subtitle: String

    var body: some View {
        // Hi-Fi v2 skeleton: cream paper card with rule2-colored placeholder
        // bars. No legacy "surfaceElevated" navy.
        ClavixCard(fill: .clavixPaper) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 12) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.clavixRule2)
                        .frame(width: 44, height: 44)
                    VStack(alignment: .leading, spacing: 6) {
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.clavixRule2)
                            .frame(width: 140, height: 12)
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.clavixRule2)
                            .frame(maxWidth: .infinity).frame(height: 10)
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.clavixRule2)
                            .frame(width: 180, height: 10)
                    }
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(ClavisTypography.clavixSerif(15, weight: .medium))
                        .foregroundColor(.clavixInk)
                    Text(subtitle)
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
            }
        }
    }
}

// MARK: - Shared Error Card

struct DashboardErrorCard: View {
    let message: String

    var body: some View {
        // Hi-Fi v2 error treatment: warm bordeaux-tinted card on cream paper,
        // not the legacy dark dashboard surface.
        ClavixCard(fill: .clavixBadSoft) {
            VStack(alignment: .leading, spacing: 6) {
                Text("Something went wrong")
                    .font(ClavisTypography.clavixSerif(15, weight: .medium))
                    .foregroundColor(.clavixBadInk)
                Text(message)
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixBadInk)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

// MARK: - Metric Label

struct ClavisMetricLabel: View {
    let label: String
    let value: String
    let tone: Color?

    init(label: String, value: String, tone: Color? = nil) {
        self.label = label
        self.value = value
        self.tone = tone
    }

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.microSpacing) {
            Text(label.uppercased())
                .font(ClavisTypography.label)
                .kerning(0.88)
                .foregroundColor(.textSecondary)
            Text(value)
                .font(ClavisTypography.dataNumber)
                .foregroundColor(tone ?? .textPrimary)
        }
    }
}

// MARK: - GradeDisplay

enum GradeDisplayStyle {
    case hero
    case row
    case compact
}

struct GradeDisplay: View {
    let grade: String
    let score: Int?
    var trend: RiskTrend? = nil
    var evidence: EvidenceStrength? = nil
    var previousScore: Int? = nil
    var style: GradeDisplayStyle = .hero

    var body: some View {
        switch style {
        case .hero:
            heroBody
        case .row:
            rowBody
        case .compact:
            compactBody
        }
    }

    private var heroBody: some View {
        HStack(alignment: .center, spacing: 14) {
            GradeBadge(grade: grade, size: .large)

            VStack(alignment: .leading, spacing: 6) {
                if let trend {
                    RiskDirectionLabel(trend: trend)
                }

                if let score {
                    HStack(alignment: .firstTextBaseline, spacing: 6) {
                        Text("Score")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.textSecondary)

                        Text("\(score)")
                            .font(.system(size: 22, weight: .bold, design: .monospaced))
                            .foregroundColor(.textSecondary)
                            .monospacedDigit()

                        if let previousScore {
                            Text("was \(previousScore)")
                                .font(.system(size: 11, weight: .regular))
                                .foregroundColor(.textTertiary)
                        }
                    }
                }

                if let evidence {
                    EvidenceDots(evidence: evidence, grade: grade)
                }
            }
        }
    }

    private var rowBody: some View {
        HStack(alignment: .center, spacing: 10) {
            GradeBadge(grade: grade, size: .standard)

            VStack(alignment: .leading, spacing: 4) {
                if let trend {
                    RiskDirectionLabel(trend: trend)
                }

                if let score {
                    Text("\(score)")
                        .font(.system(size: 15, weight: .semibold, design: .monospaced))
                        .foregroundColor(.textSecondary)
                        .monospacedDigit()
                }

                if let evidence {
                    EvidenceDots(evidence: evidence, grade: grade)
                }
            }
        }
    }

    private var compactBody: some View {
        HStack(alignment: .center, spacing: 6) {
            GradeBadge(grade: grade, size: .compact)

            VStack(alignment: .leading, spacing: 3) {
                if let trend {
                    RiskDirectionLabel(trend: trend)
                }

                if let score {
                    Text("\(score)")
                        .font(.system(size: 13, weight: .semibold, design: .monospaced))
                        .foregroundColor(.textSecondary)
                        .monospacedDigit()
                }

                if let evidence {
                    EvidenceDots(evidence: evidence, grade: grade)
                }
            }
        }
    }
}

// MARK: - Score Source Chip

struct ScoreSourceChip: View {
    let source: String?

    private var label: String {
        guard let source else { return "" }
        let normalized = source.lowercased().trimmingCharacters(in: .whitespaces)
        if normalized.contains("position") || normalized.contains("holding") || normalized.contains("user") {
            return "Portfolio-specific"
        }
        if normalized.contains("shared") || normalized.contains("snapshot") {
            return "Shared rating"
        }
        return ClavisCopy.Status.sourceLabel(for: source)
    }

    private var isPortfolioSpecific: Bool {
        guard let source else { return false }
        let normalized = source.lowercased()
        return normalized.contains("position") || normalized.contains("holding") || normalized.contains("user")
    }

    var body: some View {
        if !label.isEmpty {
            Text(label)
                .font(.system(size: 10, weight: .medium))
                .foregroundColor(isPortfolioSpecific ? .informational : .textSecondary)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(Color.surfaceElevated)
                .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .stroke(Color.border, lineWidth: 0.5)
                )
        }
    }
}

// MARK: - Freshness Chip

struct FreshnessChip: View {
    let date: Date?

    private var text: String {
        guard let date else { return "" }
        let interval = Date().timeIntervalSince(date)
        if interval < 0 { return "Updated now" }
        let hours = interval / 3600
        if hours < 1 {
            let minutes = Int(interval / 60)
            return "Updated \(minutes)m ago"
        }
        if hours < 24 {
            return "Updated \(Int(hours))h ago"
        }
        if hours < 48 {
            return "Updated today"
        }
        return "Stale"
    }

    private var isStale: Bool {
        guard let date else { return false }
        return Date().timeIntervalSince(date) > 48 * 3600
    }

    var body: some View {
        if !text.isEmpty {
            Text(text)
                .font(.system(size: 10, weight: .medium))
                .foregroundColor(isStale ? .riskC : .textTertiary)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(Color.surfaceElevated)
                .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .stroke(Color.border, lineWidth: 0.5)
                )
        }
    }
}

// MARK: - Markdown Text

struct MarkdownText: View {
    let text: String
    var font: Font = ClavisTypography.body
    var color: Color = .textPrimary

    init(_ text: String, font: Font = ClavisTypography.body, color: Color = .textPrimary) {
        self.text = text
        self.font = font
        self.color = color
    }

    var body: some View {
        if let attributed = try? AttributedString(
            markdown: text,
            options: AttributedString.MarkdownParsingOptions(
                interpretedSyntax: .inlineOnlyPreservingWhitespace
            )
        ) {
            Text(attributed).font(font).foregroundColor(color).lineSpacing(5)
        } else {
            Text(text).font(font).foregroundColor(color).lineSpacing(5)
        }
    }
}

struct ClavisTextFieldStyle: TextFieldStyle {
    var monospaced: Bool = false

    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .font(monospaced ? .system(size: 15, weight: .regular, design: .monospaced) : .system(size: 15, weight: .regular))
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(Color.surfaceElevated)
            .foregroundColor(.textPrimary)
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .stroke(Color.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
    }
}
