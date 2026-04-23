import Foundation

enum Config {
    static let supabaseUrl = "https://uwvwulhkxtzabykelvam.supabase.co"
    static let supabaseAnonKey: String = {
        let envValue = ProcessInfo.processInfo.environment["SUPABASE_ANON_KEY"]?.trimmingCharacters(in: .whitespacesAndNewlines)
        if let envValue, !envValue.isEmpty { return envValue }

        if let bundleValue = Bundle.main.object(forInfoDictionaryKey: "SUPABASE_ANON_KEY") as? String {
            let trimmed = bundleValue.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty { return trimmed }
        }

        return ""
    }()
    static let backendBaseUrl: String = {
        if let bundleValue = Bundle.main.object(forInfoDictionaryKey: "BACKEND_BASE_URL") as? String {
            let trimmed = bundleValue.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty { return trimmed }
        }

        return "https://clavis.andoverdigital.com"
    }()
}

enum APIError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case unauthorized
    case serverError(Int)
    case decodingError(Error)
    case networkError(String, Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Invalid URL"
        case .invalidResponse: return "Invalid response from server"
        case .unauthorized: return "Unauthorized - please log in again"
        case .serverError(let code): return "Server error: \(code)"
        case .decodingError(let error): return "Failed to decode response: \(error.localizedDescription)"
        case .networkError(let url, let error): return "Network error for \(url): \(error.localizedDescription)"
        }
    }
}

class APIService {
    static let shared = APIService()

    private let baseURL: String
    private let decoder: JSONDecoder
    private let session: URLSession

