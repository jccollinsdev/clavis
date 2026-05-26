#if DEBUG
import SwiftUI
import WebKit

private extension ClavisTypography {
    static func mono(_ size: CGFloat, weight: Font.Weight) -> Font {
        Font.custom("JetBrainsMono-Regular", size: size).weight(weight)
    }

    static func serif(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        Font.system(size: size, weight: weight, design: .serif)
    }

    static var vqaCaption: Font { inter(12, weight: .regular) }
}

struct ClavixVisualQARoot: View {
    let open: String?
    @State private var selectedTab: Int
    @State private var routeOverride: String?

    init(open: String?) {
        self.open = open
        switch open {
        case "holdings": _selectedTab = State(initialValue: 1)
        case "search": _selectedTab = State(initialValue: 2)
        case "alerts": _selectedTab = State(initialValue: 3)
        case "settings": _selectedTab = State(initialValue: 4)
        default: _selectedTab = State(initialValue: 0)
        }
    }

    var body: some View {
        let activeOpen = routeOverride ?? open
        Group {
            switch activeOpen {
            case "design", "blueprint", "hifi": ClavixDesignArtifactView()
            case "splash": ClavixVisualQASplash()
            case "auth": ClavixVisualQAAuthWelcome()
            case "auth-signup": ClavixVisualQAAuthForm(mode: .signUp)
            case "auth-signin": ClavixVisualQAAuthForm(mode: .signIn)
            case "auth-forgot": ClavixVisualQAForgotPassword()
            case "auth-error": ClavixVisualQAAuthError()
            case "auth-loading": ClavixVisualQALoading(title: "Verifying your account", detail: "Loading your saved positions, preferences, and recent score history.")
            case "onboarding": ClavixVisualQAOnboarding()
            case "digest", "report": ClavixVisualQADigest()
            case "add-holding": ClavixVisualQAAddPositionMethod()
            case "holding-manual": ClavixVisualQAAddPositionManual(outside: false)
            case "holding-outside": ClavixVisualQAAddPositionManual(outside: true)
            case "search-none": ClavixVisualQASearchNoResults()
            case "search-outside": ClavixVisualQASearchOutsideUniverse()
            case "ticker": ClavixVisualQATickerDetail()
            case "ticker-live": TickerDetailDebugHarness(scrollTarget: nil)
            case "ticker-live-summary": TickerDetailDebugHarness(scrollTarget: "executive-summary")
            case "methodology": ClavixVisualQAMethodology()
            case "methodology-page": ClavixVisualQAMethodologyPage()
            case "article": ClavixVisualQAArticle()
            case "article-paywalled": ClavixVisualQAArticleState(kind: .paywalled)
            case "article-failed": ClavixVisualQAArticleState(kind: .failed)
            case "alert-detail": ClavixVisualQAAlertDetail()
            case "alerts-empty": ClavixVisualQAAlertsEmpty()
            case "notification-prefs": ClavixVisualQANotificationPrefs()
            case "profile": ClavixVisualQAProfile()
            case "subscription-trial": ClavixVisualQASubscription(kind: .trial)
            case "subscription-active": ClavixVisualQASubscription(kind: .active)
            case "export": ClavixVisualQAExport()
            case "delete-account": ClavixVisualQADeleteAccount()
            case "support-legal": ClavixVisualQASupportLegal()
            case "methodology-financial": ClavixVisualQAAuditDetail(title: "Financial Health", code: "FIN", score: 82, source: "Fundamentals", tone: .vqaGood)
            case "methodology-news": ClavixVisualQAAuditDetail(title: "News Signal", code: "NEWS", score: 38, source: "Article window", tone: .vqaWarn)
            case "methodology-macro": ClavixVisualQAAuditDetail(title: "Macro Exposure", code: "MAC", score: 64, source: "Macro factors", tone: .vqaInk)
            case "methodology-sector": ClavixVisualQAAuditDetail(title: "Sector Exposure", code: "SEC", score: 58, source: "Sector data", tone: .vqaWarn)
            case "methodology-volatility": ClavixVisualQAAuditDetail(title: "Volatility", code: "VOL", score: 76, source: "Price history", tone: .vqaGood)
            case "edit-holding": ClavixVisualQAEditPosition()
            case "delete-confirm": ClavixVisualQADeleteConfirm()
            case "free-limit": ClavixVisualQAFreeLimitReached()
            case "brokerage-sync": ClavixVisualQABrokerageSync()
            case "watchlist", "tracked-tickers": ClavixVisualQATrackedTickers()
            case "watchlist-add", "tracked-add": ClavixVisualQATrackedTickerAdd()
            case "watchlist-convert", "tracked-convert": ClavixVisualQATrackedTickerConvert()
            case "today-empty": ClavixVisualQAStateScreen(title: "No positions yet", eyebrow: "Today", glyph: "briefcase", body: "Add positions to generate a Morning Report and portfolio risk grade.", cta: "Add positions")
            case "today-error": ClavixVisualQAStateScreen(title: "Could not load Today", eyebrow: "Connection", glyph: "exclamationmark.triangle", body: "Clavix could not refresh this view. Your last saved portfolio is unchanged.", cta: "Try again", tone: .vqaBad)
            case "offline": ClavixVisualQAStateScreen(title: "Offline", eyebrow: "Connection", glyph: "wifi.slash", body: "Reconnect to refresh scores, articles, and the Morning Report.", cta: "Retry")
            case "limited-data": ClavixVisualQAStateScreen(title: "Limited data", eyebrow: "Ticker", glyph: "chart.bar.doc.horizontal", body: "This ticker has partial coverage. Some dimensions are unavailable until the data window fills.", cta: "View available data", tone: .vqaWarn)
            case "insufficient-history": ClavixVisualQAStateScreen(title: "More history needed", eyebrow: "Score history", glyph: "calendar.badge.clock", body: "Clavix needs more trading days before trend charts are available.", cta: "Back to ticker")
            case "ticker-held": ClavixVisualQATickerHeldState()
            case "refresh-limit": ClavixVisualQAStateScreen(title: "Refresh limit reached", eyebrow: "Manual refresh", glyph: "clock", body: "Your manual refresh allowance has been used for today. Scheduled refreshes continue normally.", cta: "Got it", tone: .vqaWarn)
            case "onb-intro": ClavixVisualQAOnboardingIntro()
            case "onb-digest-prefs": ClavixVisualQAOnboardingDigestPrefs()
            case "onb-final": ClavixVisualQAOnboardingFinal()
            case "paywall": ClavixVisualQAPaywall()
            default: tabShell
            }
        }
        .environment(\.vqaNavigate) { route in
            if route == "root" {
                routeOverride = nil
            } else if let tab = ["today", "holdings", "search", "alerts", "settings"].firstIndex(of: route) {
                routeOverride = nil
                selectedTab = tab
            } else {
                routeOverride = route
            }
        }
        .safeAreaInset(edge: .top, spacing: 0) {
            if routeOverride != nil {
                HStack {
                    Button { routeOverride = nil } label: {
                        Text("<- Back")
                            .font(ClavisTypography.mono(11, weight: .semibold))
                            .foregroundColor(.vqaAccent)
                    }
                    Spacer()
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(Color.vqaPage)
                .overlay(alignment: .bottom) { Rectangle().fill(Color.vqaRule).frame(height: 1) }
            }
        }
    }

    private var tabShell: some View {
        VStack(spacing: 0) {
            Group {
                switch selectedTab {
                case 1: ClavixVisualQAHoldings()
                case 2: ClavixVisualQASearch()
                case 3: ClavixVisualQAAlerts()
                case 4: ClavixVisualQASettings()
                default: ClavixVisualQAToday()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            VQATabBar(selectedTab: $selectedTab)
        }
    }
}

private struct VQANavigateKey: EnvironmentKey {
    static let defaultValue: (String) -> Void = { _ in }
}

private extension EnvironmentValues {
    var vqaNavigate: (String) -> Void {
        get { self[VQANavigateKey.self] }
        set { self[VQANavigateKey.self] = newValue }
    }
}

private extension Color {
    static let vqaInk = Color(hex: "#1A1814")
    static let vqaInk2 = Color(hex: "#3A342B")
    static let vqaInk3 = Color(hex: "#6B6357")
    static let vqaInk4 = Color(hex: "#A39B8D")
    static let vqaInk5 = Color(hex: "#C8C0B0")
    static let vqaCanvas = Color(hex: "#F0EADB")
    static let vqaPage = Color(hex: "#F7F2E6")
    static let vqaPaper = Color(hex: "#FFFDF7")
    static let vqaPaper2 = Color(hex: "#F3EDE0")
    static let vqaRule = Color(hex: "#D6CEBD")
    static let vqaRule2 = Color(hex: "#E6DFCF")
    static let vqaAccent = Color(hex: "#1D3A6E")
    static let vqaAccentSoft = Color(hex: "#E3E9F3")
    static let vqaAccentInk = Color(hex: "#11264A")
    static let vqaGood = Color(hex: "#1F6F43")
    static let vqaGoodSoft = Color(hex: "#DDE9D8")
    static let vqaGoodInk = Color(hex: "#0D4A2A")
    static let vqaWarn = Color(hex: "#9A6B1A")
    static let vqaWarnSoft = Color(hex: "#F1E3C2")
    static let vqaWarnInk = Color(hex: "#5A3E0C")
    static let vqaBad = Color(hex: "#8E1F1F")
    static let vqaBadSoft = Color(hex: "#F0D8D4")
    static let vqaBadInk = Color(hex: "#5E1313")
}

private enum VQA {
    static let pad: CGFloat = 20
    static let bottomPad: CGFloat = 28
    static let cardRadius: CGFloat = 10
    static let controlRadius: CGFloat = 7
    static let portfolioValue = "$1,284,715.42"
    static let portfolioGrade = "AA"
    static let portfolioScore = 81
    static let portfolioDelta = -1

    struct Holding: Identifiable {
        let id: String
        let ticker: String
        let name: String
        let grade: String
        let score: Int
        let delta: Int
        let value: String
        let today: String
        let weight: String
        let note: String
    }

    struct Sector: Identifiable {
        let id: String
        let symbol: String
        let name: String
        let change: String
        let weight: String
        let tone: Color
    }

    struct Dimension: Identifiable {
        let id: String
        let code: String
        let name: String
        let score: Int
        let delta: Int
    }

    struct NewsItem: Identifiable {
        let id: String
        let source: String
        let time: String
        let topic: String
        let score: Int
        let headline: String
        let tier: String
        let tone: Color
    }

    struct Alert: Identifiable {
        let id: String
        let category: String
        let time: String
        let title: String
        let detail: String
        let meta: String
        let route: String
        let tone: Color
        let unread: Bool
    }

    static let dimensions: [Dimension] = [
        .init(id: "fin", code: "FIN", name: "Financial Health", score: 82, delta: 0),
        .init(id: "news", code: "NEWS", name: "News Signal", score: 38, delta: -7),
        .init(id: "mac", code: "MAC", name: "Macro Exposure", score: 64, delta: 1),
        .init(id: "sec", code: "SEC", name: "Sector Exposure", score: 58, delta: -2),
        .init(id: "vol", code: "VOL", name: "Volatility", score: 76, delta: -1)
    ]

    static let holdings: [Holding] = [
        .init(id: "nvda", ticker: "NVDA", name: "NVIDIA", grade: "BBB", score: 64, delta: -3, value: "$200,852", today: "-2.1%", weight: "15.6%", note: "News signal fell on export-control evidence."),
        .init(id: "msft", ticker: "MSFT", name: "Microsoft", grade: "AAA", score: 91, delta: 1, value: "$158,920", today: "+0.6%", weight: "12.4%", note: "Cash-flow evidence remains strong."),
        .init(id: "brkb", ticker: "BRK.B", name: "Berkshire Hathaway", grade: "AA", score: 84, delta: 0, value: "$130,104", today: "+0.1%", weight: "10.1%", note: "Stable financial and volatility inputs."),
        .init(id: "jpm", ticker: "JPM", name: "JPMorgan Chase", grade: "A", score: 78, delta: 0, value: "$99,441", today: "+0.3%", weight: "7.7%", note: "Higher rates offset credit normalization."),
        .init(id: "xle", ticker: "XLE", name: "Energy Select Sector", grade: "BB", score: 57, delta: -2, value: "$85,902", today: "-1.3%", weight: "6.7%", note: "WTI weakness raised sector exposure."),
        .init(id: "cost", ticker: "COST", name: "Costco", grade: "AA", score: 83, delta: 0, value: "$72,218", today: "-0.2%", weight: "5.6%", note: "Margin signal steady before earnings."),
        .init(id: "vti", ticker: "VTI", name: "US Total Market", grade: "AA", score: 81, delta: 0, value: "$242,000", today: "+0.1%", weight: "18.8%", note: "Broad-market anchor."),
        .init(id: "googl", ticker: "GOOGL", name: "Alphabet", grade: "A", score: 79, delta: 0, value: "$88,412", today: "+0.4%", weight: "6.9%", note: "Ad evidence remains stable."),
        .init(id: "pltr", ticker: "PLTR", name: "Palantir", grade: "BBB", score: 62, delta: -2, value: "$44,708", today: "-1.7%", weight: "3.5%", note: "Guidance evidence lowered score." )
    ]

    static let tracked: [Holding] = [
        .init(id: "meta", ticker: "META", name: "Meta Platforms", grade: "A", score: 77, delta: 0, value: "-", today: "+0.3%", weight: "tracked", note: "Ad-market evidence stable."),
        .init(id: "tsla", ticker: "TSLA", name: "Tesla", grade: "B", score: 43, delta: -4, value: "-", today: "-2.9%", weight: "tracked", note: "Policy and margin signals remain weak."),
        .init(id: "amd", ticker: "AMD", name: "Advanced Micro Devices", grade: "BBB", score: 66, delta: 1, value: "-", today: "+1.2%", weight: "tracked", note: "Data-center demand evidence improved." )
    ]

    static let sectors: [Sector] = [
        .init(id: "xlk", symbol: "XLK", name: "Technology", change: "+0.42%", weight: "42%", tone: .vqaGood),
        .init(id: "xlv", symbol: "XLV", name: "Health", change: "-0.12%", weight: "11%", tone: .vqaBad),
        .init(id: "xlf", symbol: "XLF", name: "Financials", change: "+0.18%", weight: "9%", tone: .vqaGood),
        .init(id: "xle", symbol: "XLE", name: "Energy", change: "-1.32%", weight: "8%", tone: .vqaBad),
        .init(id: "xly", symbol: "XLY", name: "Consumer D", change: "-0.42%", weight: "6%", tone: .vqaBad),
        .init(id: "vti", symbol: "VTI", name: "US Total", change: "+0.06%", weight: "12%", tone: .vqaGood)
    ]

    static let news: [NewsItem] = [
        .init(id: "n1", source: "Reuters", time: "4h ago", topic: "Regulatory", score: 28, headline: "US widens chip-export curbs to second tier of Chinese AI labs", tier: "T1", tone: .vqaBad),
        .init(id: "n2", source: "Bloomberg", time: "7h ago", topic: "Demand", score: 64, headline: "Hyperscaler capex guidance remains steady through Q3", tier: "T1", tone: .vqaWarn),
        .init(id: "n3", source: "WSJ", time: "11h ago", topic: "Supply", score: 71, headline: "TSMC ramps CoWoS capacity, easing GPU bottleneck timeline", tier: "T2", tone: .vqaGood)
    ]

    static let alerts: [Alert] = [
        .init(id: "a1", category: "GRADE", time: "04:12", title: "NVDA changed A -> BBB", detail: "News signal fell 7 pts on widened chip-export curbs. Composite 67 -> 64.", meta: "BBB -3", route: "alert-detail", tone: .vqaBad, unread: true),
        .init(id: "a2", category: "MACRO", time: "06:48", title: "10Y yield +14 bps overnight", detail: "Affects four positions with elevated rate sensitivity: XLE, JPM, COST, BRK.B.", meta: "Macro", route: "alert-detail", tone: .vqaWarn, unread: true),
        .init(id: "a3", category: "NEWS", time: "14:22", title: "TSLA high-impact article", detail: "Reuters: EU lowers EV import duties on Chinese rivals. News signal 32.", meta: "B", route: "article", tone: .vqaBad, unread: false),
        .init(id: "a4", category: "TRACK", time: "11:04", title: "PLTR tracked ticker update", detail: "Score 65 -> 62 on guidance pull-through concerns.", meta: "BBB -2", route: "ticker", tone: .vqaAccent, unread: false),
        .init(id: "a5", category: "PORT", time: "07:00", title: "Morning Report ready", detail: "Portfolio composite 81 (AA). Largest mover: NVDA -3; largest lift: MSFT +1.", meta: "AA", route: "digest", tone: .vqaInk, unread: false)
    ]
}

private struct ClavixDesignArtifactView: View {
    private var url: URL? {
        if let raw = ProcessInfo.processInfo.environment["CLAVIX_DESIGN_URL"], let url = URL(string: raw) { return url }
        return URL(string: "http://127.0.0.1:9174/Clavix%20Hi-Fi%20v2%20(standalone).html")
    }

    var body: some View {
        Group {
            if let url { VQADesignWebView(url: url) }
            else { Text("Design artifact URL unavailable").foregroundColor(.vqaInk) }
        }
        .background(Color.vqaCanvas.ignoresSafeArea())
    }
}

private struct VQADesignWebView: UIViewRepresentable {
    let url: URL
    func makeUIView(context: Context) -> WKWebView {
        let webView = WKWebView(frame: .zero)
        webView.isOpaque = false
        webView.backgroundColor = UIColor(Color.vqaCanvas)
        webView.scrollView.backgroundColor = UIColor(Color.vqaCanvas)
        webView.allowsBackForwardNavigationGestures = true
        return webView
    }
    func updateUIView(_ webView: WKWebView, context: Context) {
        guard webView.url != url else { return }
        webView.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 30))
    }
}

private struct VQAScreen<Content: View>: View {
    let eyebrow: String
    let title: String
    var trailing: AnyView? = nil
    @ViewBuilder let content: Content

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) { content }
                .padding(.horizontal, VQA.pad)
                .padding(.top, 8)
                .padding(.bottom, VQA.bottomPad)
        }
        .background(Color.vqaPage.ignoresSafeArea())
        .safeAreaInset(edge: .top, spacing: 0) {
            VQALargeHeader(eyebrow: eyebrow, title: title, trailing: trailing)
        }
    }
}

