import SwiftUI

// MARK: - Theme Constants

enum ClavisTheme {
    static let cornerRadius: CGFloat = 12         // cards
    static let innerCornerRadius: CGFloat = 10    // controls and inline surfaces
    static let sectionSpacing: CGFloat = 10
    static let cardPadding: CGFloat = 14
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
    // MARK: Surfaces (dark)
    static let backgroundPrimary = Color(hex: "#0B0D12")
    static let surface           = Color(hex: "#14171E")
    static let surfaceElevated   = Color(hex: "#1B1F28")
    static let surfaceMuted      = Color(hex: "#101319")
    static let border            = Color(hex: "#242934")
    static let borderSubtleTone  = Color(hex: "#1E232D")

    // MARK: Text
    static let textPrimary   = Color(hex: "#EEF1F5")
    static let textSecondary = Color(hex: "#8A93A3")
    static let textTertiary  = Color(hex: "#5A6374")
    static let brandCream    = Color(hex: "#D4C49B")

    // MARK: Informational (non-risk blue — never near score displays)
    static let informational = Color(hex: "#3B82C4")

    // MARK: Risk Scale — 5-state closed set. Color = state, never brand.
    static let riskA = Color(hex: "#1D9E75")   // Safe      (A) ≥80
    static let riskB = Color(hex: "#639922")   // Stable    (B) ≥65
    static let riskC = Color(hex: "#BA7517")   // Elevated  (C) ≥50
    static let riskD = Color(hex: "#D85A30")   // Risky     (D) ≥35
    static let riskF = Color(hex: "#C8342B")   // Critical  (F) <35

    // MARK: Grade Tag Surfaces
    static let gradeABg   = Color(hex: "#E1F5EE")
    static let gradeAText = Color(hex: "#085041")
    static let gradeBBg   = Color(hex: "#EAF3DE")
    static let gradeBText = Color(hex: "#27500A")
    static let gradeCBg   = Color(hex: "#FAEEDA")
    static let gradeCText = Color(hex: "#633806")
    static let gradeDBg   = Color(hex: "#FAECE7")
    static let gradeDText = Color(hex: "#712B13")
    static let gradeFBg   = Color(hex: "#FCEBEB")
    static let gradeFText = Color(hex: "#791F1F")

    // MARK: Backward-compat aliases
    static let accentBlue         = informational
    static let canvasBackground   = backgroundPrimary
    static let cardBackground     = surface
    static let elevatedBackground = surfaceElevated
    static let appBackground      = backgroundPrimary
    static let surfacePrimary     = surface
    static let surfaceSecondary   = surfaceElevated
    static let borderSubtle       = borderSubtleTone
    static let borderStrong       = border
    static let successTone        = riskA
    static let warningTone        = riskC
    static let criticalTone       = riskF
    static let mint               = riskB
    static let trustNavy          = informational
    static let neutralSurface     = surfaceElevated
    static let clavisCardBorder   = border
    static let clavisShadow       = Color.clear
    static let clavisAlertText    = riskF
    static let clavisAlertBg      = Color(hex: "#C8342B").opacity(0.12)
    static let successSurface     = Color(hex: "#1D9E75").opacity(0.12)
    static let warningSurface     = Color(hex: "#BA7517").opacity(0.12)
    static let dangerSurface      = Color(hex: "#C8342B").opacity(0.12)
    static let decisionSafe       = riskA
    static let decisionElevated   = riskC
    static let decisionReduce     = riskF
    static let decisionInfo       = textSecondary
    static let semanticGreen      = riskA
    static let semanticAmber      = riskC
    static let semanticRed        = riskF
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
        case "A": return .riskA
        case "B": return .riskB
        case "C": return .riskC
        case "D": return .riskD
        case "F": return .riskF
        default:  return .textSecondary
        }
    }

    /// Backward-compat alias
    static func color(for grade: String?) -> Color { riskColor(for: grade) }

    static func gradeBandBg(for grade: String?) -> Color {
        switch grade {
        case "A": return .gradeABg
        case "B": return .gradeBBg
        case "C": return .gradeCBg
        case "D": return .gradeDBg
        case "F": return .gradeFBg
        default:  return .surfaceElevated
        }
    }

    static func gradeBandText(for grade: String?) -> Color {
        switch grade {
        case "A": return .gradeAText
        case "B": return .gradeBText
        case "C": return .gradeCText
        case "D": return .gradeDText
        case "F": return .gradeFText
        default:  return .textSecondary
        }
    }

    static func gradeBandLabel(for grade: String?) -> String {
        switch grade {
        case "A": return "Safe (80–100)"
        case "B": return "Stable (65–79)"
        case "C": return "Elevated (50–64)"
        case "D": return "Risky (35–49)"
        case "F": return "Critical (0–34)"
        default:  return "—"
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
            .cornerRadius(4)
    }
}

// MARK: - Risk Direction Label

struct RiskDirectionLabel: View {
    let trend: RiskTrend

    private var color: Color {
        switch trend {
        case .worsening:  return .riskD
        case .improving:  return .riskA
        case .stable:     return .textSecondary
        }
    }