    private init() {
        self.baseURL = Config.backendBaseUrl
        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)
            if let date = FlexibleDateDecoder.decode(dateString) {
                return date
            }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode date")
        }
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 12
        configuration.timeoutIntervalForResource = 90
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.urlCache = nil
        self.session = URLSession(configuration: configuration)
    }

    private func makeRequest(
        path: String,
        method: String = "GET",
        body: Data? = nil,
        timeoutInterval: TimeInterval = 12
    ) async throws -> Data {
        guard let url = URL(string: "\(baseURL)\(path)") else {
            print("API request invalid URL base=\(baseURL) path=\(path)")
            throw APIError.invalidURL
        }

        print("API request \(method) \(url.absoluteString)")

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        request.setValue("no-cache", forHTTPHeaderField: "Pragma")

        if let token = await SupabaseAuthService.shared.getAccessToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            request.httpBody = body
        }

        do {
            request.timeoutInterval = timeoutInterval
            let (data, response) = try await session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.invalidResponse
            }

            switch httpResponse.statusCode {
            case 200...299:
                return data
            case 401:
                throw APIError.unauthorized
            default:
                throw APIError.serverError(httpResponse.statusCode)
            }
        } catch let error as APIError {
            print("API request failed \(method) \(url.absoluteString): \(error)")
            throw error
        } catch let error as URLError where error.code == .cancelled {
            throw CancellationError()
        } catch {
            print("API request failed \(method) \(url.absoluteString): \(error)")
            throw APIError.networkError(url.absoluteString, error)
        }
    }

    struct CreateHoldingRequest: Encodable {
        let ticker: String
        let shares: Double
        let purchase_price: Double
        let archetype: String
    }

    // MARK: - Holdings

    func fetchHoldings() async throws -> [Position] {
        let data = try await makeRequest(path: "/holdings")
        return try decoder.decode([Position].self, from: data)
    }

    func fetchDashboard() async throws -> DashboardResponse {
        let data = try await makeRequest(path: "/dashboard")
        return try decoder.decode(DashboardResponse.self, from: data)
    }

    func createHolding(ticker: String, shares: Double, purchasePrice: Double, archetype: Archetype) async throws -> Position {
        let req = CreateHoldingRequest(ticker: ticker, shares: shares, purchase_price: purchasePrice, archetype: archetype.rawValue)
        let body = try JSONEncoder().encode(req)
        let data = try await makeRequest(path: "/holdings", method: "POST", body: body)
        return try decoder.decode(Position.self, from: data)
    }

    // MARK: - Tickers

    func searchTickers(query: String, limit: Int = 20) async throws -> [TickerSearchResult] {
        let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        let data = try await makeRequest(path: "/tickers/search?q=\(encoded)&limit=\(limit)")
        let response = try decoder.decode(TickerSearchResponse.self, from: data)
        return response.results
    }

    func fetchTickerDetail(ticker: String) async throws -> TickerDetailResponse {
        let data = try await makeRequest(path: "/tickers/\(ticker)")
        return try decoder.decode(TickerDetailResponse.self, from: data)
    }

    func refreshTicker(ticker: String) async throws -> TickerRefreshResponse {
        let data = try await makeRequest(path: "/tickers/\(ticker)/refresh", method: "POST", body: Data())
        return try decoder.decode(TickerRefreshResponse.self, from: data)
    }

    func fetchTickerRefreshStatus(ticker: String) async throws -> TickerRefreshStatusResponse {
        let data = try await makeRequest(path: "/tickers/\(ticker)/refresh-status")
        return try decoder.decode(TickerRefreshStatusResponse.self, from: data)
    }

    // MARK: - Watchlists

    struct WatchlistItemCreate: Encodable {
        let ticker: String
    }

    func fetchWatchlists() async throws -> [Watchlist] {
        let data = try await makeRequest(path: "/watchlists")
        let response = try decoder.decode(WatchlistsResponse.self, from: data)
        return response.watchlists
    }

    func addToWatchlist(ticker: String) async throws -> Watchlist {
        let body = try JSONEncoder().encode(WatchlistItemCreate(ticker: ticker))
        let data = try await makeRequest(path: "/watchlists/default/items", method: "POST", body: body)
        return try decoder.decode(Watchlist.self, from: data)
    }

    func removeFromWatchlist(ticker: String) async throws -> Watchlist {
        let data = try await makeRequest(path: "/watchlists/default/items/\(ticker)", method: "DELETE")
        return try decoder.decode(Watchlist.self, from: data)
    }

    func deleteHolding(id: String) async throws {
        _ = try await makeRequest(path: "/holdings/\(id)", method: "DELETE")
    }

    // MARK: - Digest

    func fetchTodayDigest(forceRefresh: Bool = false, timeoutInterval: TimeInterval = 75) async throws -> DigestResponse {
        let path = forceRefresh ? "/digest?force_refresh=true" : "/digest"
        let data = try await makeRequest(path: path, timeoutInterval: timeoutInterval)
        return try decoder.decode(DigestResponse.self, from: data)
    }

    func fetchDigestHistory(limit: Int = 7, timeoutInterval: TimeInterval = 75) async throws -> [Digest] {
        let data = try await makeRequest(
            path: "/digest/history?limit=\(limit)",
            timeoutInterval: timeoutInterval
        )
        return try decoder.decode([Digest].self, from: data)
    }

    // MARK: - Positions

    func fetchPositionDetail(id: String) async throws -> PositionDetailResponse {
        let data = try await makeRequest(path: "/positions/\(id)")
        return try decoder.decode(PositionDetailResponse.self, from: data)
    }

    // MARK: - Alerts

    func fetchAlerts() async throws -> [Alert] {
        let data = try await makeRequest(path: "/alerts")
        return try decoder.decode([Alert].self, from: data)
    }

    // MARK: - News

    func fetchNewsFeed(limit: Int = 30) async throws -> NewsFeedResponse {
        let data = try await makeRequest(path: "/news?limit=\(limit)")
        return try decoder.decode(NewsFeedResponse.self, from: data)
    }

    func fetchNewsArticle(id: String) async throws -> NewsArticleResponse {
        let encoded = id.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? id
        let data = try await makeRequest(path: "/news/\(encoded)")
        return try decoder.decode(NewsArticleResponse.self, from: data)
    }

    // MARK: - Analysis Runs

    struct LatestAnalysisRunResponse: Codable {
        let analysisRun: AnalysisRun?
        let status: String
        let message: String?

        enum CodingKeys: String, CodingKey {
            case analysisRun = "analysis_run"
            case status
            case message
        }
    }

    func fetchLatestAnalysisRun() async throws -> AnalysisRun? {
        let data = try await makeRequest(path: "/analysis-runs/latest")
        let response = try decoder.decode(LatestAnalysisRunResponse.self, from: data)
        return response.analysisRun
    }

    func fetchAnalysisRun(id: String) async throws -> AnalysisRun {
        let data = try await makeRequest(path: "/analysis-runs/\(id)")
        return try decoder.decode(AnalysisRun.self, from: data)
    }

    // MARK: - Trigger

    struct TriggerAnalysisRequest: Encodable {
        let position_id: String?
    }

    func triggerAnalysis(positionId: String? = nil) async throws -> TriggerAnalysisResponse {
        let body: Data?
        if let positionId {
            body = try JSONEncoder().encode(TriggerAnalysisRequest(position_id: positionId))
        } else {
            body = nil
        }
        let data = try await makeRequest(path: "/trigger-analysis", method: "POST", body: body)
        return try decoder.decode(TriggerAnalysisResponse.self, from: data)
    }

    // MARK: - Preferences

    struct PreferencesResponse: Codable {
        let digestTime: String?
        let notificationsEnabled: Bool?
        let summaryLength: String?
        let weekdayOnly: Bool?
        let alertsGradeChanges: Bool?
        let alertsMajorEvents: Bool?
        let alertsPortfolioRisk: Bool?
        let alertsLargePriceMoves: Bool?
        let quietHoursEnabled: Bool?
        let quietHoursStart: String?
        let quietHoursEnd: String?
        let hasCompletedOnboarding: Bool?
        let name: String?
        let birthYear: Int?
        let subscriptionTier: String?

        enum CodingKeys: String, CodingKey {
            case digestTime = "digest_time"
            case notificationsEnabled = "notifications_enabled"
            case summaryLength = "summary_length"
            case weekdayOnly = "weekday_only"
            case alertsGradeChanges = "alerts_grade_changes"
            case alertsMajorEvents = "alerts_major_events"
            case alertsPortfolioRisk = "alerts_portfolio_risk"
            case alertsLargePriceMoves = "alerts_large_price_moves"
            case quietHoursEnabled = "quiet_hours_enabled"
            case quietHoursStart = "quiet_hours_start"
            case quietHoursEnd = "quiet_hours_end"
            case hasCompletedOnboarding = "has_completed_onboarding"
            case name
            case birthYear = "birth_year"
            case subscriptionTier = "subscription_tier"
        }
    }

    struct BrokerageConnection: Codable, Identifiable {
        let id: String
        let institutionName: String?
        let broker: String?
        let disabled: Bool
        let disabledDate: Date?

        enum CodingKeys: String, CodingKey {
            case id
            case institutionName = "institution_name"
            case broker
            case disabled
            case disabledDate = "disabled_date"
        }
    }

    struct BrokerageAccount: Codable, Identifiable {
        let id: String
        let brokerageAuthorizationId: String?
        let institutionName: String?
        let name: String?
        let numberMasked: String?
        let lastHoldingsSyncAt: Date?
        let isPaper: Bool

        enum CodingKeys: String, CodingKey {
            case id
            case brokerageAuthorizationId = "brokerage_authorization_id"
            case institutionName = "institution_name"
            case name
            case numberMasked = "number_masked"
            case lastHoldingsSyncAt = "last_holdings_sync_at"
            case isPaper = "is_paper"
        }
    }

    struct BrokerageStatusResponse: Codable {
        let configured: Bool
        let registered: Bool
        let connected: Bool
        let autoSyncEnabled: Bool
        let syncMode: String
        let lastSyncAt: Date?
        let connections: [BrokerageConnection]
        let accounts: [BrokerageAccount]

        enum CodingKeys: String, CodingKey {
            case configured
            case registered
            case connected
            case autoSyncEnabled = "auto_sync_enabled"
            case syncMode = "sync_mode"
            case lastSyncAt = "last_sync_at"
            case connections
            case accounts
        }
    }

    struct BrokerageConnectRequest: Encodable {
        let broker: String?
        let reconnect_connection_id: String?
    }

    struct BrokerageConnectResponse: Codable {
        let redirectURI: String
        let sessionId: String?

        enum CodingKeys: String, CodingKey {
            case redirectURI = "redirect_uri"
            case sessionId = "session_id"
        }
    }

    struct BrokerageSyncRequest: Encodable {
        let refresh_remote: Bool
    }

    struct BrokerageSyncResponse: Codable {
        let connectedAccounts: Int
        let createdPositions: Int
        let updatedPositions: Int
        let deletedPositions: Int
        let skippedPositions: Int
        let lastSyncAt: Date?

        enum CodingKeys: String, CodingKey {
            case connectedAccounts = "connected_accounts"
            case createdPositions = "created_positions"
            case updatedPositions = "updated_positions"
            case deletedPositions = "deleted_positions"
            case skippedPositions = "skipped_positions"
            case lastSyncAt = "last_sync_at"
        }
    }

    struct BrokerageSettingsUpdate: Encodable {
        let auto_sync_enabled: Bool
    }

    func fetchPreferences() async throws -> PreferencesResponse {
        let data = try await makeRequest(path: "/preferences")
        return try decoder.decode(PreferencesResponse.self, from: data)
    }

    func fetchBrokerageStatus() async throws -> BrokerageStatusResponse {
        let data = try await makeRequest(path: "/brokerage/status")
        return try decoder.decode(BrokerageStatusResponse.self, from: data)
    }

    func createBrokerageConnectLink(broker: String? = nil, reconnectConnectionId: String? = nil) async throws -> BrokerageConnectResponse {
        let body = try JSONEncoder().encode(
            BrokerageConnectRequest(
                broker: broker,
                reconnect_connection_id: reconnectConnectionId
            )
        )
        let data = try await makeRequest(path: "/brokerage/connect", method: "POST", body: body)
        return try decoder.decode(BrokerageConnectResponse.self, from: data)
    }

    func syncBrokerage(refreshRemote: Bool = false) async throws -> BrokerageSyncResponse {
        let body = try JSONEncoder().encode(BrokerageSyncRequest(refresh_remote: refreshRemote))
        let data = try await makeRequest(path: "/brokerage/sync", method: "POST", body: body, timeoutInterval: 60)
        return try decoder.decode(BrokerageSyncResponse.self, from: data)
    }

    func updateBrokerageSettings(autoSyncEnabled: Bool) async throws {
        let body = try JSONEncoder().encode(BrokerageSettingsUpdate(auto_sync_enabled: autoSyncEnabled))
        _ = try await makeRequest(path: "/brokerage/settings", method: "PATCH", body: body)
    }

    func disconnectBrokerage() async throws {
        _ = try await makeRequest(path: "/brokerage/disconnect", method: "DELETE")
    }

    struct PreferencesUpdate: Encodable {
        let digest_time: String?
        let notifications_enabled: Bool?
        let summary_length: String?
        let weekday_only: Bool?
    }

    func updatePreferences(digestTime: String?, notificationsEnabled: Bool?, summaryLength: String?, weekdayOnly: Bool?) async throws {
        let update = PreferencesUpdate(
            digest_time: digestTime,
            notifications_enabled: notificationsEnabled,
            summary_length: summaryLength,
            weekday_only: weekdayOnly
        )
        let body = try JSONEncoder().encode(update)
        _ = try await makeRequest(path: "/preferences", method: "PATCH", body: body)
    }

    struct AlertPreferencesUpdate: Encodable {
        let alerts_grade_changes: Bool?
        let alerts_major_events: Bool?
        let alerts_portfolio_risk: Bool?
        let alerts_large_price_moves: Bool?
        let quiet_hours_enabled: Bool?
        let quiet_hours_start: String?
        let quiet_hours_end: String?
    }

    func updateAlertPreferences(
        gradeChanges: Bool,
        majorEvents: Bool,
        portfolioRisk: Bool,
        largePriceMoves: Bool? = nil,
        quietHoursEnabled: Bool,
        quietHoursStart: Date,
        quietHoursEnd: Date
    ) async throws {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        let update = AlertPreferencesUpdate(
            alerts_grade_changes: gradeChanges,
            alerts_major_events: majorEvents,
            alerts_portfolio_risk: portfolioRisk,
            alerts_large_price_moves: largePriceMoves,
            quiet_hours_enabled: quietHoursEnabled,
            quiet_hours_start: formatter.string(from: quietHoursStart),
            quiet_hours_end: formatter.string(from: quietHoursEnd)
        )
        let body = try JSONEncoder().encode(update)
        _ = try await makeRequest(path: "/preferences/alerts", method: "PATCH", body: body)
    }

    // MARK: - Onboarding

    func acknowledgeOnboarding() async throws {
        _ = try await makeRequest(path: "/preferences/acknowledge", method: "POST", body: Data())
    }

    struct ProfileUpdate: Encodable {
        let name: String?
        let birth_year: Int?
    }

    func updateProfile(name: String?, birthYear: Int?) async throws {
        let update = ProfileUpdate(name: name, birth_year: birthYear)
        let body = try JSONEncoder().encode(update)
        _ = try await makeRequest(path: "/preferences/profile", method: "POST", body: body)
    }

    func exportAccount() async throws -> Data {
        try await makeRequest(path: "/account/export")
    }

    func deleteAccount() async throws {
        _ = try await makeRequest(path: "/account", method: "DELETE")
    }

    // MARK: - Prices

    func fetchPriceHistory(ticker: String, days: Int = 30) async throws -> PriceHistoryResponse {
        let data = try await makeRequest(path: "/prices/\(ticker)?days=\(days)", timeoutInterval: 35)
        return try decoder.decode(PriceHistoryResponse.self, from: data)
    }

    // MARK: - Device Token

    struct DeviceTokenUpdate: Encodable {
        let apns_token: String
    }

    func registerDeviceToken(_ token: String) async throws {
        let update = DeviceTokenUpdate(apns_token: token)
        let body = try JSONEncoder().encode(update)
        _ = try await makeRequest(path: "/preferences/device-token", method: "POST", body: body)
    }
}