private struct VQALargeHeader: View {
    let eyebrow: String
    let title: String
    var trailing: AnyView? = nil
    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack {
                VQAEyebrow(eyebrow)
                Spacer()
                if let trailing { trailing }
            }
            Text(title)
                .font(ClavisTypography.serif(32, weight: .medium))
                .tracking(-0.6)
                .foregroundColor(.vqaInk)
        }
        .padding(.horizontal, VQA.pad)
        .padding(.top, 4)
        .padding(.bottom, 14)
        .background(Color.vqaPage.ignoresSafeArea(edges: .top))
    }
}

private struct VQAEyebrow: View {
    let text: String
    init(_ text: String) { self.text = text }
    var body: some View {
        Text(text.uppercased())
            .font(ClavisTypography.mono(10, weight: .bold))
            .tracking(0.7)
            .foregroundColor(.vqaInk3)
    }
}

private struct VQACard<Content: View>: View {
    var padding: CGFloat = 16
    var fill: Color = .vqaPaper
    @ViewBuilder let content: Content
    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(fill)
            .overlay(RoundedRectangle(cornerRadius: VQA.cardRadius).stroke(Color.vqaRule, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: VQA.cardRadius))
    }
}

private struct VQATabBar: View {
    @Binding var selectedTab: Int

    private let tabs: [(title: String, icon: String)] = [
        ("Today", "doc.text"),
        ("Holdings", "rectangle.grid.1x2"),
        ("Search", "magnifyingglass"),
        ("Alerts", "bell"),
        ("Settings", "gearshape")
    ]

    var body: some View {
        VStack(spacing: 0) {
            Rectangle().fill(Color.vqaRule).frame(height: 1)
            HStack(spacing: 0) {
                ForEach(tabs.indices, id: \.self) { index in
                    Button { selectedTab = index } label: {
                        VStack(spacing: 3) {
                            Image(systemName: tabs[index].icon)
                                .font(.system(size: 17, weight: .regular))
                            Text(tabs[index].title)
                                .font(ClavisTypography.inter(10, weight: selectedTab == index ? .semibold : .medium))
                                .tracking(0.1)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, 8)
                        .padding(.bottom, 6)
                        .foregroundColor(selectedTab == index ? .vqaAccent : .vqaInk4)
                    }
                    .buttonStyle(.plain)
                }
            }
            .background(Color.vqaPaper)
        }
        .background(Color.vqaPaper.ignoresSafeArea(edges: .bottom))
    }
}

private struct VQASection<Content: View>: View {
    let eyebrow: String
    let title: String
    @ViewBuilder let content: Content
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            VQAEyebrow(eyebrow)
            Text(title)
                .font(ClavisTypography.serif(20, weight: .medium))
                .tracking(-0.3)
                .foregroundColor(.vqaInk)
            content
        }
        .padding(.top, 6)
    }
}

private struct VQAGrade: View {
    let grade: String
    var size: CGFloat = 44
    init(_ grade: String, size: CGFloat = 44) {
        self.grade = grade
        self.size = size
    }
    var body: some View {
        let metrics = gradeMetrics
        Text(grade)
            .font(ClavisTypography.mono(metrics.font, weight: .bold))
            .tracking(0.4)
            .foregroundColor(foreground)
            .frame(width: metrics.width, height: metrics.height)
            .background(color)
    }
    private var gradeMetrics: (width: CGFloat, height: CGFloat, font: CGFloat) {
        switch size {
        case 80...: return (124, 84, 42)
        case 40...: return (76, 44, 22)
        case 28...: return (50, 28, 13)
        case 22...: return (38, 22, 11)
        default: return (30, 18, 10)
        }
    }
    private var color: Color {
        switch grade {
        case "AAA", "AA": return .vqaGood
        case "A": return .vqaInk
        case "BBB", "BB": return .vqaWarn
        default: return .vqaBad
        }
    }
    private var foreground: Color {
        grade == "A" ? .vqaPaper : .white
    }
}

private struct VQAScoreBar: View {
    let score: Int
    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle().fill(Color.vqaRule2)
                Rectangle()
                    .fill(scoreTone(score))
                    .frame(width: geo.size.width * CGFloat(min(max(score, 0), 100)) / 100)
                ForEach([CGFloat(0.25), CGFloat(0.5), CGFloat(0.75)], id: \.self) { tick in
                    Rectangle()
                        .fill(Color.vqaPage)
                        .frame(width: 1)
                        .offset(x: geo.size.width * tick)
                }
            }
        }
        .frame(height: 4)
        .clipShape(RoundedRectangle(cornerRadius: 2))
    }
}

private func scoreTone(_ score: Int) -> Color {
    if score >= 75 { return .vqaGood }
    if score >= 55 { return .vqaInk }
    if score >= 40 { return .vqaWarn }
    return .vqaBad
}

private struct ClavixVisualQASplash: View {
    var body: some View {
        ZStack {
            Color.vqaPage.ignoresSafeArea()
            VStack(spacing: 12) {
                Image(systemName: "waveform.path.ecg.rectangle")
                    .font(.system(size: 54, weight: .thin))
                    .foregroundColor(.vqaInk)
                Text("Clavix")
                    .font(ClavisTypography.serif(26, weight: .semibold))
                    .foregroundColor(.vqaInk)
                Text("Portfolio risk, measured.")
                    .font(ClavisTypography.mono(11, weight: .regular))
                    .tracking(0.7)
                    .foregroundColor(.vqaInk3)
            }
        }
    }
}

private struct ClavixVisualQAAuthWelcome: View {
    @Environment(\.vqaNavigate) private var navigate
    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack { VQABrand(); Spacer(); VQAEyebrow("Andover Digital") }
            Spacer(minLength: 20)
            VQACard {
                VStack(alignment: .leading, spacing: 10) {
                    VQAEyebrow("Morning Report")
                    Text("One briefing. Every score audited.")
                        .font(ClavisTypography.serif(26, weight: .medium))
                        .foregroundColor(.vqaInk)
                    Text("Macro, sector, and position risk in one daily view, with the math behind every grade.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.vqaInk2)
                }
            }
            Spacer()
            Text("Portfolio risk, measured.")
                .font(ClavisTypography.serif(36, weight: .medium))
                .foregroundColor(.vqaInk)
            Text("Built for investors who want the morning answer without opening six different apps.")
                .font(ClavisTypography.body)
                .foregroundColor(.vqaInk2)
            Spacer()
            VQAButton("Create account", fill: .vqaInk, foreground: .vqaPaper) { navigate("auth-signup") }
            VQAButton("Sign in", fill: .clear, foreground: .vqaInk) { navigate("auth-signin") }
                .overlay(RoundedRectangle(cornerRadius: 7).stroke(Color.vqaRule, lineWidth: 1))
            Text("Clavix is informational only.")
                .font(ClavisTypography.vqaCaption)
                .foregroundColor(.vqaInk3)
                .frame(maxWidth: .infinity)
        }
        .padding(24)
        .background(Color.vqaPage.ignoresSafeArea())
    }
}

private struct ClavixVisualQAAuthForm: View {
    enum Mode { case signUp, signIn }
    let mode: Mode
    var body: some View {
        VQAScreen(eyebrow: "Account", title: mode == .signUp ? "Create account" : "Sign in") {
            VQACard { VStack(spacing: 12) { VQAInputRow("Email"); VQAInputRow("Password"); VQAButton(mode == .signUp ? "Continue" : "Sign in", fill: .vqaInk, foreground: .vqaPaper) {} } }
            Text(mode == .signUp ? "Your first report appears after your portfolio is added." : "Welcome back to Clavix.")
                .font(ClavisTypography.vqaCaption)
                .foregroundColor(.vqaInk3)
        }
    }
}

private struct ClavixVisualQAForgotPassword: View {
    var body: some View { VQAScreen(eyebrow: "Account recovery", title: "Reset password") { VQACard { VStack(spacing: 12) { VQAInputRow("Email"); VQAButton("Send reset link", fill: .vqaInk, foreground: .vqaPaper) {} } } } }
}

private struct ClavixVisualQAAuthError: View {
    var body: some View { VQAScreen(eyebrow: "Sign in", title: "Could not verify") { VQACard(fill: .vqaBadSoft) { Text("The email or password did not match an account. Check the details and try again.").foregroundColor(.vqaInk2) } } }
}

private struct ClavixVisualQALoading: View {
    let title: String
    let detail: String
    var body: some View { VStack(spacing: 18) { ProgressView(); Text(title).font(ClavisTypography.serif(24, weight: .medium)); Text(detail).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3).multilineTextAlignment(.center).frame(maxWidth: 260) }.frame(maxWidth: .infinity, maxHeight: .infinity).background(Color.vqaPage.ignoresSafeArea()) }
}

private struct ClavixVisualQAOnboarding: View {
    @Environment(\.vqaNavigate) private var navigate
    var body: some View {
        VQAScreen(eyebrow: "Step 1 of 2", title: "Add portfolio") {
            Text("Choose how Clavix should read your positions.")
                .font(ClavisTypography.serif(20, weight: .medium))
                .foregroundColor(.vqaInk)
            VQAMethodCard(title: "Connect your brokerage", body: "Read-only position sync for Pro accounts.", icon: "link", badge: "PRO")
            VQAMethodCard(title: "Enter manually", body: "Ticker, share count, and cost basis.", icon: "plus")
            VQAMethodCard(title: "Upload CSV", body: "Map rows from a portfolio export.", icon: "doc", badge: "PRO")
            VQAButton("Continue manually", fill: .vqaInk, foreground: .vqaPaper) { navigate("holding-manual") }
        }
    }
}

private struct ClavixVisualQAToday: View {
    @Environment(\.vqaNavigate) private var navigate
    var body: some View {
        VQAScreen(eyebrow: "Morning Report", title: "Today", trailing: AnyView(HStack(spacing: 18) { Image(systemName: "magnifyingglass"); Image(systemName: "bell") }.foregroundColor(.vqaInk))) {
            portfolioHero
            morningReportCard
            dimensionSnapshot
            sectorExposure
            attention
            bookPreview
            calendar
        }
    }

    private var portfolioHero: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("FRIDAY · MAY 9 · 7:02 ET")
                Spacer()
                Text("Updated")
            }
            .font(ClavisTypography.mono(10, weight: .regular))
            .tracking(0.7)
            .foregroundColor(.vqaInk3)
            HStack(alignment: .bottom, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Portfolio value").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3)
                    Text(VQA.portfolioValue)
                        .font(ClavisTypography.mono(29, weight: .semibold))
                        .tracking(-0.6)
                        .foregroundColor(.vqaInk)
                        .lineLimit(1)
                        .minimumScaleFactor(0.76)
                    Text("-$5,438 today").font(ClavisTypography.mono(12, weight: .regular)).foregroundColor(.vqaBad)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 4) {
                    VQAGrade(VQA.portfolioGrade)
                    Text("Composite \(VQA.portfolioScore) · -\(abs(VQA.portfolioDelta))")
                        .font(ClavisTypography.mono(11, weight: .regular))
                        .foregroundColor(.vqaInk3)
                }
            }
        }
        .padding(.bottom, 14)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.vqaRule).frame(height: 1) }
    }

    private var morningReportCard: some View {
        Button { navigate("digest") } label: {
            VQACard {
                HStack(alignment: .top, spacing: 14) {
                    VStack(alignment: .leading, spacing: 5) {
                        VQAEyebrow("Morning Report")
                        Text("Your daily risk brief is ready")
                            .font(ClavisTypography.serif(18, weight: .medium))
                            .foregroundColor(.vqaInk)
                        Text("Rates moved higher overnight and semiconductor policy risk weighed on NVDA. Portfolio grade remains AA, with two names needing a closer look.")
                            .font(ClavisTypography.vqaCaption)
                            .foregroundColor(.vqaInk2)
                            .lineLimit(3)
                            .truncationMode(.tail)
                    }
                    Spacer()
                    Text("Open ->").font(ClavisTypography.mono(11, weight: .semibold)).foregroundColor(.vqaAccent)
                }
            }
        }
        .buttonStyle(.plain)
    }

    private var dimensionSnapshot: some View {
        VQASection(eyebrow: "Portfolio risk by dimension", title: "Five-axis snapshot") {
            HStack(spacing: 1) {
                ForEach([("FIN", 86), ("NEWS", 62), ("MAC", 71), ("SEC", 78), ("VOL", 80)], id: \.0) { item in
                    VStack(spacing: 8) {
                        Text(item.0).font(ClavisTypography.mono(10, weight: .bold)).foregroundColor(.vqaInk3)
                        Text("\(item.1)").font(ClavisTypography.mono(22, weight: .semibold)).foregroundColor(.vqaInk)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(Color.vqaPaper)
                }
            }
            .overlay(Rectangle().stroke(Color.vqaRule, lineWidth: 1))
        }
    }

    private var sectorExposure: some View {
        VQASection(eyebrow: "Portfolio sectors", title: "Sector exposure") {
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 1), count: 3), spacing: 1) {
                ForEach(VQA.sectors) { sector in VQASectorCell(sector: sector) }
            }
            .overlay(Rectangle().stroke(Color.vqaRule, lineWidth: 1))
        }
    }

    private var attention: some View {
        VQASection(eyebrow: "2 alerts overnight", title: "Attention") {
            HStack { Spacer(); Button("See all ->") { navigate("alerts") }.font(ClavisTypography.vqaCaption).foregroundColor(.vqaAccent) }
                .offset(y: -48)
                .padding(.bottom, -38)
            ForEach(VQA.alerts.prefix(2)) { alert in
                Button { navigate(alert.route) } label: { VQAAlertRow(alert: alert) }.buttonStyle(.plain)
            }
        }
    }

    private var bookPreview: some View {
        VQASection(eyebrow: "Top movers · 9 positions", title: "Your book") {
            HStack { Spacer(); Button("Holdings ->") { navigate("holdings") }.font(ClavisTypography.vqaCaption).foregroundColor(.vqaAccent) }
                .offset(y: -48)
                .padding(.bottom, -38)
            VQACard(padding: 0) {
                VStack(spacing: 0) {
                    HStack { Text("SYM"); Spacer(); Text("GRADE · DELTA · TODAY") }
                        .font(ClavisTypography.mono(9, weight: .bold))
                        .foregroundColor(.vqaInk3)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                    Divider()
                    ForEach(Array(VQA.holdings.prefix(5))) { holding in
                        Button { navigate("ticker") } label: { VQABookRow(holding: holding) }.buttonStyle(.plain)
                        if holding.id != VQA.holdings.prefix(5).last?.id { Divider() }
                    }
                }
            }
        }
    }

    private var calendar: some View {
        VQASection(eyebrow: "Today", title: "Calendar") {
            VQACard(padding: 0) {
                VQACalendarLine("08:30", "DATA", "April core CPI m/m · consensus +0.30%")
                Divider()
                VQACalendarLine("14:00", "EARN", "COST Q3 earnings · post-close")
                Divider()
                VQACalendarLine("14:30", "FED", "Williams (NY Fed) · fireside chat")
            }
        }
    }
}