    private var label: String {
        switch trend {
        case .worsening:  return "↑ worsening"
        case .improving:  return "↓ improving"
        case .stable:     return "→ stable"
        }
    }

    var body: some View {
        Text(label)
            .font(.system(size: 12, weight: .semibold, design: .monospaced))
            .foregroundColor(color)
            .accessibilityLabel(label.replacingOccurrences(of: "↑", with: "worsening")
                .replacingOccurrences(of: "↓", with: "improving")
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

// MARK: - Grade Tag (deprecated)

@available(*, deprecated, message: "Use GradeBadge instead. P1-C requires GradeBadge for visual hierarchy.")
struct GradeTag: View {
    let grade: String
    var compact: Bool = false
    var large: Bool = false

    var body: some View {
        GradeBadge(
            grade: grade,
            size: large ? .large : (compact ? .compact : .standard)
        )
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

// MARK: - Gauge

struct ClavixGauge: View {
    let score: Int
    let grade: String
    var size: CGFloat = 112

    var body: some View {
        ZStack {
            GaugeArc(shapeGrade: grade, progress: 1)
                .stroke(Color.border, style: StrokeStyle(lineWidth: 8, lineCap: .round))

            GaugeArc(shapeGrade: grade, progress: progress)
                .stroke(ClavisGradeStyle.riskColor(for: grade), style: StrokeStyle(lineWidth: 8, lineCap: .round))

            VStack(spacing: 4) {
                Text("\(score)")
                    .font(.system(size: size * 0.27, weight: .bold, design: .monospaced))
                    .foregroundColor(.textPrimary)
                    .monospacedDigit()
                Text("GRADE \(grade)")
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(.textSecondary)
                    .tracking(0.8)
            }
            .offset(y: 6)
        }
        .frame(width: size, height: size)
    }

    private var progress: CGFloat {
        CGFloat(max(0, min(score, 100))) / 100
    }
}

private struct GaugeArc: Shape {
    let shapeGrade: String
    let progress: CGFloat

    func path(in rect: CGRect) -> Path {
        let startAngle = Angle(degrees: -220)
        let endAngle = Angle(degrees: 40)
        let angleDelta = endAngle.degrees - startAngle.degrees
        let currentAngle = Angle(degrees: startAngle.degrees + angleDelta * progress)
        let radius = min(rect.width, rect.height) / 2 - 10

        var path = Path()
        path.addArc(
            center: CGPoint(x: rect.midX, y: rect.midY),
            radius: radius,
            startAngle: startAngle,
            endAngle: currentAngle,
            clockwise: false
        )
        return path
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

// MARK: - Capsule Button (deprecated — violates spec R-07)

@available(*, deprecated, message: "Use clavisCardStyle instead. Capsule shapes violate spec R-07.")
struct ClavisCapsuleButton<Content: View>: View {
    let action: () -> Void
    @ViewBuilder let content: Content

    init(action: @escaping () -> Void, @ViewBuilder content: () -> Content) {
        self.action = action
        self.content = content()
    }

    var body: some View {
        Button(action: action) {
            content
                .padding(.horizontal, 24)
                .padding(.vertical, 16)
                .background(Color.surface)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))
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

// MARK: - Stat Pill (deprecated — violates spec R-07)

@available(*, deprecated, message: "Use ClavisMetricLabel. Pill shapes violate spec R-07.")
struct ClavisStatPill: View {
    let label: String
    let value: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.microSpacing) {
            Text(label)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
            Text(value)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.textPrimary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(Color.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: 4)
                .stroke(tint.opacity(0.18), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 4))
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
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(spacing: ClavisTheme.mediumSpacing) {
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color.surfaceElevated)
                    .frame(width: 44, height: 44)
                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.surfaceElevated)
                        .frame(width: 140, height: 14)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.surfaceElevated)
                        .frame(maxWidth: .infinity).frame(height: 12)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.surfaceElevated)
                        .frame(width: 180, height: 12)
                }
            }
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text(title).font(ClavisTypography.cardTitle).foregroundColor(.textPrimary)
                Text(subtitle).font(ClavisTypography.footnote).foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle()
    }
}

// MARK: - Ring Gauge (deprecated — violates spec R-02 and R-03)

@available(*, deprecated, message: "Ring gauges violate spec R-02/R-03. Score is the primary visual object.")
struct ClavisRingGauge: View {
    let progress: Double
    let lineWidth: CGFloat
    let tint: Color
    let icon: String?

    init(progress: Double, lineWidth: CGFloat = 10, tint: Color, icon: String? = nil) {
        self.progress = min(max(progress, 0), 1)
        self.lineWidth = lineWidth
        self.tint = tint
        self.icon = icon
    }

    var body: some View {
        ZStack {
            Circle().stroke(Color.border, lineWidth: lineWidth)
            Circle()
                .trim(from: 0, to: progress)
                .stroke(tint, style: StrokeStyle(lineWidth: lineWidth, lineCap: .butt))
                .rotationEffect(.degrees(-90))
            if let icon {
                Image(systemName: icon)
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundColor(tint)
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