struct PositionDetailResponse: Codable {
    let position: Position
    let currentScore: RiskScore?
    let currentAnalysis: PositionAnalysis?
    let methodology: String?
    let dimensionBreakdown: [String: String]?
    let latestEventAnalyses: [EventAnalysis]
    let mirofishUsedThisCycle: Bool
    let recentNews: [NewsItem]
    let recentAlerts: [Alert]

    enum CodingKeys: String, CodingKey {
        case position
        case currentScore = "current_score"
        case currentAnalysis = "current_analysis"
        case methodology
        case dimensionBreakdown = "dimension_breakdown"
        case latestEventAnalyses = "latest_event_analyses"
        case mirofishUsedThisCycle = "mirofish_used_this_cycle"
        case recentNews = "recent_news"
        case recentAlerts = "recent_alerts"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        position = try container.decode(Position.self, forKey: .position)
        currentScore = try? container.decodeIfPresent(RiskScore.self, forKey: .currentScore)
        currentAnalysis = try? container.decodeIfPresent(PositionAnalysis.self, forKey: .currentAnalysis)
        methodology = try container.decodeIfPresent(String.self, forKey: .methodology)
        dimensionBreakdown = try? container.decodeIfPresent([String: String].self, forKey: .dimensionBreakdown)
        latestEventAnalyses = (try? container.decode([EventAnalysis].self, forKey: .latestEventAnalyses)) ?? []
        mirofishUsedThisCycle = (try? container.decode(Bool.self, forKey: .mirofishUsedThisCycle)) ?? false
        recentNews = (try? container.decode([NewsItem].self, forKey: .recentNews)) ?? []
        recentAlerts = (try? container.decode([Alert].self, forKey: .recentAlerts)) ?? []
    }
}