private struct ClavixVisualQADigest: View {
    var body: some View {
        VQAScreen(eyebrow: "Daily risk brief", title: "Morning Report", trailing: AnyView(HStack(spacing: 14) { Image(systemName: "slider.horizontal.3"); Image(systemName: "doc") }.foregroundColor(.vqaInk))) {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .firstTextBaseline) {
                    Text("CLAVIX · MORNING REPORT").font(ClavisTypography.mono(10, weight: .bold)).tracking(1.5)
                    Spacer()
                    Text("MAY 9").font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3)
                }
                Text("Friday, May 9, 2026 · generated 5:42 ET")
                    .font(ClavisTypography.serif(13).italic())
                    .foregroundColor(.vqaInk2)
                HStack(alignment: .bottom) {
                    VStack(alignment: .leading, spacing: 5) {
                        VQAEyebrow("Portfolio rating")
                        HStack(alignment: .lastTextBaseline, spacing: 10) { VQAGrade("AA"); Text("composite 81 · was 82").font(ClavisTypography.mono(14, weight: .regular)).foregroundColor(.vqaInk2) }
                    }
                    Spacer()
                    VQALineChart().frame(width: 112, height: 40)
                }
            }
            .padding(.bottom, 14)
            .overlay(alignment: .bottom) { Rectangle().fill(Color.vqaInk).frame(height: 2) }

            VQARomanSection("I", "Macro overnight", tag: "Generic") {
                Text("Treasuries sold off through the Asian session as a stronger wage print revived rate-cut anxiety. 10Y +14 bps to 4.62%, DXY +0.4, and WTI softened on China demand data.")
                    .font(ClavisTypography.serif(16))
                    .foregroundColor(.vqaInk)
                VQACard(padding: 12, fill: .vqaPaper2) { Text("READ-THROUGH: elevated yields are an incremental headwind to long-duration technology and rate-sensitive positions.").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2) }
            }
            VQARomanSection("II", "Sector exposure", tag: "Your sectors") {
                Text("Three of six exposed sectors are showing weaker risk signals. Energy is the largest detractor and semiconductor exposure remains the principal portfolio driver.")
                    .font(ClavisTypography.serif(16))
                    .foregroundColor(.vqaInk)
                VQASectorLedger()
            }
            VQARomanSection("III", "Position changes", tag: "Personalised") { VQAPositionLedger() }
            VQARomanSection("IV", "Tracked tickers", tag: "3 names") { Text("PLTR BBB -2 on enterprise-spend evidence. GOOGL and META unchanged.").font(ClavisTypography.serif(15)).foregroundColor(.vqaInk) }
            VQARomanSection("V", "What to track today", tag: "Calendar") {
                VQACard(padding: 0) { VQACalendarLine("08:30", "DATA", "April core CPI m/m · consensus +0.30%"); Divider(); VQACalendarLine("14:00", "EARN", "COST Q3 earnings · post-close") }
            }
            VQARomanSection("VI", "Sources & Methodology", tag: "Audit") {
                VQACard(padding: 12, fill: .vqaPaper2) { Text("Generated by Clavix at 5:42 ET using data refreshed within the last 4 hours. View full methodology ->").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3) }
            }
        }
    }
}

private struct ClavixVisualQAHoldings: View {
    @Environment(\.vqaNavigate) private var navigate
    var body: some View {
        VQAScreen(eyebrow: "9 positions · 3 tracked", title: "Holdings", trailing: AnyView(HStack(spacing: 14) { Image(systemName: "slider.horizontal.3"); Image(systemName: "plus") }.foregroundColor(.vqaInk))) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Synced 02:14 from your brokerage · $1,284,715")
                    .font(ClavisTypography.vqaCaption)
                    .foregroundColor(.vqaInk3)
            }
            VQAHoldingsToolbar()
            VQAHoldingsLedgerHeader()
            VStack(spacing: 0) {
                ForEach(Array(VQA.holdings.enumerated()), id: \.element.id) { index, holding in
                    Button { navigate("ticker") } label: {
                        VQAHoldingsLedgerRow(holding: holding, highlighted: holding.id == "nvda")
                    }
                    .buttonStyle(.plain)
                    if index < VQA.holdings.count - 1 { Divider().background(Color.vqaRule2) }
                }
            }
            VQASection(eyebrow: "3 of unlimited (Pro)", title: "Tracked tickers") {
                HStack { Spacer(); Button("Add ticker ->") { navigate("tracked-add") }.font(ClavisTypography.vqaCaption).foregroundColor(.vqaAccent) }
                    .offset(y: -48)
                    .padding(.bottom, -38)
                VQACard(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(Array(VQA.tracked.enumerated()), id: \.element.id) { index, item in
                            Button { navigate("ticker") } label: { VQATrackedTickerLedgerRow(holding: item) }
                                .buttonStyle(.plain)
                            if index < VQA.tracked.count - 1 { Divider().background(Color.vqaRule2) }
                        }
                    }
                }
            }
            VQASection(eyebrow: "Composition", title: "By sector") {
                VStack(spacing: 8) {
                    VQASectorBar(name: "Technology", weight: 42, grade: "AA", tickers: "AAPL · MSFT · NVDA")
                    VQASectorBar(name: "Diversified ETF", weight: 12, grade: "AAA", tickers: "VTI")
                    VQASectorBar(name: "Financials", weight: 9, grade: "A", tickers: "JPM")
                    VQASectorBar(name: "Energy", weight: 8, grade: "BB", tickers: "XLE")
                    VQASectorBar(name: "Conglomerate", weight: 14, grade: "AAA", tickers: "BRK.B")
                    VQASectorBar(name: "Consumer Disc.", weight: 5, grade: "AA", tickers: "COST")
                }
            }
        }
    }
}

private struct ClavixVisualQASearch: View {
    @Environment(\.vqaNavigate) private var navigate
    var body: some View {
        VStack(spacing: 0) {
            VQASearchHeader(query: "")
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    VQASection(eyebrow: "Recent", title: "Last viewed") {
                        HStack { Spacer(); Button("Clear ->") {}.font(ClavisTypography.vqaCaption).foregroundColor(.vqaAccent) }
                            .offset(y: -48)
                            .padding(.bottom, -38)
                        VQACard(padding: 0) {
                            VStack(spacing: 0) {
                                VQASearchResultLedgerRow(symbol: "NVDA", name: "NVIDIA", grade: "BBB", price: "-", change: nil, icon: "arrow.clockwise") { navigate("ticker") }
                                Divider()
                                VQASearchResultLedgerRow(symbol: "COIN", name: "Coinbase", grade: "CCC", price: "-", change: nil, icon: "arrow.clockwise") { navigate("ticker") }
                                Divider()
                                VQASearchResultLedgerRow(symbol: "BRK.B", name: "Berkshire H. B", grade: "AAA", price: "-", change: nil, icon: "arrow.clockwise") { navigate("ticker") }
                                Divider()
                                VQASearchResultLedgerRow(symbol: "XLE", name: "Energy Select", grade: "BB", price: "-", change: nil, icon: "arrow.clockwise") { navigate("ticker") }
                            }
                        }
                    }
                    VQASection(eyebrow: "What others are looking at", title: "Trending") {
                        VQACard(padding: 0) {
                            VStack(spacing: 0) {
                                VQASearchResultLedgerRow(symbol: "TSLA", name: "Tesla", grade: "B", price: "$184.60", change: -3.4) { navigate("ticker") }
                                Divider()
                                VQASearchResultLedgerRow(symbol: "PLTR", name: "Palantir", grade: "BBB", price: "$38.18", change: -1.4) { navigate("ticker") }
                                Divider()
                                VQASearchResultLedgerRow(symbol: "META", name: "Meta Platforms", grade: "A", price: "$612.40", change: 0.6) { navigate("ticker") }
                                Divider()
                                VQASearchResultLedgerRow(symbol: "JPM", name: "JPMorgan Chase", grade: "A", price: "$196.32", change: 0.3) { navigate("ticker") }
                            }
                        }
                    }
                    VQASection(eyebrow: "Quick filters", title: "Browse") {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack(spacing: 6) { VQAPill("S&P 500"); VQAPill("ETFs"); VQAPill("Mega caps") }
                            HStack(spacing: 6) { VQAPill("Dividend aristocrats"); VQAPill("High-grade only") }
                            HStack(spacing: 6) { VQAPill("Recently downgraded") }
                        }
                    }
                    HStack {
                        Button("No results state") { navigate("search-none") }
                        Spacer()
                        Button("Outside universe") { navigate("search-outside") }
                    }
                    .font(ClavisTypography.vqaCaption)
                    .foregroundColor(.vqaAccent)
                    .padding(.top, 14)
                }
                .padding(.horizontal, VQA.pad)
                .padding(.bottom, VQA.bottomPad)
            }
        }
        .background(Color.vqaPage.ignoresSafeArea())
    }
}

private struct ClavixVisualQASearchNoResults: View {
    var body: some View { VQAScreen(eyebrow: "Search", title: "No match") { VQACard { Text("No supported ticker matched that query. Try a ticker symbol or company name.").foregroundColor(.vqaInk2) } } }
}

private struct ClavixVisualQASearchOutsideUniverse: View {
    var body: some View { VQAScreen(eyebrow: "Outside universe", title: "Ticker unavailable") { VQACard(fill: .vqaWarnSoft) { Text("Risk data will be limited. Composite score, news signal, macro exposure, and sector exposure are unavailable until the ticker enters the universe.").foregroundColor(.vqaInk2) } } }
}

private struct VQAHoldingsToolbar: View {
    var body: some View {
        HStack(alignment: .center) {
            HStack(spacing: 4) {
                VQAPill("Weight", active: true)
                VQAPill("Grade")
                VQAPill("Δ Today")
                VQAPill("P&L")
            }
            Spacer()
            Text("9 / 9")
                .font(ClavisTypography.mono(11, weight: .regular))
                .foregroundColor(.vqaInk3)
        }
        .padding(.top, 2)
    }
}

private struct VQAHoldingsLedgerHeader: View {
    var body: some View {
        HStack(spacing: 8) {
            VQAColumnHeader("Sym · w%")
                .frame(width: 70, alignment: .leading)
            VQAColumnHeader("Last · day")
                .frame(maxWidth: .infinity, alignment: .leading)
            VQAColumnHeader("P&L", align: .trailing)
                .frame(width: 70, alignment: .trailing)
            VQAColumnHeader("Grade · Δ", align: .trailing)
                .frame(width: 60, alignment: .trailing)
        }
        .padding(.horizontal, VQA.pad)
        .padding(.vertical, 8)
        .background(Color.vqaPaper2)
        .overlay(alignment: .top) { Rectangle().fill(Color.vqaRule).frame(height: 1) }
        .overlay(alignment: .bottom) { Rectangle().fill(Color.vqaRule).frame(height: 1) }
        .padding(.horizontal, -VQA.pad)
    }
}

private struct VQAColumnHeader: View {
    let text: String
    var align: TextAlignment = .leading
    init(_ text: String, align: TextAlignment = .leading) {
        self.text = text
        self.align = align
    }
    var body: some View {
        Text(text.uppercased())
            .font(ClavisTypography.mono(9, weight: .semibold))
            .tracking(0.7)
            .foregroundColor(.vqaInk3)
            .multilineTextAlignment(align)
            .lineLimit(1)
            .minimumScaleFactor(0.75)
    }
}

private struct VQAHoldingsLedgerRow: View {
    let holding: VQA.Holding
    var highlighted = false

    var body: some View {
        HStack(spacing: 8) {
            VStack(alignment: .leading, spacing: 3) {
                Text(holding.ticker)
                    .font(ClavisTypography.mono(13, weight: .bold))
                    .tracking(0.3)
                    .foregroundColor(.vqaInk)
                Text("w \(holding.weight)")
                    .font(ClavisTypography.mono(10, weight: .regular))
                    .foregroundColor(.vqaInk3)
            }
            .frame(width: 70, alignment: .leading)

            VStack(alignment: .leading, spacing: 4) {
                Text(lastPrice)
                    .font(ClavisTypography.mono(13, weight: .semibold))
                    .foregroundColor(.vqaInk)
                HStack(spacing: 6) {
                    VQAMiniSpark(tone: dayTone)
                        .frame(width: 48, height: 14)
                    Text(holding.today)
                        .font(ClavisTypography.mono(10, weight: .semibold))
                        .foregroundColor(dayTone)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            VStack(alignment: .trailing, spacing: 3) {
                Text(pnl)
                    .font(ClavisTypography.mono(13, weight: .semibold))
                    .foregroundColor(pnl.hasPrefix("-") ? .vqaBad : .vqaGood)
                Text(pnlPct)
                    .font(ClavisTypography.mono(10, weight: .regular))
                    .foregroundColor(.vqaInk3)
            }
            .frame(width: 70, alignment: .trailing)

            VStack(alignment: .trailing, spacing: 2) {
                VQAGrade(holding.grade, size: 18)
                Text(holding.delta == 0 ? "—" : holding.delta > 0 ? "▲ \(holding.delta)" : "▼ \(abs(holding.delta))")
                    .font(ClavisTypography.mono(10, weight: .semibold))
                    .foregroundColor(holding.delta < 0 ? .vqaBad : holding.delta > 0 ? .vqaGood : .vqaInk3)
            }
            .frame(width: 60, alignment: .trailing)
        }
        .padding(.horizontal, VQA.pad)
        .padding(.vertical, 12)
        .background(highlighted ? Color.vqaAccentSoft : Color.clear)
        .overlay(alignment: .leading) {
            if highlighted { Rectangle().fill(Color.vqaAccent).frame(width: 3) }
        }
        .padding(.horizontal, -VQA.pad)
    }

    private var dayTone: Color { holding.today.hasPrefix("-") ? .vqaBad : holding.today == "+0.1%" ? .vqaInk2 : .vqaGood }
    private var lastPrice: String {
        switch holding.ticker {
        case "NVDA": return "$478.22"
        case "MSFT": return "$425.60"
        case "BRK.B": return "$412.31"
        case "JPM": return "$196.32"
        case "XLE": return "$92.18"
        case "COST": return "$810.44"
        case "VTI": return "$259.18"
        case "GOOGL": return "$176.12"
        case "PLTR": return "$38.18"
        default: return "$--"
        }
    }
    private var pnl: String {
        switch holding.ticker {
        case "NVDA": return "+$69,737"
        case "MSFT": return "+$28,104"
        case "BRK.B": return "+$18,020"
        case "JPM": return "+$7,842"
        case "XLE": return "-$3,108"
        case "COST": return "+$11,390"
        case "VTI": return "+$32,441"
        case "GOOGL": return "+$8,716"
        case "PLTR": return "+$4,096"
        default: return "$0"
        }
    }
    private var pnlPct: String {
        switch holding.ticker {
        case "NVDA": return "+52.9%"
        case "MSFT": return "+21.5%"
        case "XLE": return "-3.5%"
        case "PLTR": return "+10.1%"
        default: return "+8.4%"
        }
    }
}

private struct VQATrackedTickerLedgerRow: View {
    let holding: VQA.Holding
    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(holding.ticker).font(ClavisTypography.mono(13, weight: .bold)).foregroundColor(.vqaInk)
                Text(holding.name).font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3).lineLimit(1)
            }
            .frame(width: 70, alignment: .leading)
            VQAMiniSpark(tone: scoreTone(holding.score)).frame(width: 56, height: 20)
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(trackedPrice).font(ClavisTypography.mono(13, weight: .semibold)).foregroundColor(.vqaInk)
                Text(holding.today).font(ClavisTypography.mono(10, weight: .semibold)).foregroundColor(holding.today.hasPrefix("-") ? .vqaBad : .vqaGood)
            }
            VStack(alignment: .trailing, spacing: 2) {
                VQAGrade(holding.grade, size: 18)
                Text(holding.delta == 0 ? "—" : holding.delta > 0 ? "▲ \(holding.delta)" : "▼ \(abs(holding.delta))")
                    .font(ClavisTypography.mono(10, weight: .semibold))
                    .foregroundColor(holding.delta < 0 ? .vqaBad : holding.delta > 0 ? .vqaGood : .vqaInk3)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
    }
    private var trackedPrice: String {
        switch holding.ticker {
        case "META": return "$612.40"
        case "TSLA": return "$184.60"
        case "AMD": return "$164.12"
        default: return "$--"
        }
    }
}

