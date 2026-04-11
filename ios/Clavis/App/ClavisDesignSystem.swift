import SwiftUI

enum ClavisTheme {
    static let cornerRadius: CGFloat = 16
    static let innerCornerRadius: CGFloat = 12
    static let sectionSpacing: CGFloat = 20
    static let cardPadding: CGFloat = 16
    static let screenPadding: CGFloat = 36
    static let microSpacing: CGFloat = 4
    static let smallSpacing: CGFloat = 8
    static let mediumSpacing: CGFloat = 16
    static let largeSpacing: CGFloat = 24
    static let extraLargeSpacing: CGFloat = 36
    static let topBarSpacing: CGFloat = 30
    static let floatingTabInset: CGFloat = 16
    static let floatingTabHeight: CGFloat = 74
}

enum ClavisTypography {
    static func appFont(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .system(size: size, weight: weight, design: .default)
    }

    static let dashboardTitle = appFont(32, weight: .bold)
    static let pageTitle = appFont(28, weight: .bold)
    static let sectionTitle = appFont(22, weight: .semibold)
    static let cardTitle = appFont(17, weight: .semibold)
    static let body = appFont(16, weight: .regular)
    static let bodyStrong = appFont(16, weight: .medium)
    static let bodyEmphasis = appFont(16, weight: .semibold)
    static let footnote = appFont(12, weight: .regular)
    static let footnoteEmphasis = appFont(12, weight: .semibold)
    static let metric = appFont(32, weight: .bold)
    static let grade = appFont(36, weight: .bold)
    static let heroNumber = appFont(48, weight: .bold)
    static let heroLabel = appFont(24, weight: .semibold)
    static let interpretation = appFont(16, weight: .regular)
    static let action = appFont(17, weight: .semibold)
    static let topBarTitle = appFont(27, weight: .bold)
    static let eyebrow = appFont(11, weight: .semibold)
}

extension Color {
    static let accentBlue = Color.blue
    static let canvasBackground = Color(red: 0.968, green: 0.978, blue: 0.992)
    static let cardBackground = Color.white
    static let elevatedBackground = Color(red: 0.97, green: 0.97, blue: 0.98)
    static let successTone = Color.green
    static let warningTone = Color.orange
    static let criticalTone = Color.red
    static let mint = Color.green

    static let trustNavy = Color.blue
    static let slate900 = Color(red: 0.08, green: 0.12, blue: 0.22)
    static let slate700 = Color(red: 0.26, green: 0.33, blue: 0.45)
    static let slate500 = Color(red: 0.44, green: 0.50, blue: 0.61)
    static let slate300 = Color(red: 0.84, green: 0.88, blue: 0.93)
    static let slate200 = Color(red: 0.88, green: 0.91, blue: 0.95)
    static let slate100 = Color(red: 0.96, green: 0.96, blue: 0.98)

    static let appBackground = canvasBackground
    static let surfacePrimary = cardBackground
    static let surfaceSecondary = elevatedBackground
    static let textPrimary = slate900
    static let textSecondary = slate700
    static let textTertiary = slate500
    static let borderSubtle = slate200
    static let borderStrong = slate300
    static let successSurface = successTone.opacity(0.10)
    static let warningSurface = warningTone.opacity(0.10)
    static let dangerSurface = criticalTone.opacity(0.10)
    static let neutralSurface = surfaceSecondary
    static let clavisAlertText = criticalTone
    static let clavisAlertBg = dangerSurface
    static let clavisCardBorder = borderSubtle
    static let clavisShadow = Color.black.opacity(0.06)

    static let decisionSafe = successTone
    static let decisionWatch = warningTone
    static let decisionReduce = criticalTone
    static let decisionInfo = textSecondary

    static let semanticGreen = decisionSafe
    static let semanticAmber = decisionWatch
    static let semanticRed = decisionReduce
    static let semanticBlue = accentBlue
    static let semanticGray = decisionInfo
}

enum ClavisGradeStyle {
    static func color(for grade: String?) -> Color {
        switch grade {
        case "A": return .successTone
        case "B": return .mint
        case "C": return .warningTone
        case "D", "F": return .criticalTone
        default: return .textSecondary
        }
    }
}

extension View {
    func clavisCardStyle(fill: Color = .cardBackground) -> some View {
        background(fill)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
            .shadow(color: Color.clavisShadow, radius: 0, x: 0, y: 0)
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .stroke(Color.clavisCardBorder, lineWidth: 1)
            )
    }

    func clavisHeroCardStyle(fill: Color = .cardBackground) -> some View {
        background(fill)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
            .shadow(color: Color.clavisShadow, radius: 0, x: 0, y: 0)
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .stroke(Color.borderStrong, lineWidth: 1.5)
            )
    }

    func clavisSecondaryCardStyle(fill: Color = .surfaceSecondary) -> some View {
        background(fill)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}

struct ClavisAtmosphereBackground: View {
    var body: some View {
        LinearGradient(
            colors: [Color(red: 0.973, green: 0.981, blue: 0.994), Color(red: 0.956, green: 0.968, blue: 0.988)],
            startPoint: .top,
            endPoint: .bottom
        )
        .ignoresSafeArea()
    }
}

struct ClavisTopBar<Leading: View, Trailing: View>: View {
    let title: String
    @ViewBuilder let leading: Leading
    @ViewBuilder let trailing: Trailing

    init(title: String, @ViewBuilder leading: () -> Leading, @ViewBuilder trailing: () -> Trailing) {
        self.title = title
        self.leading = leading()
        self.trailing = trailing()
    }