struct TriggerAnalysisResponse: Codable {
    let status: String
    let userId: String?
    let analysisRunId: String?
    let progress: Int?
    let positionsProcessed: Int?
    let eventsProcessed: Int?
    let eventsAnalyzed: Int?
    let overallGrade: String?
    let digestReady: Bool?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case status
        case userId = "user_id"
        case analysisRunId = "analysis_run_id"
        case progress
        case positionsProcessed = "positions_processed"
        case eventsProcessed = "events_processed"
        case eventsAnalyzed = "events_analyzed"
        case overallGrade = "overall_grade"
        case digestReady = "digest_ready"
        case error
    }
}

struct TickerSearchResponse: Codable {
    let results: [TickerSearchResult]
    let message: String?
}

struct TickerSearchResult: Identifiable, Codable, Hashable {
    let ticker: String
    let companyName: String
    let exchange: String?
    let sector: String?
    let industry: String?
    let price: Double?
    let priceAsOf: Date?
    let grade: String?
    let safetyScore: Double?
    let analysisAsOf: Date?
    let summary: String?
    let isSupported: Bool

    var id: String { ticker }

    enum CodingKeys: String, CodingKey {
        case ticker
        case companyName = "company_name"
        case exchange
        case sector
        case industry
        case price
        case priceAsOf = "price_as_of"
        case grade
        case safetyScore = "safety_score"
        case analysisAsOf = "analysis_as_of"
        case summary
        case isSupported = "is_supported"
    }
}