private struct VQASectorBar: View {
    let name: String
    let weight: Int
    let grade: String
    let tickers: String
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(name).font(ClavisTypography.inter(13, weight: .medium)).foregroundColor(.vqaInk)
                VQAGrade(grade, size: 18)
                Spacer()
                Text("\(weight)%").font(ClavisTypography.mono(12, weight: .semibold)).foregroundColor(.vqaInk)
            }
            VQAScoreBar(score: min(weight * 2, 100))
            Text(tickers).font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3)
        }
    }
}

private struct VQASearchHeader: View {
    let query: String
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VQAEyebrow("Search")
                Spacer()
                Text("Cancel")
                    .font(ClavisTypography.inter(13, weight: .medium))
                    .foregroundColor(.vqaAccent)
            }
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 14, weight: .regular))
                    .foregroundColor(.vqaInk3)
                Text(query.isEmpty ? "Ticker or company name..." : query)
                    .font(ClavisTypography.mono(14, weight: .regular))
                    .tracking(0.2)
                    .foregroundColor(query.isEmpty ? .vqaInk4 : .vqaInk)
                Spacer()
                if !query.isEmpty { Image(systemName: "xmark").font(.system(size: 12)).foregroundColor(.vqaInk3) }
            }
            .padding(.horizontal, 12)
            .frame(height: 42)
            .background(Color.vqaPaper)
            .overlay(RoundedRectangle(cornerRadius: VQA.cardRadius).stroke(query.isEmpty ? Color.vqaRule : Color.vqaInk, lineWidth: query.isEmpty ? 1 : 1.5))
            .clipShape(RoundedRectangle(cornerRadius: VQA.cardRadius))
        }
        .padding(.horizontal, 16)
        .padding(.top, 4)
        .padding(.bottom, 12)
        .background(Color.vqaPage.ignoresSafeArea(edges: .top))
        .overlay(alignment: .bottom) { Rectangle().fill(Color.vqaRule).frame(height: 1) }
    }
}

private struct VQASearchResultLedgerRow: View {
    let symbol: String
    let name: String
    let grade: String?
    let price: String
    let change: Double?
    var icon: String? = nil
    var outside = false
    var action: () -> Void = {}

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                if let icon {
                    Image(systemName: icon)
                        .font(.system(size: 13, weight: .regular))
                        .foregroundColor(.vqaInk4)
                }
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 8) {
                        Text(symbol).font(ClavisTypography.mono(13, weight: .bold)).tracking(0.3).foregroundColor(.vqaInk)
                        Text(name).font(ClavisTypography.inter(12, weight: .regular)).foregroundColor(.vqaInk3).lineLimit(1)
                        if outside { Text("· OUTSIDE").font(ClavisTypography.mono(9, weight: .bold)).foregroundColor(.vqaWarn) }
                    }
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    if price != "-" { Text(price).font(ClavisTypography.mono(12, weight: .semibold)).foregroundColor(.vqaInk) }
                    if let change {
                        Text(change == 0 ? "—" : change > 0 ? "▲ \(String(format: "%.1f", change))%" : "▼ \(String(format: "%.1f", abs(change)))%")
                            .font(ClavisTypography.mono(10, weight: .semibold))
                            .foregroundColor(change < 0 ? .vqaBad : .vqaGood)
                    }
                }
                .frame(width: 70, alignment: .trailing)
                if let grade { VQAGrade(grade, size: 18) } else { Text("N/A").font(ClavisTypography.serif(13).italic()).foregroundColor(.vqaInk3) }
                Image(systemName: "chevron.right").font(.system(size: 10)).foregroundColor(.vqaInk4)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .opacity(outside ? 0.85 : 1)
        }
        .buttonStyle(.plain)
    }
}

private struct VQAMiniSpark: View {
    var tone: Color = .vqaInk
    var body: some View {
        GeometryReader { geo in
            Path { path in
                let points: [CGFloat] = [0.66, 0.52, 0.58, 0.41, 0.48, 0.32]
                for (index, y) in points.enumerated() {
                    let x = geo.size.width * CGFloat(index) / CGFloat(points.count - 1)
                    let p = CGPoint(x: x, y: geo.size.height * y)
                    if index == 0 { path.move(to: p) } else { path.addLine(to: p) }
                }
            }
            .stroke(tone, style: StrokeStyle(lineWidth: 1.4, lineCap: .round, lineJoin: .round))
        }
    }
}

private struct ClavixVisualQAAlerts: View {
    @Environment(\.vqaNavigate) private var navigate
    var body: some View {
        VQAScreen(eyebrow: "2 unread · 14 in 7D", title: "Alerts", trailing: AnyView(HStack(spacing: 14) { Image(systemName: "slider.horizontal.3"); Image(systemName: "checkmark") }.foregroundColor(.vqaInk))) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 4) { VQAPill("All · 14", active: true); VQAPill("Grade · 5"); VQAPill("News · 6"); VQAPill("Portfolio · 1"); VQAPill("Tracked · 1"); VQAPill("Macro · 1") }
            }
            VQADaySeparator("Today · Fri May 9")
            Button { navigate("alert-detail") } label: { VQAAlertCenterRow(unread: true, tone: .vqaBad, category: "GRADE", time: "04:12", title: "NVDA downgraded A -> BBB", body: "News signal fell 7 pts on widened chip-export curbs. Composite 67 -> 64.", grade: "BBB", delta: -3) }.buttonStyle(.plain)
            Button { navigate("methodology-macro") } label: { VQAAlertCenterRow(unread: true, tone: .vqaWarn, category: "MACRO", time: "06:48", title: "10Y yield +14 bps overnight", body: "Affects 4 positions with elevated rate sensitivity: XLE, JPM, COST, BRK.B.") }.buttonStyle(.plain)
            VQADaySeparator("Yesterday · Thu May 8")
            Button { navigate("article") } label: { VQAAlertCenterRow(tone: .vqaBad, category: "NEWS", time: "14:22", title: "TSLA high-impact article", body: "Reuters: EU lowers EV import duties on Chinese rivals · news score 32.", grade: "B") }.buttonStyle(.plain)
            Button { navigate("ticker") } label: { VQAAlertCenterRow(tone: .vqaAccent, category: "TRACK", time: "11:04", title: "PLTR tracked ticker update", body: "Score 65 -> 62 on guidance pull-through concerns.", grade: "BBB", delta: -2) }.buttonStyle(.plain)
            Button { navigate("ticker") } label: { VQAAlertCenterRow(tone: .vqaGood, category: "GRADE", time: "07:02", title: "MSFT upgraded AA -> AAA", body: "Hyperscaler capex confirmation lifts financial-health dimension.", grade: "AAA", delta: 1) }.buttonStyle(.plain)
            VQAAlertCenterRow(tone: .vqaInk, category: "PORT", time: "07:00", title: "Portfolio composite unchanged", body: "Daily summary: 81 (AA). Largest mover: NVDA -3; largest lifter: MSFT +1.", grade: "AA")
            VQADaySeparator("Wed May 7")
            VQAAlertCenterRow(tone: .vqaWarn, category: "NEWS", time: "16:14", title: "JPM regulatory headline", body: "Fed extends stress-test scenarios. No grade change.")
            VQAButton("Load earlier alerts", fill: .clear, foreground: .vqaInk) {}.overlay(RoundedRectangle(cornerRadius: 7).stroke(Color.vqaRule, lineWidth: 1))
        }
    }
}

private struct VQADaySeparator: View {
    let label: String
    init(_ label: String) { self.label = label }
    var body: some View {
        HStack(spacing: 10) {
            Text(label.uppercased())
                .font(ClavisTypography.mono(10, weight: .semibold))
                .tracking(0.7)
                .foregroundColor(.vqaInk3)
            Rectangle().fill(Color.vqaRule).frame(height: 1)
        }
        .padding(.top, 8)
    }
}

private struct VQAAlertCenterRow: View {
    var unread = false
    let tone: Color
    let category: String
    let time: String
    let title: String
    let detail: String
    var grade: String? = nil
    var delta: Int? = nil

    init(unread: Bool = false, tone: Color, category: String, time: String, title: String, body: String, grade: String? = nil, delta: Int? = nil) {
        self.unread = unread
        self.tone = tone
        self.category = category
        self.time = time
        self.title = title
        self.detail = body
        self.grade = grade
        self.delta = delta
    }

    var bodyView: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(category)
                    .font(ClavisTypography.mono(9, weight: .bold))
                    .tracking(0.5)
                    .foregroundColor(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(tone)
                    .clipShape(RoundedRectangle(cornerRadius: 3))
                Text(time).font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3)
            }
            .frame(width: 56, alignment: .leading)
            VStack(alignment: .leading, spacing: 4) {
                Text(title).font(ClavisTypography.inter(13, weight: unread ? .semibold : .medium)).foregroundColor(.vqaInk).fixedSize(horizontal: false, vertical: true)
                Text(detail).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3).fixedSize(horizontal: false, vertical: true)
                if grade != nil || delta != nil {
                    HStack(spacing: 6) {
                        if let grade { VQAGrade(grade, size: 18) }
                        if let delta { Text(delta == 0 ? "—" : delta > 0 ? "▲ \(delta)" : "▼ \(abs(delta))").font(ClavisTypography.mono(10, weight: .semibold)).foregroundColor(delta < 0 ? .vqaBad : .vqaGood) }
                    }
                    .padding(.top, 4)
                }
            }
            Spacer(minLength: 8)
            Image(systemName: "chevron.right").font(.system(size: 10)).foregroundColor(.vqaInk4).padding(.top, 2)
        }
        .padding(.horizontal, VQA.pad)
        .padding(.vertical, 12)
        .background(unread ? Color.vqaPaper : Color.clear)
        .overlay(alignment: .leading) { if unread { Rectangle().fill(Color.vqaAccent).frame(width: 3) } }
        .overlay(alignment: .bottom) { Rectangle().fill(Color.vqaRule2).frame(height: 1).padding(.leading, VQA.pad) }
        .padding(.horizontal, -VQA.pad)
    }
    var body: some View { bodyView }
}

private struct ClavixVisualQAAlertsEmpty: View {
    var body: some View { VQAScreen(eyebrow: "0 unread", title: "Alerts") { VStack(spacing: 14) { Image(systemName: "bell.slash").font(.system(size: 48)).foregroundColor(.vqaInk4); Text("All quiet.").font(ClavisTypography.serif(24, weight: .medium)); Text("Grade changes and major news will appear here. Your Morning Report still arrives every weekday.").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3).multilineTextAlignment(.center) }.frame(maxWidth: .infinity).padding(.vertical, 36) } }
}

private struct ClavixVisualQANotificationPrefs: View {
    var body: some View {
        VQAScreen(eyebrow: "Alerts", title: "Notifications") {
            VQASettingsSection("DELIVERY") { VQASettingRow("Morning Report", value: "On"); Divider(); VQASettingRow("Quiet hours", value: "9p-7a") }
            VQASettingsSection("RULES") { VQASettingRow("Grade changes", value: "On"); Divider(); VQASettingRow("Major news", value: "On"); Divider(); VQASettingRow("Macro shock", value: "Off"); Divider(); VQASettingRow("Tracked ticker alerts", value: "Pro") }
        }
    }
}

private struct ClavixVisualQASettings: View {
    @Environment(\.vqaNavigate) private var navigate
    var body: some View {
        VQAScreen(eyebrow: "Account", title: "Settings") {
            Button { navigate("profile") } label: { VQASettingsSection("PROFILE") { VQASettingRow("Name", value: "Bipul"); Divider(); VQASettingRow("Plan", value: "Pro trial", detail: "10 days remaining") } }.buttonStyle(.plain)
            Button { navigate("notification-prefs") } label: { VQASettingsSection("MORNING REPORT") { VQASettingRow("Delivery time", value: "7:00 ET"); Divider(); VQASettingRow("Length", value: "Brief") } }.buttonStyle(.plain)
            Button { navigate("brokerage-sync") } label: { VQASettingsSection("BROKERAGE") { VQASettingRow("Connected brokerage", value: "Live"); Divider(); VQASettingRow("Auto-sync", value: "On") } }.buttonStyle(.plain)
            Button { navigate("methodology-page") } label: { VQASettingsSection("REFERENCE") { VQASettingRow("Methodology", value: "Open") } }.buttonStyle(.plain)
            VQASettingsSection("ACCOUNT") { Button { navigate("export") } label: { VQASettingRow("Export data", value: "") }.buttonStyle(.plain); Divider(); Button { navigate("support-legal") } label: { VQASettingRow("Support & legal", value: "") }.buttonStyle(.plain); Divider(); Button { navigate("delete-account") } label: { VQASettingRow("Delete account", value: "") }.buttonStyle(.plain) }
        }
    }
}

private struct ClavixVisualQAProfile: View {
    var body: some View {
        VQAScreen(eyebrow: "Profile", title: "Account") {
            VQACard { HStack { VStack(alignment: .leading, spacing: 4) { Text("Bipul").font(ClavisTypography.serif(24, weight: .medium)).foregroundColor(.vqaInk); Text("bipul@example.com").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3) }; Spacer(); Text("PRO").font(ClavisTypography.mono(10, weight: .bold)).padding(8).background(Color.vqaAccentSoft).foregroundColor(.vqaAccentInk) } }
            VQASettingsSection("DETAILS") { VQASettingRow("Display name", value: "Bipul"); Divider(); VQASettingRow("Birth year", value: "1976"); Divider(); VQASettingRow("Region", value: "US") }
        }
    }
}

private struct ClavixVisualQASubscription: View {
    enum Kind { case trial, active }
    let kind: Kind
    var body: some View {
        VQAScreen(eyebrow: "Subscription", title: kind == .trial ? "Trial" : "Pro") {
            VQACard(fill: .vqaAccentSoft) { VStack(alignment: .leading, spacing: 8) { VQAEyebrow(kind == .trial ? "10 days remaining" : "Active"); Text(kind == .trial ? "Clavix Pro trial" : "Clavix Pro") .font(ClavisTypography.serif(28, weight: .medium)).foregroundColor(.vqaInk); Text(kind == .trial ? "No card needed until the trial ends." : "Renews monthly through the App Store.").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2) } }
            VQASettingsSection("INCLUDED") { VQASettingRow("Positions", value: "Unlimited"); Divider(); VQASettingRow("Tracked tickers", value: "Unlimited"); Divider(); VQASettingRow("Brokerage sync", value: "On"); Divider(); VQASettingRow("Verbose report", value: "On") }
        }
    }
}

private struct ClavixVisualQAExport: View {
    var body: some View { VQAScreen(eyebrow: "Privacy", title: "Export data") { Text("Download a copy of your positions, preferences, alerts, and report history.").font(ClavisTypography.serif(18)).foregroundColor(.vqaInk2); VQASettingsSection("EXPORT INCLUDES") { VQASettingRow("Positions", value: "CSV"); Divider(); VQASettingRow("Alerts", value: "JSON"); Divider(); VQASettingRow("Reports", value: "PDF") }; VQAButton("Prepare export", fill: .vqaInk, foreground: .vqaPaper) {} } }
}