    var body: some View {
        HStack(alignment: .center) {
            leading
                .frame(width: 52, height: 52, alignment: .leading)

            Spacer(minLength: 12)

            Text(title)
                .font(ClavisTypography.topBarTitle)
                .foregroundColor(.textPrimary)

            Spacer(minLength: 12)

            trailing
                .frame(width: 52, height: 52, alignment: .trailing)
        }
    }
}

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
                .background(Color.white.opacity(0.92))
                .clipShape(Circle())
                .shadow(color: Color.clavisShadow, radius: 12, x: 0, y: 6)
                .overlay(Circle().stroke(Color.borderSubtle, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

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
                .background(Color.white.opacity(0.94))
                .clipShape(Capsule())
                .shadow(color: Color.clavisShadow, radius: 12, x: 0, y: 6)
                .overlay(Capsule().stroke(Color.borderSubtle, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

struct ClavisEyebrowHeader: View {
    let eyebrow: String
    let title: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(eyebrow)
                .font(ClavisTypography.eyebrow)
                .kerning(2.2)
                .foregroundColor(.textTertiary)
            Text(title)
                .font(ClavisTypography.dashboardTitle)
                .foregroundColor(.textPrimary)
        }
    }
}

struct ClavynxMark: View {
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color.elevatedBackground)
                .frame(width: 88, height: 88)

            VStack(spacing: 7) {
                HStack(spacing: 6) {
                    RoundedRectangle(cornerRadius: 7, style: .continuous)
                        .fill(Color.successTone)
                        .frame(width: 18, height: 44)
                    RoundedRectangle(cornerRadius: 7, style: .continuous)
                        .fill(Color.accentBlue.opacity(0.82))
                        .frame(width: 18, height: 62)
                    RoundedRectangle(cornerRadius: 7, style: .continuous)
                        .fill(Color.accentBlue)
                        .frame(width: 18, height: 78)
                }
                .offset(y: 4)

                RoundedRectangle(cornerRadius: 1.5, style: .continuous)
                    .fill(Color.textPrimary)
                    .frame(height: 2)
                    .padding(.horizontal, 18)
            }
            .offset(y: -3)
        }
    }
}

enum ClavisDecisionStyle {
    static func color(for score: Double) -> Color {
        switch score {
        case 65...100: return .decisionSafe
        case 50..<65: return .decisionWatch
        default: return .decisionReduce
        }
    }

    static func label(for score: Double) -> String {
        switch score {
        case 65...100: return "Hold"
        case 50..<65: return "Watch"
        default: return "Reduce"
        }
    }

    static func tint(for pressure: ActionPressure?) -> Color {
        switch pressure {
        case .low:
            return .decisionSafe
        case .medium:
            return .decisionWatch
        case .high:
            return .decisionReduce
        case .none:
            return .decisionInfo
        }
    }
}

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
                        .font(ClavisTypography.footnoteEmphasis)
                        .kerning(0.8)
                        .foregroundColor(.textTertiary)

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
                    ZStack {
                        ClavisRingGauge(progress: gradeProgress, lineWidth: 8, tint: ClavisGradeStyle.color(for: grade))

                        Text(grade)
                            .font(.system(size: 24, weight: .bold))
                            .foregroundColor(.textPrimary)
                    }
                    .frame(width: 72, height: 72)
                }
            }
        }
        .padding(ClavisTheme.largeSpacing)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private var gradeProgress: CGFloat {
        switch grade {
        case "A": return 0.9
        case "B": return 0.75
        case "C": return 0.58
        case "D": return 0.4
        case "F": return 0.22
        default: return 0.5
        }
    }
}

struct ClavisStatPill: View {
    let label: String
    let value: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.microSpacing) {
            Text(label)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
            Text(value)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.textPrimary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(Color.surfaceSecondary)
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous)
                .stroke(tint.opacity(0.18), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}

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
                Text(title)
                    .font(ClavisTypography.sectionTitle)
                    .foregroundColor(.textPrimary)
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

struct ClavisLoadingCard: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(spacing: ClavisTheme.mediumSpacing) {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(Color.surfaceSecondary)
                    .frame(width: 44, height: 44)

                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .fill(Color.surfaceSecondary)
                        .frame(width: 140, height: 14)
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .fill(Color.surfaceSecondary)
                        .frame(maxWidth: .infinity)
                        .frame(height: 12)
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .fill(Color.surfaceSecondary)
                        .frame(width: 180, height: 12)
                }
            }

            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text(title)
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text(subtitle)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }
}

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
            Circle()
                .stroke(Color.borderSubtle, lineWidth: lineWidth)
            Circle()
                .trim(from: 0, to: progress)
                .stroke(tint, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round))
                .rotationEffect(.degrees(-90))

            if let icon {
                Image(systemName: icon)
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundColor(tint)
            }
        }
    }
}

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
            Text(label)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
            Text(value)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(tone ?? .textPrimary)
        }
    }
}

struct MarkdownText: View {
    let text: String
    var font: Font = .body
    var color: Color = .primary

    init(_ text: String, font: Font = .body, color: Color = .primary) {
        self.text = text
        self.font = font
        self.color = color
    }

    var body: some View {
        let cleaned = text
        if let attributed = try? AttributedString(
            markdown: cleaned,
            options: AttributedString.MarkdownParsingOptions(
                interpretedSyntax: .inlineOnlyPreservingWhitespace
            )
        ) {
            Text(attributed)
                .font(font)
                .foregroundColor(color)
                .lineSpacing(5)
        } else {
            Text(cleaned)
                .font(font)
                .foregroundColor(color)
                .lineSpacing(5)
        }
    }
}