struct TickerDetailResponse: Codable {
    let ticker: String
    let profile: TickerProfile
    let position: Position
    let latestPrice: TickerLatestPrice
    let latestRiskSnapshot: TickerRiskSnapshot?
    let currentScore: RiskScore?
    let currentAnalysis: PositionAnalysis?
    let methodology: String?
    let dimensionBreakdown: [String: String]?
    let latestEventAnalyses: [EventAnalysis]
    let recentNews: [NewsItem]
    let recentAlerts: [Alert]
    let freshness: TickerFreshness
    let userContext: TickerUserContext

    enum CodingKeys: String, CodingKey {
        case ticker
        case profile
        case position
        case latestPrice = "latest_price"
        case latestRiskSnapshot = "latest_risk_snapshot"
        case currentScore = "current_score"
        case currentAnalysis = "current_analysis"
        case methodology
        case dimensionBreakdown = "dimension_breakdown"
        case latestEventAnalyses = "latest_event_analyses"
        case recentNews = "recent_news"
        case recentAlerts = "recent_alerts"
        case freshness
        case userContext = "user_context"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        ticker = try container.decode(String.self, forKey: .ticker)
        profile = try container.decode(TickerProfile.self, forKey: .profile)
        position = try container.decode(Position.self, forKey: .position)
        latestPrice = try container.decode(TickerLatestPrice.self, forKey: .latestPrice)
        latestRiskSnapshot = try? container.decodeIfPresent(TickerRiskSnapshot.self, forKey: .latestRiskSnapshot)
        currentScore = try? container.decodeIfPresent(RiskScore.self, forKey: .currentScore)
        currentAnalysis = try? container.decodeIfPresent(PositionAnalysis.self, forKey: .currentAnalysis)
        methodology = try container.decodeIfPresent(String.self, forKey: .methodology)
        dimensionBreakdown = try? container.decodeIfPresent([String: String].self, forKey: .dimensionBreakdown)
        latestEventAnalyses = (try? container.decode([EventAnalysis].self, forKey: .latestEventAnalyses)) ?? []
        recentNews = (try? container.decode([NewsItem].self, forKey: .recentNews)) ?? []
        recentAlerts = (try? container.decode([Alert].self, forKey: .recentAlerts)) ?? []
        freshness = try container.decode(TickerFreshness.self, forKey: .freshness)
        userContext = try container.decode(TickerUserContext.self, forKey: .userContext)
    }
}