private struct ClavixVisualQADeleteAccount: View {
    var body: some View { VQAScreen(eyebrow: "Danger zone", title: "Delete account") { VQACard(fill: .vqaBadSoft) { Text("This permanently removes your account, positions, preferences, device tokens, and report history.").foregroundColor(.vqaInk2) }; VQAInputRow("Type DELETE"); VQAButton("Delete account", fill: .vqaBad, foreground: .white) {} } }
}

private struct ClavixVisualQASupportLegal: View {
    var body: some View { VQAScreen(eyebrow: "Reference", title: "Support & legal") { VQASettingsSection("SUPPORT") { VQASettingRow("Email", value: "support"); Divider(); VQASettingRow("Status", value: "Online") }; VQASettingsSection("LEGAL") { VQASettingRow("Terms", value: "Open"); Divider(); VQASettingRow("Privacy", value: "Open"); Divider(); VQASettingRow("Methodology", value: "Open") } } }
}

private struct ClavixVisualQATickerDetail: View {
    @Environment(\.vqaNavigate) private var navigate
    var body: some View {
        VQAScreen(eyebrow: "NVIDIA · Tech · Semis", title: "NVDA", trailing: AnyView(HStack(spacing: 14) { Text("SUMMARY").font(ClavisTypography.mono(10, weight: .bold)); Image(systemName: "ellipsis") }.foregroundColor(.vqaInk))) {
            VQACard(padding: 0) {
                VStack(alignment: .leading, spacing: 0) {
                    HStack(alignment: .top, spacing: 14) {
                        VStack(alignment: .leading, spacing: 8) { VQAEyebrow("Composite"); HStack(alignment: .lastTextBaseline, spacing: 8) { VQAGrade("BBB"); Text("64").font(ClavisTypography.mono(32, weight: .semibold)).tracking(-0.6).foregroundColor(.vqaInk) }; HStack(spacing: 8) { Text("▼ 3").font(ClavisTypography.mono(12, weight: .semibold)).foregroundColor(.vqaBad); Text("was 67 · 5 days").font(ClavisTypography.mono(11, weight: .regular)).foregroundColor(.vqaInk3) }; Text("Downgraded A -> BBB overnight. News signal is the primary driver; balance sheet remains AAA-grade.").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2).fixedSize(horizontal: false, vertical: true) }
                        Spacer()
                        VQARadar(values: VQA.dimensions.map(\.score)).frame(width: 150, height: 150)
                    }.padding(16)
                    Divider()
                    HStack { VStack(alignment: .leading) { VQAEyebrow("Position"); Text("420 sh · 15.6% of book").font(ClavisTypography.mono(14, weight: .semibold)); Text("+$69,737 · +52.9% from cost").font(ClavisTypography.mono(11, weight: .regular)).foregroundColor(.vqaGood) }; Spacer(); VStack(alignment: .trailing) { VQAEyebrow("Last"); Text("$478.22").font(ClavisTypography.mono(22, weight: .semibold)); Text("-2.1%").font(ClavisTypography.mono(12, weight: .semibold)).foregroundColor(.vqaBad) } }.padding(16)
                }
            }
            VQACard(padding: 0) { VStack(alignment: .leading, spacing: 0) { HStack(alignment: .top) { VStack(alignment: .leading, spacing: 3) { VQAEyebrow("Price · 1M"); Text("$478.22 · -0.94%").font(ClavisTypography.mono(14, weight: .semibold)).foregroundColor(.vqaBad) }; Spacer(); HStack(spacing: 4) { VQAPill("1W"); VQAPill("1M", active: true); VQAPill("3M") } }.padding(.horizontal, 16).padding(.top, 12); VQALineChart().frame(height: 150).padding(16) } }
            VQASection(eyebrow: "Tap any row for the full audit", title: "Five dimensions") {
                VQACard(padding: 0) { VStack(spacing: 0) { ForEach(VQA.dimensions) { d in Button { navigate("methodology-\(d.id == "fin" ? "financial" : d.id == "news" ? "news" : d.id == "mac" ? "macro" : d.id == "sec" ? "sector" : "volatility")") } label: { VQATickerDimensionRow(dimension: d) }.buttonStyle(.plain); if d.id != VQA.dimensions.last?.id { Divider() } } } }
            }
            VQASection(eyebrow: "Why BBB", title: "Key drivers") {
                VQADriverCard(tone: .vqaBad, soft: .vqaBadSoft, tag: "HEADWIND", title: "Chip-export curbs widened", body: "Reuters · 4h ago. Second-tier Chinese AI labs added to entity list. Estimated 3-4% revenue at risk in a severe case.", score: "-7", dimension: "News Signal")
                VQADriverCard(tone: .vqaWarn, soft: .vqaWarnSoft, tag: "PRESSURE", title: "Sector beta to XLK rising", body: "Rolling 90D beta has climbed from 1.18 to 1.34 since March.", score: "-2", dimension: "Sector Exposure")
                VQADriverCard(tone: .vqaGood, soft: .vqaGoodSoft, tag: "TAILWIND", title: "Cash flow remains best-in-class", body: "TTM FCF margin 47%, debt-to-equity 0.21. Financial health remains strong.", score: "±0", dimension: "Financial Health")
            }
            VQASection(eyebrow: "Tap SUMMARY in app bar", title: "Executive summary") {
                VQACard(fill: .vqaAccentSoft) {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack(alignment: .top, spacing: 12) {
                            VStack(alignment: .leading, spacing: 6) { VQAEyebrow("Bull case"); Text("FCF margin 47%\nCoWoS supply easing\nHyperscaler capex steady").font(ClavisTypography.vqaCaption).foregroundColor(.vqaAccentInk) }
                            VStack(alignment: .leading, spacing: 6) { VQAEyebrow("Risk case"); Text("Export-curb widening\nInference benchmark miss\n30D vol up 1.2x").font(ClavisTypography.vqaCaption).foregroundColor(.vqaAccentInk) }
                        }
                        Rectangle().fill(Color.vqaAccent.opacity(0.22)).frame(height: 1)
                        VQAEyebrow("What to look for")
                        Text("Q3 earnings May 22. Track China revenue guidance and inference-tier ASPs. A second consecutive news-signal dip would trigger BBB -> BB review.").font(ClavisTypography.vqaCaption).foregroundColor(.vqaAccentInk).fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
            VQASection(eyebrow: "Last 7 days · 14 articles considered", title: "Recent news") {
                HStack { Spacer(); Button("View all ->") { navigate("article") }.font(ClavisTypography.vqaCaption).foregroundColor(.vqaAccent) }.offset(y: -48).padding(.bottom, -38)
                ForEach(VQA.news) { item in Button { navigate("article") } label: { VQANewsLedgerCard(item: item) }.buttonStyle(.plain) }
            }
            VQASection(eyebrow: "Composite · 90 days", title: "Score history") { VQACard { HStack { Text("70 --- 64").font(ClavisTypography.mono(11, weight: .regular)).foregroundColor(.vqaInk3); Spacer(); VQAPill("Composite", active: true); VQAPill("News"); VQAPill("Macro") }; VQALineChart().frame(height: 84); HStack { Text("Feb 8"); Spacer(); Text("Mar 9"); Spacer(); Text("Apr 8"); Spacer(); Text("May 9") }.font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3) } }
            HStack(spacing: 8) { VQAButton("Refresh data", fill: .clear, foreground: .vqaInk) {}; VQAButton("Tracked ticker", fill: .clear, foreground: .vqaInk) {} }.overlay(RoundedRectangle(cornerRadius: VQA.controlRadius).stroke(Color.vqaRule, lineWidth: 1))
        }
    }
}

private struct VQATickerDimensionRow: View {
    let dimension: VQA.Dimension
    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(dimension.code).font(ClavisTypography.mono(9, weight: .semibold)).tracking(0.6).foregroundColor(.vqaInk3)
                Text(dimension.name).font(ClavisTypography.inter(12, weight: .medium)).foregroundColor(.vqaInk)
            }
            .frame(width: 90, alignment: .leading)
            VQAScoreBar(score: dimension.score)
            Text("\(dimension.score)").font(ClavisTypography.mono(16, weight: .semibold)).foregroundColor(scoreTone(dimension.score)).frame(width: 36, alignment: .trailing)
            Text(dimension.delta == 0 ? "—" : dimension.delta > 0 ? "▲ \(dimension.delta)" : "▼ \(abs(dimension.delta))").font(ClavisTypography.mono(11, weight: .semibold)).foregroundColor(dimension.delta < 0 ? .vqaBad : dimension.delta > 0 ? .vqaGood : .vqaInk3).frame(width: 38, alignment: .trailing)
            Image(systemName: "chevron.right").font(.system(size: 10)).foregroundColor(.vqaInk4)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
    }
}

private struct ClavixVisualQAMethodology: View {
    @Environment(\.vqaNavigate) private var navigate
    var body: some View {
        VQAScreen(eyebrow: "Methodology · how 64 was computed", title: "Composite · NVDA") {
            VStack(alignment: .leading, spacing: 6) {
                HStack(alignment: .lastTextBaseline, spacing: 10) {
                    VQAGrade("BBB")
                    Text("64").font(ClavisTypography.mono(38, weight: .semibold)).tracking(-0.6).foregroundColor(.vqaInk)
                    Spacer()
                    Text("▼ 3").font(ClavisTypography.mono(13, weight: .semibold)).foregroundColor(.vqaBad)
                }
                Text("Equal-weighted average of the five dimensions. Refreshed daily after market close.")
                    .font(ClavisTypography.vqaCaption)
                    .foregroundColor(.vqaInk3)
            }
            .padding(.bottom, 14)
            .overlay(alignment: .bottom) { Rectangle().fill(Color.vqaRule).frame(height: 1) }

            VQASection(eyebrow: "Formula", title: "Composite = Σ dims / 5") {
                VQACodeCard(lines: [
                    ("# equal-weighted, 20% each", true),
                    ("composite = (FIN + NEWS + MAC + SEC + VOL) / 5", false),
                    ("          = (82 + 38 + 64 + 58 + 76) / 5", false),
                    ("          = 318 / 5 = 63.6 -> 64", false),
                    ("// grade change requires Δ>=3 pts across boundary for 2+ days", true)
                ])
            }
            VQASection(eyebrow: "Five dimensions · tap to audit", title: "Inputs") {
                VQACard(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(VQA.dimensions) { d in
                            Button { navigate("methodology-\(auditRoute(for: d.id))") } label: { VQAMethodologyInputRow(dimension: d) }.buttonStyle(.plain)
                            if d.id != VQA.dimensions.last?.id { Divider() }
                        }
                    }
                }
            }
            VQASection(eyebrow: "Reference", title: "Grade bands") {
                VQACard(padding: 0) {
                    VStack(spacing: 0) {
                        ForEach(Array(VQAGradeBand.bands.enumerated()), id: \.element.grade) { index, band in
                            VQAGradeBandRow(band: band, current: band.grade == "BBB")
                            if index < VQAGradeBand.bands.count - 1 { Divider() }
                        }
                    }
                }
            }
            VQAButton("Read full methodology", fill: .clear, foreground: .vqaInk) { navigate("methodology-page") }
                .overlay(RoundedRectangle(cornerRadius: VQA.controlRadius).stroke(Color.vqaRule, lineWidth: 1))
        }
    }

    private func auditRoute(for id: String) -> String {
        switch id {
        case "fin": return "financial"
        case "news": return "news"
        case "mac": return "macro"
        case "sec": return "sector"
        default: return "volatility"
        }
    }
}

private struct ClavixVisualQAMethodologyPage: View {
    var body: some View {
        VQAScreen(eyebrow: "Reference · v2.0", title: "Methodology") {
            Text("How Clavix rates risk.").font(ClavisTypography.serif(28, weight: .medium)).foregroundColor(.vqaInk)
            VQASettingsSection("CONTENTS") { VQASettingRow("1 · What is a Clavix score", value: ""); Divider(); VQASettingRow("2 · The five dimensions", value: "FIN NEWS MAC SEC VOL"); Divider(); VQASettingRow("3 · Composite formula", value: ""); Divider(); VQASettingRow("4 · Grade scale", value: "AAA -> F") }
            VQASettingsSection("AUDIT PAGES") { VQASettingRow("Financial Health", value: "FIN"); Divider(); VQASettingRow("News Signal", value: "NEWS"); Divider(); VQASettingRow("Macro Exposure", value: "MAC"); Divider(); VQASettingRow("Sector Exposure", value: "SEC"); Divider(); VQASettingRow("Volatility", value: "VOL") }
            VQARomanSection("1", "What is a Clavix score", tag: "Excerpt") { Text("A Clavix score is a 0-100 measure of structural risk attached to a single ticker, computed nightly from five equally weighted dimensions.").font(ClavisTypography.serif(15)).foregroundColor(.vqaInk) }
        }
    }
}

private struct ClavixVisualQAAuditDetail: View {
    let title: String
    let code: String
    let score: Int
    let source: String
    let tone: Color

    var body: some View {
        let model = VQAAuditModel.make(code: code, title: title, score: score, source: source, tone: tone)
        VQAScreen(eyebrow: "\(model.code) · audit", title: model.title) {
            HStack(alignment: .bottom, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    VQAEyebrow("\(model.code) · score")
                    Text("\(model.score)").font(ClavisTypography.mono(38, weight: .semibold)).tracking(-0.6).foregroundColor(model.tone)
                    HStack(spacing: 8) { Text(model.deltaText).font(ClavisTypography.mono(11, weight: .semibold)).foregroundColor(model.deltaColor); Text("weighted 20% in composite").font(ClavisTypography.mono(11, weight: .regular)).foregroundColor(.vqaInk3) }
                }
                Spacer()
                VStack(spacing: 4) { VQAScoreBar(score: model.score).frame(width: 100); HStack { Text("0"); Spacer(); Text("50"); Spacer(); Text("100") }.font(ClavisTypography.mono(9, weight: .regular)).foregroundColor(.vqaInk3).frame(width: 100) }
            }
            .padding(.bottom, 14)
            .overlay(alignment: .bottom) { Rectangle().fill(Color.vqaRule).frame(height: 1) }

            VQASection(eyebrow: "Formula", title: "How this dimension is built") { VQACodeCard(lines: model.formula.map { ($0, $0.hasPrefix("#")) }) }
            VQASection(eyebrow: "Raw inputs", title: "Numbers behind the score") {
                VQACard(padding: 0) { VStack(spacing: 0) { ForEach(Array(model.inputs.enumerated()), id: \.element.label) { index, input in VQAAuditInputRow(input: input); if index < model.inputs.count - 1 { Divider() } } } }
            }
            if !model.narrative.isEmpty {
                VQASection(eyebrow: "What it means right now", title: "Narrative") {
                    VQACard(fill: .vqaAccentSoft) { VStack(alignment: .leading, spacing: 8) { VQAEyebrow("Generated · LLM"); Text(model.narrative).font(ClavisTypography.serif(14)).foregroundColor(.vqaAccentInk).fixedSize(horizontal: false, vertical: true) } }
                }
            }
            VQASection(eyebrow: "Source · refresh", title: "Data lineage") {
                VQACard(padding: 0) { VQASettingRow("Primary source", value: model.source); Divider(); VQASettingRow("Last refreshed", value: model.refreshed); Divider(); VQASettingRow("Refresh cadence", value: model.cadence); Divider(); VQASettingRow("Distance to next band", value: model.boundary) }
            }
            if model.code == "NEWS" {
                VQASection(eyebrow: "Articles · ranked by weight", title: "14 considered · 4 driving") { ForEach(VQA.news) { item in VQANewsLedgerCard(item: item) } }
            }
            if model.code == "MAC" {
                VQASection(eyebrow: "Current macro state", title: "Regime inputs") { VQACard(padding: 0) { VQAFormulaRow(label: "10Y", value: "4.62% · +14 bps"); Divider(); VQAFormulaRow(label: "DXY", value: "104.81 · +0.4%"); Divider(); VQAFormulaRow(label: "VIX", value: "14.82 · +0.6") } }
            }
            VQAButton("Recompute now (Pro)", fill: .clear, foreground: .vqaInk) {}.overlay(RoundedRectangle(cornerRadius: VQA.controlRadius).stroke(Color.vqaRule, lineWidth: 1))
        }
    }
}