struct TickerProfile: Codable {
    let ticker: String
    let companyName: String?
    let exchange: String?
    let sector: String?
    let industry: String?
    let peRatio: Double?
    let week52High: Double?
    let week52Low: Double?
    let marketCap: Double?

    enum CodingKeys: String, CodingKey {
        case ticker
        case companyName = "company_name"
        case exchange
        case sector
        case industry
        case peRatio = "pe_ratio"
        case week52High = "week_52_high"
        case week52Low = "week_52_low"
        case marketCap = "market_cap"
    }
}

struct TickerLatestPrice: Codable {
    let price: Double?
    let priceAsOf: Date?
    let previousClose: Double?
    let openPrice: Double?
    let dayHigh: Double?
    let dayLow: Double?
    let week52High: Double?
    let week52Low: Double?
    let avgVolume: Double?
    let source: String?

    enum CodingKeys: String, CodingKey {
        case price
        case priceAsOf = "price_as_of"
        case previousClose = "previous_close"
        case openPrice = "open_price"
        case dayHigh = "day_high"
        case dayLow = "day_low"
        case week52High = "week_52_high"
        case week52Low = "week_52_low"
        case avgVolume = "avg_volume"
        case source
    }
}

struct TickerRiskSnapshot: Codable {
    let id: String
    let ticker: String
    let grade: String?
    let safetyScore: Double?
    let structuralBaseScore: Double?
    let confidence: Double?
    let factorBreakdown: FactorBreakdown?
    let reasoning: String?
    let newsSummary: String?
    let analysisAsOf: Date

    enum CodingKeys: String, CodingKey {
        case id
        case ticker
        case grade
        case safetyScore = "safety_score"
        case structuralBaseScore = "structural_base_score"
        case confidence
        case factorBreakdown = "factor_breakdown"
        case reasoning
        case newsSummary = "news_summary"
        case analysisAsOf = "analysis_as_of"
    }
}

struct TickerFreshness: Codable {
    let priceAsOf: Date?
    let analysisAsOf: Date?

    enum CodingKeys: String, CodingKey {
        case priceAsOf = "price_as_of"
        case analysisAsOf = "analysis_as_of"
    }
}

struct TickerUserContext: Codable {
    let isHeld: Bool
    let holdingIds: [String]
    let isInWatchlist: Bool

    enum CodingKeys: String, CodingKey {
        case isHeld = "is_held"
        case holdingIds = "holding_ids"
        case isInWatchlist = "is_in_watchlist"
    }
}

struct WatchlistsResponse: Codable {
    let watchlists: [Watchlist]
    let message: String?
}

struct Watchlist: Identifiable, Codable {
    let id: String
    let userId: String
    let name: String
    let isDefault: Bool
    let items: [WatchlistItem]

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case name
        case isDefault = "is_default"
        case items
    }
}

struct WatchlistItem: Identifiable, Codable {
    let id: String
    let ticker: String
    let companyName: String?
    let price: Double?
    let priceAsOf: Date?
    let grade: String?
    let safetyScore: Double?
    let analysisAsOf: Date?
    let summary: String?

    enum CodingKeys: String, CodingKey {
        case id
        case ticker
        case companyName = "company_name"
        case price
        case priceAsOf = "price_as_of"
        case grade
        case safetyScore = "safety_score"
        case analysisAsOf = "analysis_as_of"
        case summary
    }
}

struct TickerRefreshResponse: Codable {
    let jobId: String?
    let ticker: String
    let status: String
    let startedAt: Date?
    let completedAt: Date?
    let errorMessage: String?

    enum CodingKeys: String, CodingKey {
        case jobId = "job_id"
        case ticker
        case status
        case startedAt = "started_at"
        case completedAt = "completed_at"
        case errorMessage = "error_message"
    }
}

struct TickerRefreshStatusResponse: Codable {
    let ticker: String
    let status: String
    let startedAt: Date?
    let completedAt: Date?
    let errorMessage: String?

    enum CodingKeys: String, CodingKey {
        case ticker
        case status
        case startedAt = "started_at"
        case completedAt = "completed_at"
        case errorMessage = "error_message"
    }
}