private struct VQACodeCard: View {
    let lines: [(text: String, muted: Bool)]
    var body: some View {
        VQACard {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(Array(lines.enumerated()), id: \.offset) { _, line in
                    Text(line.text)
                        .font(ClavisTypography.mono(line.muted ? 11 : 12, weight: line.muted ? .regular : .semibold))
                        .foregroundColor(line.muted ? .vqaInk3 : .vqaInk)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }
}

private struct VQAMethodologyInputRow: View {
    let dimension: VQA.Dimension
    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text(dimension.code).font(ClavisTypography.mono(10, weight: .semibold)).tracking(0.6).foregroundColor(.vqaInk3)
                    Text(dimension.name).font(ClavisTypography.inter(13, weight: .medium)).foregroundColor(.vqaInk)
                    if dimension.id == "news" { Text("DRIVER").font(ClavisTypography.mono(9, weight: .bold)).padding(.horizontal, 5).padding(.vertical, 2).background(Color.vqaBad).foregroundColor(.white).clipShape(RoundedRectangle(cornerRadius: 3)) }
                }
                Text(sourceLine).font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3)
                Text(refreshLine).font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk4)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text("\(dimension.score)").font(ClavisTypography.mono(18, weight: .semibold)).foregroundColor(scoreTone(dimension.score))
                Text(dimension.delta == 0 ? "—" : dimension.delta > 0 ? "▲ \(dimension.delta)" : "▼ \(abs(dimension.delta))").font(ClavisTypography.mono(10, weight: .semibold)).foregroundColor(dimension.delta < 0 ? .vqaBad : dimension.delta > 0 ? .vqaGood : .vqaInk3)
            }
            Image(systemName: "chevron.right").font(.system(size: 10)).foregroundColor(.vqaInk4)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
    }
    private var sourceLine: String {
        switch dimension.id {
        case "fin": return "Finnhub · stock/metric · quarterly"
        case "news": return "Google News + LLM · every 4 hours"
        case "mac": return "Polygon · regression · weekly"
        case "sec": return "Polygon · sector ETF · daily"
        default: return "Polygon · daily bars · after close"
        }
    }
    private var refreshLine: String {
        switch dimension.id {
        case "fin": return "refreshed Apr 25, 2026"
        case "news": return "refreshed 12 min ago"
        case "mac": return "refreshed May 5, 2026"
        case "sec": return "refreshed 02:14 ET"
        default: return "refreshed May 8, 16:00 ET"
        }
    }
}

private struct VQAGradeBand {
    let grade: String
    let range: String
    let label: String
    static let bands: [VQAGradeBand] = [
        .init(grade: "AAA", range: "90-100", label: "Treasury-grade"),
        .init(grade: "AA", range: "80-89", label: "Investment-grade"),
        .init(grade: "A", range: "70-79", label: "Solid"),
        .init(grade: "BBB", range: "60-69", label: "Stable, review points"),
        .init(grade: "BB", range: "50-59", label: "Mixed signals"),
        .init(grade: "B", range: "40-49", label: "Elevated risk"),
        .init(grade: "CCC", range: "30-39", label: "High risk"),
        .init(grade: "CC", range: "20-29", label: "Severe risk"),
        .init(grade: "C", range: "10-19", label: "Distressed"),
        .init(grade: "F", range: "0-9", label: "Failure mode")
    ]
}

private struct VQAGradeBandRow: View {
    let band: VQAGradeBand
    var current = false
    var body: some View {
        HStack(spacing: 10) {
            VQAGrade(band.grade, size: 18)
                .frame(width: 50, alignment: .leading)
            Text(band.range).font(ClavisTypography.mono(11, weight: .regular)).foregroundColor(.vqaInk2).frame(width: 70, alignment: .leading)
            Text(band.label).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2)
            Spacer()
            if current { Text("CURRENT").font(ClavisTypography.mono(9, weight: .bold)).foregroundColor(.vqaWarn) }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(current ? Color.vqaWarnSoft : Color.clear)
    }
}

private struct VQAAuditInput {
    let label: String
    let value: String
    let note: String
    let benchmark: String
    let tone: Color
}

private struct VQAAuditModel {
    let title: String
    let code: String
    let score: Int
    let tone: Color
    let delta: Int
    let formula: [String]
    let inputs: [VQAAuditInput]
    let source: String
    let refreshed: String
    let cadence: String
    let boundary: String
    let narrative: String

    var deltaText: String { delta == 0 ? "—" : delta > 0 ? "▲ \(delta)" : "▼ \(abs(delta))" }
    var deltaColor: Color { delta < 0 ? .vqaBad : delta > 0 ? .vqaGood : .vqaInk3 }

    static func make(code: String, title: String, score: Int, source: String, tone: Color) -> VQAAuditModel {
        switch code {
        case "FIN": return financial
        case "NEWS": return news
        case "MAC": return macro
        case "SEC": return sector
        case "VOL": return volatility
        default: return .init(title: title, code: code, score: score, tone: tone, delta: 0, formula: ["# weighted input model", "score = normalized weighted average"], inputs: [.init(label: "Signal", value: "\(score)", note: "Mock audit value", benchmark: "", tone: tone)], source: source, refreshed: "today", cadence: "daily", boundary: "—", narrative: "")
        }
    }

    static let financial = VQAAuditModel(title: "Financial Health", code: "FIN", score: 82, tone: .vqaGood, delta: 0, formula: ["# six ratios, normalized 0-100, then averaged", "debt_equity: 0.21 -> 92", "fcf_margin: 47.3% -> 95", "interest_cov: 28.4x -> 96", "current_ratio: 4.1 -> 88", "revenue_growth: +24% YoY -> 78", "profit_trend: 8/8 positive Q -> 90", "# average -> clipped+scaled -> score = 82"], inputs: [.init(label: "Debt-to-equity", value: "0.21", note: "Lower = healthier", benchmark: "sector 0.62", tone: .vqaGood), .init(label: "FCF margin (TTM)", value: "47.3%", note: "Cash generation remains strong", benchmark: "sector 18%", tone: .vqaGood), .init(label: "Interest coverage", value: "28.4x", note: "Coverage of interest burden", benchmark: "sector 9.2x", tone: .vqaGood), .init(label: "Current ratio", value: "4.10", note: "Liquidity cushion", benchmark: "sector 1.85", tone: .vqaGood), .init(label: "Revenue growth · TTM", value: "+24.0%", note: "Four-quarter trend", benchmark: "4Q avg +21%", tone: .vqaGood), .init(label: "Profitability streak", value: "8/8", note: "Consecutive positive EPS quarters", benchmark: "positive Q", tone: .vqaGood)], source: "Finnhub · stock/metric + stock/profile2", refreshed: "Apr 25, 2026 · FY2026 Q1 filing", cadence: "Quarterly · on earnings filings", boundary: "6 pts to AAA band", narrative: "")

    static let news = VQAAuditModel(title: "News Signal", code: "NEWS", score: 38, tone: .vqaBad, delta: -7, formula: ["# trailing 7-day weighted average", "raw = LLM(headline + body)", "w_recency = 3.0 if <24h, 2.0 if <72h, else 1.0", "w_source = 1.5 (T1) | 1.0 (T2) | 0.5 (T3)", "score = Σ(raw × weight) / Σ(weight)", "# volume signal: 14 articles vs 4w avg 6 = HIGH"], inputs: [.init(label: "Articles considered · 7d", value: "14", note: "Included in trailing window", benchmark: "4w avg 6", tone: .vqaInk), .init(label: "High-volume coverage", value: "+2.3x", note: "vs trailing average", benchmark: "", tone: .vqaBad), .init(label: "Average article score", value: "41", note: "Unweighted mean", benchmark: "", tone: .vqaBad), .init(label: "Weighted score", value: "38", note: "Final input", benchmark: "", tone: .vqaBad), .init(label: "T1 / T2 / T3 mix", value: "6 / 6 / 2", note: "Source weights", benchmark: "", tone: .vqaInk)], source: "Google News RSS -> Jina Reader -> MiniMax LLM", refreshed: "12 minutes ago", cadence: "Every 4 hours", boundary: "2 pts to B band", narrative: "News is the dimension dragging the composite. The export-curb article alone removed 7 pts from the 7-day weighted score; without it the dimension would read 47.")

    static let macro = VQAAuditModel(title: "Macro Exposure", code: "MAC", score: 64, tone: .vqaInk, delta: 1, formula: ["# 252-day OLS regression of NVDA daily returns", "β_10Y = -0.42", "β_DXY = -0.18", "β_WTI = +0.04", "β_VIX = -0.31", "β_SPX = 1.34", "R² = 0.71", "score = 100 - normalize(sensitivity)"], inputs: [.init(label: "β to 10Y yield", value: "-0.42", note: "Rising yields drag price", benchmark: "", tone: .vqaBad), .init(label: "β to DXY", value: "-0.18", note: "Mild currency sensitivity", benchmark: "", tone: .vqaWarn), .init(label: "β to WTI crude", value: "+0.04", note: "Statistically near zero", benchmark: "", tone: .vqaInk3), .init(label: "β to VIX", value: "-0.31", note: "Risk-off sensitivity", benchmark: "", tone: .vqaBad), .init(label: "β to S&P 500", value: "1.34", note: "High beta", benchmark: "", tone: .vqaWarn), .init(label: "Model R²", value: "0.71", note: "71% explained by macro", benchmark: "", tone: .vqaInk)], source: "Polygon · daily bars + macro factor series", refreshed: "May 5, 2026 · weekly recomputation", cadence: "Weekly correlation · daily narrative", boundary: "6 pts to A band", narrative: "Current macro is mixed for NVDA: 10Y and DXY are the wrong direction, while VIX remains benign. Net vulnerability is moderate.")

    static let sector = VQAAuditModel(title: "Sector Exposure", code: "SEC", score: 58, tone: .vqaWarn, delta: -2, formula: ["# two-layer: quant + narrative", "sector_etf = XLK", "β_to_sector = 1.18", "sector_momentum = -0.4%", "sector_breadth = 58%", "quant_score = 60", "narrative_adj = -2", "score = 58"], inputs: [.init(label: "Sector ETF used", value: "XLK", note: "Technology Select SPDR", benchmark: "", tone: .vqaInk), .init(label: "β to XLK (90D)", value: "1.18", note: "Climbed from 1.05 in March", benchmark: "", tone: .vqaWarn), .init(label: "Sector momentum", value: "-0.4%", note: "30D vs SPX", benchmark: "", tone: .vqaWarn), .init(label: "Sector breadth", value: "58%", note: "% above 200-day MA", benchmark: "", tone: .vqaInk), .init(label: "Narrative adjustment", value: "-2", note: "Regulatory tone", benchmark: "", tone: .vqaBad)], source: "Polygon (sector ETF) + sector RSS", refreshed: "02:14 ET · narrative 6 hours ago", cadence: "Daily quant · 12h narrative", boundary: "2 pts to BBB band", narrative: "Technology leadership has narrowed, breadth has weakened, and regulatory headlines are picking up. NVDA's beta to XLK means sector softness passes through with leverage.")

    static let volatility = VQAAuditModel(title: "Volatility", code: "VOL", score: 76, tone: .vqaGood, delta: -1, formula: ["# four price-based inputs", "realized_vol_30d = 42.1% ann. -> 60", "realized_vol_90d = 38.4% ann. -> 64", "vol_ratio_30/90 = 1.10 -> 58", "max_dd_252d = -18.4% -> 68", "β_to_SPX_252d = 1.34 -> 70", "score = weighted(...) -> 76"], inputs: [.init(label: "30-day realized vol", value: "42.1%", note: "Annualized daily returns", benchmark: "", tone: .vqaWarn), .init(label: "90-day realized vol", value: "38.4%", note: "Slower baseline", benchmark: "", tone: .vqaInk), .init(label: "30d / 90d ratio", value: "1.10", note: ">1 = vol expanding", benchmark: "", tone: .vqaWarn), .init(label: "Max drawdown · 252D", value: "-18.4%", note: "From $501 high", benchmark: "", tone: .vqaWarn), .init(label: "β to S&P 500", value: "1.34", note: "Index sensitivity", benchmark: "", tone: .vqaWarn)], source: "Polygon · adjusted daily bars", refreshed: "May 8, 16:00 ET · post-close", cadence: "Daily after market close", boundary: "4 pts to AA band", narrative: "Volatility is elevated but not extreme. The 30d-to-90d ratio signals expansion, but drawdown and realized-vol readings remain inside normal ranges for this ticker.")
}

private struct VQAAuditInputRow: View {
    let input: VQAAuditInput
    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                Text(input.label).font(ClavisTypography.inter(13, weight: .medium)).foregroundColor(.vqaInk)
                if !input.note.isEmpty { Text(input.note).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3).fixedSize(horizontal: false, vertical: true) }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(input.value).font(ClavisTypography.mono(14, weight: .semibold)).foregroundColor(input.tone)
                if !input.benchmark.isEmpty { Text("vs \(input.benchmark)").font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3) }
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
    }
}

private struct ClavixVisualQAArticle: View {
    var body: some View {
        VQAScreen(eyebrow: "NVDA", title: "Article") {
            HStack { Text("HIGH IMPACT").font(ClavisTypography.mono(10, weight: .bold)).padding(6).background(Color.vqaWarnSoft); Text("Tier 1 source").font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3); Spacer(); Text("2h ago").font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3) }
            Text("Export controls keep semiconductor risk elevated").font(ClavisTypography.serif(26, weight: .medium)).foregroundColor(.vqaInk)
            Rectangle().fill(Color.vqaRule).frame(height: 1)
            VQAEyebrow("Brief")
            Text("The article adds evidence that policy risk remains a material input for advanced semiconductor names.").font(ClavisTypography.serif(16)).foregroundColor(.vqaInk2)
            VQACard(fill: .vqaAccentSoft) { VStack(alignment: .leading, spacing: 8) { VQAEyebrow("Portfolio context"); Text("NVDA is 15.6% of your book, so this policy signal has visible portfolio-level impact even though the portfolio composite remains AA.").font(ClavisTypography.serif(15)).foregroundColor(.vqaAccentInk).fixedSize(horizontal: false, vertical: true) } }
            VQAEyebrow("Risk signal")
            VQACard { HStack { Text("61").font(ClavisTypography.mono(26, weight: .semibold)).foregroundColor(.vqaWarn); Text("Policy friction increased sector exposure but did not alter financial-health inputs.").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2) } }
            VQAButton("Read full article at Reuters ->", fill: .clear, foreground: .vqaInk) {}.overlay(RoundedRectangle(cornerRadius: 7).stroke(Color.vqaRule, lineWidth: 1))
        }
    }
}

private struct ClavixVisualQAArticleState: View {
    enum Kind { case paywalled, failed }
    let kind: Kind
    var body: some View { VQAScreen(eyebrow: "NVDA", title: "Article") { VQACard(fill: kind == .paywalled ? .vqaWarnSoft : .vqaBadSoft) { Text(kind == .paywalled ? "The full body is behind the publisher paywall. Clavix scored the headline with a low-confidence flag." : "Article readers returned an empty body. This item is excluded from the NVDA news signal.").foregroundColor(.vqaInk2) } } }
}

private struct ClavixVisualQAAlertDetail: View {
    var body: some View {
        VQAScreen(eyebrow: "Grade change · NVDA", title: "Grade change") {
            HStack(spacing: 8) { Text("GRADE · DOWNGRADE").font(ClavisTypography.mono(9, weight: .bold)).tracking(0.5).padding(.horizontal, 7).padding(.vertical, 3).background(Color.vqaBad).foregroundColor(.white).clipShape(RoundedRectangle(cornerRadius: 3)); Text("4h ago · 04:12 ET").font(ClavisTypography.mono(11, weight: .regular)).foregroundColor(.vqaInk3); Spacer() }
            Text("NVDA downgraded A -> BBB").font(ClavisTypography.serif(26, weight: .medium)).tracking(-0.4).foregroundColor(.vqaInk)
            Text("Hysteresis cleared at 04:12: composite has held at or below 67 for 2 trading days and is now 3 points across the BBB boundary.").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2).fixedSize(horizontal: false, vertical: true)
            VQACard(padding: 0) {
                VStack(spacing: 0) {
                    HStack(spacing: 0) {
                        VStack(spacing: 8) { VQAEyebrow("Before · May 7"); VQAGrade("A"); Text("composite 70").font(ClavisTypography.mono(12, weight: .regular)).foregroundColor(.vqaInk3) }.frame(maxWidth: .infinity).padding(14)
                        Rectangle().fill(Color.vqaRule2).frame(width: 1)
                        VStack(spacing: 8) { VQAEyebrow("Now · May 9"); VQAGrade("BBB"); Text("composite 64 · ▼ 6").font(ClavisTypography.mono(12, weight: .regular)).foregroundColor(.vqaBad) }.frame(maxWidth: .infinity).padding(14).background(Color.vqaBadSoft)
                    }
                    Divider()
                    VStack(alignment: .leading, spacing: 8) { VQAEyebrow("Driving dimension"); HStack(spacing: 10) { Text("NEWS").font(ClavisTypography.mono(10, weight: .semibold)).foregroundColor(.vqaInk3); VQAScoreBar(score: 38); Text("38").font(ClavisTypography.mono(14, weight: .bold)).foregroundColor(.vqaBad); Text("▼ 7").font(ClavisTypography.mono(11, weight: .semibold)).foregroundColor(.vqaBad) } }.padding(14)
                }
            }
            VQACard(fill: .vqaAccentSoft) {
                VStack(alignment: .leading, spacing: 8) {
                    VQAEyebrow("Portfolio context")
                    Text("NVDA is your largest position at 15.6% of book. A two-band downgrade in a single week is unusual, while cost basis $312 leaves a 53% unrealized gain.")
                        .font(ClavisTypography.serif(14))
                        .foregroundColor(.vqaAccentInk)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            VQASection(eyebrow: "Primary inputs", title: "3 articles drove this") { ForEach(VQA.news.prefix(3)) { item in VQANewsLedgerCard(item: item) } }
            HStack(spacing: 8) { VQAButton("Open NVDA detail", fill: .clear, foreground: .vqaInk) {}; VQAButton("Adjust threshold", fill: .clear, foreground: .vqaInk) {} }.overlay(RoundedRectangle(cornerRadius: VQA.controlRadius).stroke(Color.vqaRule, lineWidth: 1))
        }
    }
}

private struct ClavixVisualQAAddPositionMethod: View {
    var body: some View { VQAScreen(eyebrow: "Choose a method", title: "Add position") { VQAMethodCard(title: "Search the universe", body: "Type a ticker or company name. Available for tracked names.", icon: "magnifyingglass"); VQAMethodCard(title: "Refresh from your brokerage", body: "Connected brokerage can update share counts and cost data.", icon: "arrow.clockwise", badge: "LIVE"); VQAMethodCard(title: "Enter manually", body: "Ticker, shares, and cost basis.", icon: "plus"); VQAMethodCard(title: "Upload CSV", body: "Map exported rows from major brokerages.", icon: "doc", badge: "PRO") } }
}

private struct ClavixVisualQAAddPositionManual: View {
    let outside: Bool
    var body: some View { VQAScreen(eyebrow: outside ? "Outside universe" : "Manual entry", title: outside ? "Limited data" : "Add position") { VQACard { VStack(spacing: 12) { VQAInputRow("Ticker"); VQAInputRow("Shares"); VQAInputRow("Cost basis") } }; if outside { VQACard(fill: .vqaWarnSoft) { Text("This ticker can be saved as portfolio metadata, but full risk scoring requires universe support.").foregroundColor(.vqaInk2) } }; VQAButton("Save position", fill: .vqaInk, foreground: .vqaPaper) {} } }
}

private struct ClavixVisualQAEditPosition: View {
    var body: some View { VQAScreen(eyebrow: "NVDA", title: "Edit position") { VQACard { VStack(spacing: 12) { VQAInputRow("Shares · 420"); VQAInputRow("Cost basis · 312.20"); VQAInputRow("Account · Taxable") } }; VQAButton("Save changes", fill: .vqaInk, foreground: .vqaPaper) {} } }
}

private struct ClavixVisualQADeleteConfirm: View {
    var body: some View { VQAScreen(eyebrow: "NVDA", title: "Remove position") { VQACard(fill: .vqaBadSoft) { Text("Removing this position removes portfolio context for NVDA. Ticker-level risk data remains available through Search.").foregroundColor(.vqaInk2) }; VQAButton("Remove position", fill: .vqaBad, foreground: .white) {}; VQAButton("Keep position", fill: .clear, foreground: .vqaInk) {}.overlay(RoundedRectangle(cornerRadius: 7).stroke(Color.vqaRule, lineWidth: 1)) } }
}

private struct ClavixVisualQAFreeLimitReached: View {
    var body: some View { VQAScreen(eyebrow: "Free plan", title: "Position limit reached") { VQACard(fill: .vqaAccentSoft) { Text("Free accounts can track three positions. Upgrade to add more positions, connect your brokerage, and unlock full history.").foregroundColor(.vqaAccentInk) }; VQAButton("View Pro", fill: .vqaAccent, foreground: .white) {}; VQAButton("Manage positions", fill: .clear, foreground: .vqaInk) {}.overlay(RoundedRectangle(cornerRadius: 7).stroke(Color.vqaRule, lineWidth: 1)) } }
}

private struct ClavixVisualQABrokerageSync: View {
    var body: some View { VQAScreen(eyebrow: "Brokerage", title: "Sync status") { VQACard { VStack(alignment: .leading, spacing: 8) { VQAEyebrow("Connected"); Text("Your brokerage is connected read-only.").font(ClavisTypography.serif(20, weight: .medium)).foregroundColor(.vqaInk); Text("Last sync: today at 6:41 ET").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3) } }; VQASettingsSection("SYNCED") { VQASettingRow("Positions", value: "9"); Divider(); VQASettingRow("Accounts", value: "2"); Divider(); VQASettingRow("Auto-sync", value: "On") }; VQAButton("Sync now", fill: .vqaInk, foreground: .vqaPaper) {} } }
}

private struct ClavixVisualQATrackedTickers: View {
    var body: some View { VQAScreen(eyebrow: "3 names", title: "Tracked tickers") { VQACard(padding: 0) { VStack(spacing: 0) { ForEach(VQA.tracked) { item in VQAHoldingRow(holding: item, tracked: true); if item.id != VQA.tracked.last?.id { Divider() } } } }; VQAButton("Add tracked ticker", fill: .vqaInk, foreground: .vqaPaper) {} } }
}

private struct ClavixVisualQATrackedTickerAdd: View {
    var body: some View { VQAScreen(eyebrow: "Tracked tickers", title: "Add ticker") { VQACard { HStack { Image(systemName: "magnifyingglass").foregroundColor(.vqaInk3); Text("Ticker or company name").foregroundColor(.vqaInk3); Spacer() } }; VQASettingsSection("COMMON NAMES") { VQASettingRow("AMD", value: "BBB"); Divider(); VQASettingRow("META", value: "A"); Divider(); VQASettingRow("TSLA", value: "B") } } }
}

private struct ClavixVisualQATrackedTickerConvert: View {
    var body: some View { VQAScreen(eyebrow: "Tracked ticker", title: "Convert to position") { VQACard { Text("Add shares and cost basis to include this ticker in your portfolio-weighted Morning Report.").foregroundColor(.vqaInk2) }; VQAInputRow("Shares"); VQAInputRow("Cost basis"); VQAButton("Add as position", fill: .vqaInk, foreground: .vqaPaper) {} } }
}

private struct ClavixVisualQAStateScreen: View {
    let title: String
    let eyebrow: String
    let glyph: String
    let message: String
    let cta: String
    var tone: Color = .vqaInk

    init(title: String, eyebrow: String, glyph: String, body: String, cta: String, tone: Color = .vqaInk) {
        self.title = title
        self.eyebrow = eyebrow
        self.glyph = glyph
        self.message = body
        self.cta = cta
        self.tone = tone
    }

    var bodyView: some View {
        VQAScreen(eyebrow: eyebrow, title: title) {
            VStack(spacing: 16) {
                Image(systemName: glyph).font(.system(size: 52, weight: .light)).foregroundColor(tone)
                Text(message).font(ClavisTypography.serif(17)).foregroundColor(.vqaInk2).multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
                VQAButton(cta, fill: tone, foreground: .vqaPaper) {}
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 38)
        }
    }
    var body: some View { bodyView }
}

private struct ClavixVisualQATickerHeldState: View {
    var body: some View { VQAScreen(eyebrow: "Ticker", title: "Already in portfolio") { VQACard { HStack { VQAGrade("BBB"); VStack(alignment: .leading, spacing: 4) { Text("NVDA is already in your book.").font(ClavisTypography.bodyEmphasis).foregroundColor(.vqaInk); Text("420 sh · 15.6% of portfolio value").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3) }; Spacer() } }; VQAButton("View risk profile", fill: .vqaInk, foreground: .vqaPaper) {}; VQAButton("Edit position", fill: .clear, foreground: .vqaInk) {}.overlay(RoundedRectangle(cornerRadius: 7).stroke(Color.vqaRule, lineWidth: 1)) } }
}

private struct ClavixVisualQAOnboardingIntro: View {
    var body: some View { VStack(spacing: 28) { Spacer(); VQABrand(); VQAEyebrow("Welcome to Clavix"); Text("Portfolio risk, measured.").font(ClavisTypography.serif(34, weight: .medium)).foregroundColor(.vqaInk).multilineTextAlignment(.center); Text("Every morning, Clavix tells you what changed overnight, what it means for your book, and how risky every position actually is, with the math shown.").font(ClavisTypography.body).foregroundColor(.vqaInk2).multilineTextAlignment(.center).frame(maxWidth: 300); Spacer(); VQAPill("1 of 7", active: true); VQAButton("Get started", fill: .vqaInk, foreground: .vqaPaper) {} }.padding(24).background(Color.vqaPage.ignoresSafeArea()) }
}

private struct ClavixVisualQAOnboardingDigestPrefs: View {
    var body: some View { VQAScreen(eyebrow: "Step 5 of 7", title: "Report preferences") { VQASettingsSection("DELIVERY") { VQASettingRow("Time", value: "7:00 ET"); Divider(); VQASettingRow("Length", value: "Brief"); Divider(); VQASettingRow("Weekends", value: "Off") }; VQAButton("Continue", fill: .vqaInk, foreground: .vqaPaper) {} } }
}

private struct ClavixVisualQAOnboardingFinal: View {
    var body: some View { VQAScreen(eyebrow: "Ready", title: "Your first report is scheduled") { VQACard(fill: .vqaGoodSoft) { Text("Clavix will generate your Morning Report after the next data refresh. You can still review ticker scores now.").foregroundColor(.vqaInk2) }; VQAButton("Open Clavix", fill: .vqaInk, foreground: .vqaPaper) {} } }
}

private struct ClavixVisualQAPaywall: View {
    var body: some View {
        VStack(spacing: 20) {
            HStack { Button("Close") {}; Spacer(); Text("Upgrade to Pro").font(ClavisTypography.bodyEmphasis); Spacer(); Color.clear.frame(width: 44, height: 1) }.foregroundColor(.vqaInk)
            Image(systemName: "star.square").font(.system(size: 48)).foregroundColor(.vqaAccent)
            Text("Clavix Pro").font(ClavisTypography.serif(28, weight: .medium)).foregroundColor(.vqaInk)
            Text("$20 / month").font(ClavisTypography.mono(22, weight: .semibold)).foregroundColor(.vqaInk)
            Text("14-day free trial · cancel anytime").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3)
            VQACard { VStack(spacing: 0) { VQACompareHeader(); Divider(); VQACompareRow("Positions", "3", "Unlimited"); Divider(); VQACompareRow("Tracked tickers", "5", "Unlimited"); Divider(); VQACompareRow("Brokerage sync", "-", "Yes"); Divider(); VQACompareRow("CSV import", "-", "Yes"); Divider(); VQACompareRow("Report length", "Brief", "Expanded"); Divider(); VQACompareRow("News history", "7 days", "30 days") } }
            Spacer()
            VQAButton("Start free trial", fill: .vqaAccent, foreground: .white) {}
            VQAButton("Maybe later", fill: .clear, foreground: .vqaInk) {}.overlay(RoundedRectangle(cornerRadius: 7).stroke(Color.vqaRule, lineWidth: 1))
            Text("Billed $20/month after trial. Cancel anytime in App Store settings.").font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3).multilineTextAlignment(.center)
        }
        .padding(24)
        .background(Color.vqaPage.ignoresSafeArea())
    }
}

private struct VQABrand: View {
    var body: some View { HStack(spacing: 8) { Image(systemName: "waveform.path.ecg.rectangle"); Text("Clavix").font(ClavisTypography.serif(19, weight: .semibold)) }.foregroundColor(.vqaInk) }
}

private struct VQAButton: View {
    let title: String
    let fill: Color
    let foreground: Color
    let action: () -> Void
    init(_ title: String, fill: Color, foreground: Color, action: @escaping () -> Void = {}) { self.title = title; self.fill = fill; self.foreground = foreground; self.action = action }
    var body: some View { Button(action: action) { Text(title).font(ClavisTypography.inter(15, weight: .semibold)).foregroundColor(foreground).frame(maxWidth: .infinity).frame(height: 48).background(fill).clipShape(RoundedRectangle(cornerRadius: VQA.controlRadius)) }.buttonStyle(.plain) }
}

private struct VQAInputRow: View {
    let label: String
    init(_ label: String) { self.label = label }
    var body: some View { HStack { Text(label).foregroundColor(.vqaInk3); Spacer() }.font(ClavisTypography.body).frame(height: 48).padding(.horizontal, 12).background(Color.vqaPaper2).overlay(RoundedRectangle(cornerRadius: VQA.controlRadius).stroke(Color.vqaRule)).clipShape(RoundedRectangle(cornerRadius: VQA.controlRadius)) }
}

private struct VQAMethodCard: View {
    let title: String
    let description: String
    let icon: String
    var badge: String? = nil
    init(title: String, body: String, icon: String, badge: String? = nil) {
        self.title = title
        self.description = body
        self.icon = icon
        self.badge = badge
    }
    var bodyView: some View {
        VQACard { HStack(spacing: 12) { Image(systemName: icon).frame(width: 28).foregroundColor(.vqaAccent); VStack(alignment: .leading, spacing: 3) { HStack { Text(title).font(ClavisTypography.bodyEmphasis).foregroundColor(.vqaInk); if let badge { Text(badge).font(ClavisTypography.mono(9, weight: .bold)).padding(.horizontal, 5).padding(.vertical, 2).background(Color.vqaAccentSoft).foregroundColor(.vqaAccentInk) } }; Text(description).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2) }; Spacer(); Image(systemName: "chevron.right").font(.system(size: 11)).foregroundColor(.vqaInk4) } }
    }
    var body: some View { bodyView }
}

private struct VQAPill: View {
    let label: String
    var active = false
    init(_ label: String, active: Bool = false) { self.label = label; self.active = active }
    var body: some View { Text(label).font(ClavisTypography.mono(10, weight: .semibold)).foregroundColor(active ? .vqaPaper : .vqaInk2).padding(.horizontal, 10).padding(.vertical, 7).background(active ? Color.vqaInk : Color.vqaPaper).overlay(Capsule().stroke(Color.vqaRule, lineWidth: 1)).clipShape(Capsule()) }
}

private struct VQASectorCell: View {
    let sector: VQA.Sector
    var body: some View { VStack(alignment: .leading, spacing: 8) { Text(sector.symbol).font(ClavisTypography.mono(12, weight: .bold)); Text(sector.name).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2); HStack { Text(sector.change).font(ClavisTypography.mono(12, weight: .semibold)).foregroundColor(sector.tone); Spacer(); Text("w \(sector.weight)").font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3) } }.padding(10).frame(maxWidth: .infinity, alignment: .leading).background(Color.vqaPaper) }
}

private struct VQABookRow: View {
    let holding: VQA.Holding
    var body: some View { HStack(alignment: .center, spacing: 10) { VStack(alignment: .leading, spacing: 3) { Text(holding.ticker).font(ClavisTypography.mono(13, weight: .bold)).foregroundColor(.vqaInk); Text(holding.note).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3).lineLimit(2) }; Spacer(); VQAGrade(holding.grade, size: 24); Text(holding.delta == 0 ? "-" : holding.delta > 0 ? "+\(holding.delta)" : "\(holding.delta)").font(ClavisTypography.mono(11, weight: .semibold)).foregroundColor(holding.delta < 0 ? .vqaBad : holding.delta > 0 ? .vqaGood : .vqaInk3); Text(holding.today).font(ClavisTypography.mono(11, weight: .semibold)).foregroundColor(holding.today.hasPrefix("-") ? .vqaBad : .vqaGood) }.padding(.horizontal, 14).padding(.vertical, 12) }
}

private struct VQAHoldingRow: View {
    let holding: VQA.Holding
    var tracked = false
    var body: some View { HStack { VStack(alignment: .leading, spacing: 3) { Text(holding.ticker).font(ClavisTypography.mono(14, weight: .bold)).foregroundColor(.vqaInk); Text(holding.name).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2); Text(tracked ? "tracked ticker" : "\(holding.weight) of book").font(ClavisTypography.mono(11, weight: .regular)).foregroundColor(.vqaInk3) }; Spacer(); VStack(alignment: .trailing, spacing: 5) { VQAGrade(holding.grade, size: 28); Text(holding.value).font(ClavisTypography.mono(12, weight: .semibold)).foregroundColor(.vqaInk); Text(holding.today).font(ClavisTypography.mono(11, weight: .regular)).foregroundColor(holding.today.hasPrefix("-") ? .vqaBad : .vqaGood) } }.padding(.horizontal, 14).padding(.vertical, 12) }
}

private struct VQASearchRow: View {
    let holding: VQA.Holding
    var body: some View { HStack { VStack(alignment: .leading, spacing: 2) { Text(holding.ticker).font(ClavisTypography.mono(14, weight: .bold)).foregroundColor(.vqaInk); Text(holding.name).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2) }; Spacer(); VQAGrade(holding.grade, size: 22); Text("\(holding.score)").font(ClavisTypography.mono(11, weight: .regular)).foregroundColor(.vqaInk3); Image(systemName: "chevron.right").font(.system(size: 10)).foregroundColor(.vqaInk4) }.padding(.horizontal, 14).padding(.vertical, 12) }
}

private struct VQAAlertRow: View {
    let alert: VQA.Alert
    var body: some View { VQACard { HStack(alignment: .top, spacing: 12) { Circle().fill(alert.tone).frame(width: 8, height: 8).padding(.top, 6); VStack(alignment: .leading, spacing: 5) { HStack { Text(alert.category).font(ClavisTypography.mono(9, weight: .bold)).foregroundColor(alert.tone); Text(alert.time).font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3) }; Text(alert.title).font(ClavisTypography.bodyEmphasis).foregroundColor(.vqaInk); Text(alert.detail).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2) }; Spacer(); Text(alert.meta).font(ClavisTypography.mono(10, weight: .bold)).foregroundColor(.vqaInk3) } } }
}

private struct VQADaySep: View {
    let label: String
    init(_ label: String) { self.label = label }
    var body: some View { Text(label.uppercased()).font(ClavisTypography.mono(10, weight: .bold)).tracking(0.7).foregroundColor(.vqaInk3).padding(.top, 6) }
}

private struct VQASettingsSection<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content
    init(_ title: String, @ViewBuilder content: () -> Content) { self.title = title; self.content = content() }
    var body: some View { VStack(alignment: .leading, spacing: 8) { VQAEyebrow(title); VQACard { VStack(spacing: 0) { content } } } }
}

private struct VQASettingRow: View {
    let title: String
    let value: String
    var detail: String? = nil
    init(_ title: String, value: String, detail: String? = nil) { self.title = title; self.value = value; self.detail = detail }
    var body: some View { HStack(alignment: .center) { VStack(alignment: .leading, spacing: 2) { Text(title).font(ClavisTypography.bodyEmphasis).foregroundColor(.vqaInk); if let detail { Text(detail).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3) } }; Spacer(); Text(value).font(ClavisTypography.mono(12, weight: .regular)).foregroundColor(value == "Live" || value == "On" ? .vqaGood : value.contains("Pro") ? .vqaAccent : .vqaInk3) }.padding(.vertical, 10) }
}

private struct VQADimensionRow: View {
    let dimension: VQA.Dimension
    var body: some View { VStack(spacing: 6) { HStack { VStack(alignment: .leading, spacing: 2) { Text(dimension.name).font(ClavisTypography.bodyEmphasis).foregroundColor(.vqaInk); Text("Updated today · tap for audit").font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk3) }; Spacer(); Text("\(dimension.score)").font(ClavisTypography.mono(18, weight: .semibold)).foregroundColor(scoreTone(dimension.score)); Image(systemName: "chevron.right").font(.system(size: 10)).foregroundColor(.vqaInk4) }; VQAScoreBar(score: dimension.score) }.padding(.horizontal, 14).padding(.vertical, 10) }
}

private struct VQACompositeDimensionRow: View {
    let dimension: VQA.Dimension
    var body: some View { VStack(alignment: .leading, spacing: 8) { HStack(alignment: .firstTextBaseline, spacing: 10) { Text(dimension.code).font(ClavisTypography.mono(10, weight: .bold)).foregroundColor(.vqaInk3).frame(width: 42, alignment: .leading); Text(dimension.name).font(ClavisTypography.bodyEmphasis).foregroundColor(.vqaInk).lineLimit(1).minimumScaleFactor(0.82); Spacer(); Text("\(dimension.score)").font(ClavisTypography.mono(17, weight: .semibold)).foregroundColor(scoreTone(dimension.score)); Text(dimension.delta == 0 ? "-" : dimension.delta > 0 ? "+\(dimension.delta)" : "\(dimension.delta)").font(ClavisTypography.mono(10, weight: .semibold)).foregroundColor(dimension.delta < 0 ? .vqaBad : dimension.delta > 0 ? .vqaGood : .vqaInk3).frame(width: 32, alignment: .trailing) }; VQAScoreBar(score: dimension.score) }.padding(.vertical, 11) }
}

private struct VQAFormulaRow: View {
    let label: String
    let value: String
    var emphasized = false
    var body: some View { HStack(alignment: .firstTextBaseline, spacing: 12) { Text(label).font(ClavisTypography.mono(10, weight: .bold)).tracking(0.6).foregroundColor(.vqaInk3).frame(width: 78, alignment: .leading); Text(value).font(ClavisTypography.mono(emphasized ? 18 : 13, weight: emphasized ? .semibold : .regular)).foregroundColor(emphasized ? .vqaInk : .vqaInk2).lineLimit(2).minimumScaleFactor(0.72).frame(maxWidth: .infinity, alignment: .leading) }.padding(.horizontal, 14).padding(.vertical, emphasized ? 14 : 12).background(emphasized ? Color.vqaAccentSoft : Color.clear) }
}

private struct VQADriverCard: View {
    let tone: Color
    let soft: Color
    let tag: String
    let title: String
    let detail: String
    let score: String
    let dimension: String
    init(tone: Color, soft: Color, tag: String, title: String, body: String, score: String, dimension: String) { self.tone = tone; self.soft = soft; self.tag = tag; self.title = title; self.detail = body; self.score = score; self.dimension = dimension }
    var body: some View { VQACard(fill: soft) { HStack(alignment: .top, spacing: 10) { VStack(alignment: .leading, spacing: 7) { HStack { Text(tag).font(ClavisTypography.mono(9, weight: .bold)).foregroundColor(.white).padding(.horizontal, 7).padding(.vertical, 3).background(tone); Text("via \(dimension)").font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3) }; Text(title).font(ClavisTypography.serif(16, weight: .medium)).foregroundColor(.vqaInk); Text(detail).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2) }; Spacer(); VStack(alignment: .trailing, spacing: 2) { Text("SCORE").font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3); Text(score).font(ClavisTypography.mono(18, weight: .bold)).foregroundColor(tone) } } } }
}

private struct VQANewsLedgerCard: View {
    let item: VQA.NewsItem
    var body: some View { VQACard(padding: 0) { VStack(alignment: .leading, spacing: 7) { HStack(spacing: 8) { Text(item.tier).font(ClavisTypography.mono(9, weight: .bold)).padding(.horizontal, 6).padding(.vertical, 2).overlay(Rectangle().stroke(Color.vqaRule, lineWidth: 1)); Text(item.source).font(ClavisTypography.mono(11, weight: .semibold)).foregroundColor(.vqaInk2); Text("· \(item.time) · \(item.topic)").font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3); Spacer(); Text("● \(item.score)").font(ClavisTypography.mono(10, weight: .bold)).foregroundColor(item.tone) }; Text(item.headline).font(ClavisTypography.serif(16, weight: .medium)).foregroundColor(.vqaInk); Text("Why this score? · weight 60").font(ClavisTypography.vqaCaption).foregroundColor(.vqaAccent) }.padding(12) } }
}

private struct VQARomanSection<Content: View>: View {
    let roman: String
    let title: String
    let tag: String
    @ViewBuilder let content: Content
    init(_ roman: String, _ title: String, tag: String, @ViewBuilder content: () -> Content) { self.roman = roman; self.title = title; self.tag = tag; self.content = content() }
    var body: some View { VStack(alignment: .leading, spacing: 10) { HStack(alignment: .firstTextBaseline) { Text("§ \(roman)").font(ClavisTypography.serif(22, weight: .medium)).foregroundColor(.vqaInk); Text(title).font(ClavisTypography.serif(22, weight: .medium)).foregroundColor(.vqaInk); Spacer(); VQAEyebrow(tag) }; content }.padding(.top, 8) }
}

private struct VQASectorLedger: View {
    var body: some View { VQACard(padding: 0) { VStack(spacing: 0) { ForEach(VQA.sectors.prefix(3)) { s in HStack { Text(s.symbol).font(ClavisTypography.mono(12, weight: .bold)).frame(width: 42, alignment: .leading); VStack(alignment: .leading) { Text(s.name).font(ClavisTypography.vqaCaption); Text("weight \(s.weight)").font(ClavisTypography.mono(10, weight: .regular)).foregroundColor(.vqaInk3) }; Spacer(); Text(s.change).font(ClavisTypography.mono(12, weight: .semibold)).foregroundColor(s.tone) }.padding(12); if s.id != VQA.sectors.prefix(3).last?.id { Divider() } } } } }
}

private struct VQAPositionLedger: View {
    var body: some View { VQACard(padding: 0) { VStack(spacing: 0) { HStack { Text("SYM"); Text("NOTE").padding(.leading, 18); Spacer(); Text("GRADE"); Text("DELTA") }.font(ClavisTypography.mono(9, weight: .bold)).foregroundColor(.vqaInk3).padding(10); Divider(); ForEach(VQA.holdings.prefix(3)) { h in HStack(alignment: .top) { Text(h.ticker).font(ClavisTypography.mono(12, weight: .bold)).frame(width: 44, alignment: .leading); Text(h.note).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2).lineLimit(2); Spacer(); VQAGrade(h.grade, size: 22); Text(h.delta == 0 ? "-" : "\(h.delta)").font(ClavisTypography.mono(10, weight: .bold)).foregroundColor(h.delta < 0 ? .vqaBad : .vqaGood).frame(width: 28) }.padding(10); if h.id != VQA.holdings.prefix(3).last?.id { Divider() } } } } }
}

private struct VQACalendarLine: View {
    let time: String
    let type: String
    let title: String
    init(_ time: String, _ type: String, _ title: String) { self.time = time; self.type = type; self.title = title }
    var body: some View { HStack(spacing: 12) { Text(time).font(ClavisTypography.mono(12, weight: .semibold)).frame(width: 46, alignment: .leading); Text(type).font(ClavisTypography.mono(9, weight: .bold)).foregroundColor(.vqaInk3).frame(width: 42, alignment: .leading); Text(title).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk2); Spacer() }.padding(12) }
}

private struct VQARadar: View {
    let values: [Int]
    var body: some View {
        GeometryReader { geo in
            let side = min(geo.size.width, geo.size.height)
            let center = CGPoint(x: geo.size.width / 2, y: geo.size.height / 2)
            let radius = side * 0.42
            ZStack {
                ForEach(1...4, id: \.self) { ring in
                    Polygon(sides: 5, scale: CGFloat(ring) / 4)
                        .stroke(Color.vqaRule, lineWidth: 1)
                        .frame(width: radius * 2, height: radius * 2)
                        .position(center)
                }
                Path { path in
                    for index in 0..<5 {
                        let point = radarPoint(index: index, value: values.indices.contains(index) ? values[index] : 50, center: center, radius: radius)
                        if index == 0 { path.move(to: point) } else { path.addLine(to: point) }
                    }
                    path.closeSubpath()
                }
                .fill(Color.vqaAccent.opacity(0.18))
                Path { path in
                    for index in 0..<5 {
                        let point = radarPoint(index: index, value: values.indices.contains(index) ? values[index] : 50, center: center, radius: radius)
                        if index == 0 { path.move(to: point) } else { path.addLine(to: point) }
                    }
                    path.closeSubpath()
                }
                .stroke(Color.vqaAccent, lineWidth: 2)
            }
        }
    }
    private func radarPoint(index: Int, value: Int, center: CGPoint, radius: CGFloat) -> CGPoint {
        let angle = (-CGFloat.pi / 2) + (CGFloat(index) * 2 * .pi / 5)
        let scaled = radius * CGFloat(value) / 100
        return CGPoint(x: center.x + cos(angle) * scaled, y: center.y + sin(angle) * scaled)
    }
}

private struct Polygon: Shape {
    let sides: Int
    let scale: CGFloat
    func path(in rect: CGRect) -> Path {
        var path = Path()
        let center = CGPoint(x: rect.midX, y: rect.midY)
        let radius = min(rect.width, rect.height) / 2 * scale
        for index in 0..<sides {
            let angle = (-CGFloat.pi / 2) + CGFloat(index) * 2 * .pi / CGFloat(sides)
            let point = CGPoint(x: center.x + cos(angle) * radius, y: center.y + sin(angle) * radius)
            if index == 0 { path.move(to: point) } else { path.addLine(to: point) }
        }
        path.closeSubpath()
        return path
    }
}

private struct VQALineChart: View {
    var body: some View {
        GeometryReader { geo in
            Path { path in
                let points: [CGFloat] = [0.58, 0.52, 0.64, 0.48, 0.42, 0.55, 0.38]
                for (index, y) in points.enumerated() {
                    let x = geo.size.width * CGFloat(index) / CGFloat(points.count - 1)
                    let p = CGPoint(x: x, y: geo.size.height * y)
                    if index == 0 { path.move(to: p) } else { path.addLine(to: p) }
                }
            }
            .stroke(Color.vqaAccent, style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
            VStack { Spacer(); Rectangle().fill(Color.vqaRule).frame(height: 1) }
        }
    }
}

private struct VQACompareHeader: View { var body: some View { HStack { Spacer(); Text("FREE").font(ClavisTypography.mono(10, weight: .bold)).foregroundColor(.vqaInk3).frame(width: 78); Text("PRO").font(ClavisTypography.mono(10, weight: .bold)).foregroundColor(.vqaAccent).frame(width: 92) }.padding(.bottom, 8) } }
private struct VQACompareRow: View { let feature: String; let free: String; let pro: String; init(_ feature: String, _ free: String, _ pro: String) { self.feature = feature; self.free = free; self.pro = pro }; var body: some View { HStack { Text(feature).font(ClavisTypography.vqaCaption).foregroundColor(.vqaInk); Spacer(); Text(free).font(ClavisTypography.mono(11, weight: .regular)).foregroundColor(.vqaInk3).frame(width: 78); Text(pro).font(ClavisTypography.mono(11, weight: .semibold)).foregroundColor(.vqaAccent).frame(width: 92) }.padding(.vertical, 10) } }
#endif
