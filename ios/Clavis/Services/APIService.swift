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

// MARK: - In-memory response cache

/// Lightweight TTL cache for read-only GET responses.
///
/// Cached paths (2-minute TTL): ticker detail, prices, score history, methodology,
/// search results, ticker list — data that doesn't change second-to-second and
/// makes back-navigation and tab-switching feel instant.
///
/// Not cached: /today, /alerts, /positions, /watchlist, /preferences, /digests —
/// these must always reflect the latest server state.
private actor APIResponseCache {
    struct Entry {
        let data: Data
        let cachedAt: Date
    }

    private var store: [String: Entry] = [:]
    private let ttl: TimeInterval

    init(ttl: TimeInterval = 120) { // 2-minute default
        self.ttl = ttl
    }

    func get(_ key: String) -> Data? {
        guard let entry = store[key] else { return nil }
        guard Date().timeIntervalSince(entry.cachedAt) < ttl else {
            store.removeValue(forKey: key)
            return nil
        }
        return entry.data
    }

    func set(_ key: String, data: Data) {
        store[key] = Entry(data: data, cachedAt: Date())
    }

    func invalidate(prefix: String) {
        store = store.filter { !$0.key.hasPrefix(prefix) }
    }

    func invalidateAll() {
        store.removeAll()
    }
}

class APIService {
    static let shared = APIService()

    private let baseURL: String
    private let decoder: JSONDecoder
    private let sessionLock = NSLock()
    private var session: URLSession

    // Paths whose responses are safe to cache for 2 minutes.
    // Freshness-critical paths (/today, /alerts, /positions, etc.) are NOT cached.
    private static let cacheablePrefixes: [String] = [
        "/tickers/",      // ticker detail, methodology, score-history, prices
        "/search",        // search results
        "/tickers",       // ticker list
    ]
    private static let cacheExclusions: [String] = [
        "/today", "/alerts", "/positions", "/watchlist", "/preferences",
        "/digests", "/analysis", "/brokerage",
    ]
    private let responseCache = APIResponseCache()

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
        self.session = APIService.makeSession()
    }

    private static func makeSession() -> URLSession {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 90
        // URLCache disabled at OS level — we manage our own in-memory cache above,
        // which has explicit TTLs and is invalidated on writes/mutations.
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.urlCache = nil
        // HTTP/2 multiplexing — reuse the same TCP connection for concurrent
        // requests to the same host (ticker detail + prices + methodology).
        configuration.httpMaximumConnectionsPerHost = 6
        configuration.waitsForConnectivity = false
        return URLSession(configuration: configuration)
    }

    private func activeSession() -> URLSession {
        sessionLock.lock()
        defer { sessionLock.unlock() }
        return session
    }

    private func rebuildSession() {
        sessionLock.lock()
        let previous = session
        session = APIService.makeSession()
        sessionLock.unlock()
        previous.invalidateAndCancel()
    }

    private func isCacheable(path: String) -> Bool {
        guard APIService.cacheablePrefixes.contains(where: { path.hasPrefix($0) }) else { return false }
        return !APIService.cacheExclusions.contains(where: { path.hasPrefix($0) })
    }

    private func makeRequest(
        path: String,
        method: String = "GET",
        body: Data? = nil,
        timeoutInterval: TimeInterval = 30,
        suppressSessionExpired: Bool = false
    ) async throws -> Data {
        // Serve cached response for read-only GET requests on cacheable paths.
        if method == "GET", body == nil, isCacheable(path: path) {
            if let cached = await responseCache.get(path) {
                return cached
            }
            let data = try await _makeRequest(
                path: path, method: method, body: body,
                timeoutInterval: timeoutInterval,
                suppressSessionExpired: suppressSessionExpired
            )
            await responseCache.set(path, data: data)
            return data
        }
        // Non-cacheable (mutations, freshness-critical): direct request.
        // On any write (POST/PATCH/DELETE), also invalidate the relevant ticker cache.
        let data = try await _makeRequest(
            path: path, method: method, body: body,
            timeoutInterval: timeoutInterval,
            suppressSessionExpired: suppressSessionExpired
        )
        if method != "GET" {
            // Invalidate ticker-specific cache on any write so next read is fresh.
            let prefix = path.components(separatedBy: "?").first ?? path
            await responseCache.invalidate(prefix: prefix)
        }
        return data
    }

    private func _makeRequest(
        path: String,
        method: String = "GET",
        body: Data? = nil,
        timeoutInterval: TimeInterval = 30,
        isRetry: Bool = false,
        suppressSessionExpired: Bool = false,
        didResetTransport: Bool = false
    ) async throws -> Data {
        guard let url = URL(string: "\(baseURL)\(path)") else {
            print("API request invalid URL base=\(baseURL) path=\(path)")
            throw APIError.invalidURL
        }

        if !isRetry {
            print("API request \(method) \(url.absoluteString)")
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        request.setValue("no-cache", forHTTPHeaderField: "Pragma")

        if let token = await SupabaseAuthService.shared.getAccessToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        } else {
            print("[API] No token available for \(method) \(path) — request will 401")
        }

        if let body = body {
            request.httpBody = body
        }

        do {
            request.timeoutInterval = timeoutInterval
            let (data, response) = try await activeSession().data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.invalidResponse
            }

            switch httpResponse.statusCode {
            case 200...299:
                return data
            case 401:
                // On the first 401, force-refresh the Supabase session and retry
                // once with the new token. This covers the common case of an
                // expired access token that wasn't caught before the request fired.
                if !isRetry {
                    print("[API] 401 on \(method) \(path) — refreshing session and retrying once")
                    try? await SupabaseAuthService.shared.refreshSession()
                    return try await _makeRequest(
                        path: path, method: method, body: body,
                        timeoutInterval: timeoutInterval, isRetry: true,
                        suppressSessionExpired: suppressSessionExpired,
                        didResetTransport: didResetTransport
                    )
                }
                // Second 401 after refresh — session is truly invalid.
                // Only signal session-expired for requests that opt in; the
                // preferences check right after login must not sign the user out
                // when the backend has a transient validation failure.
                if suppressSessionExpired {
                    print("[API] 401 persists after refresh on \(path) — suppressing sign-out (non-critical path)")
                } else {
                    print("[API] 401 persists after refresh — session expired, posting clavixSessionExpired")
                    await MainActor.run {
                        NotificationCenter.default.post(name: .clavixSessionExpired, object: nil)
                    }
                }
                throw APIError.unauthorized
            default:
                throw APIError.serverError(httpResponse.statusCode)
            }
        } catch let error as APIError {
            print("API request failed \(method) \(url.absoluteString): \(error)")
            throw error
        } catch let error as URLError where error.code == .cancelled {
            throw CancellationError()
        } catch let error as URLError where shouldRetryTransportError(error, method: method, didResetTransport: didResetTransport) {
            print("[API] transport issue on \(method) \(path) — rebuilding session and retrying once: \(error)")
            rebuildSession()
            return try await _makeRequest(
                path: path,
                method: method,
                body: body,
                timeoutInterval: timeoutInterval,
                isRetry: isRetry,
                suppressSessionExpired: suppressSessionExpired,
                didResetTransport: true
            )
        } catch {
            print("API request failed \(method) \(url.absoluteString): \(error)")
            throw APIError.networkError(url.absoluteString, error)
        }
    }

    private func shouldRetryTransportError(_ error: URLError, method: String, didResetTransport: Bool) -> Bool {
        guard !didResetTransport, method == "GET" else { return false }
        switch error.code {
        case .timedOut, .networkConnectionLost, .cannotFindHost, .cannotConnectToHost, .dnsLookupFailed:
            return true
        default:
            return false
        }
    }

    struct CreateHoldingRequest: Encodable {
        let ticker: String
        let shares: Double
        let purchase_price: Double
        let allow_outside_universe: Bool?
    }

    struct HoldingWorkflowResponse: Codable {
        let holdingId: String
        let ticker: String
        let analysisState: String
        let analysisRunId: String?
        let latestRefreshJob: TickerRefreshJob?
        let coverageState: String?
        let coverageNote: String?
        let analysisAsOf: Date?
        let scoreSource: String?
        let scoreAsOf: Date?
        let scoreVersion: String?
        let lastNewsRefreshAt: Date?
        let newsRefreshStatus: String?
        let newsAsOf: Date?
        let priceAsOf: Date?
        let position: Position?
        let source: String?

        enum CodingKeys: String, CodingKey {
            case holdingId = "holding_id"
            case ticker
            case analysisState = "analysis_state"
            case analysisRunId = "analysis_run_id"
            case latestRefreshJob = "latest_refresh_job"
            case coverageState = "coverage_state"
            case coverageNote = "coverage_note"
            case analysisAsOf = "analysis_as_of"
            case scoreSource = "score_source"
            case scoreAsOf = "score_as_of"
            case scoreVersion = "score_version"
            case lastNewsRefreshAt = "last_news_refresh_at"
            case newsRefreshStatus = "news_refresh_status"
            case newsAsOf = "news_as_of"
            case priceAsOf = "price_as_of"
            case position
            case source
        }
    }

    // MARK: - Holdings

    func fetchHoldings(timeoutInterval: TimeInterval = 15) async throws -> [Position] {
        let data = try await makeRequest(path: "/holdings", timeoutInterval: timeoutInterval)
        return try decoder.decode([Position].self, from: data)
    }

    func fetchDashboard() async throws -> DashboardResponse {
        let data = try await makeRequest(path: "/dashboard")
        return try decoder.decode(DashboardResponse.self, from: data)
    }

    func createHolding(
        ticker: String,
        shares: Double,
        purchasePrice: Double,
        allowOutsideUniverse: Bool? = nil
    ) async throws -> HoldingWorkflowResponse {
        let req = CreateHoldingRequest(
            ticker: ticker,
            shares: shares,
            purchase_price: purchasePrice,
            allow_outside_universe: allowOutsideUniverse
        )
        let body = try JSONEncoder().encode(req)
        let data = try await makeRequest(path: "/holdings", method: "POST", body: body)
        return try decoder.decode(HoldingWorkflowResponse.self, from: data)
    }

    // MARK: - Tickers

    func searchTickers(query: String, limit: Int = 20, timeoutInterval: TimeInterval = 12) async throws -> [TickerSearchResult] {
        let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        let data = try await makeRequest(path: "/tickers/search?q=\(encoded)&limit=\(limit)", timeoutInterval: timeoutInterval)
        let response = try decoder.decode(TickerSearchResponse.self, from: data)
        return response.results
    }

    func fetchTickerDetail(
        ticker: String,
        positionId: String? = nil,
        timeoutInterval: TimeInterval = 15
    ) async throws -> TickerDetailResponse {
        let query = positionId.flatMap { id -> String? in
            let encoded = id.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? id
            return "?position_id=\(encoded)"
        } ?? ""
        let data = try await makeRequest(path: "/tickers/\(ticker)\(query)", timeoutInterval: timeoutInterval)
        return try decoder.decode(TickerDetailResponse.self, from: data)
    }

    func fetchTickerMethodology(ticker: String, timeoutInterval: TimeInterval = 15) async throws -> MethodologyResponse {
        let data = try await makeRequest(path: "/tickers/\(ticker)/methodology", timeoutInterval: timeoutInterval)
        return try decoder.decode(MethodologyResponse.self, from: data)
    }

    func refreshTicker(ticker: String) async throws -> TickerRefreshResponse {
        let data = try await makeRequest(path: "/tickers/\(ticker)/refresh", method: "POST", body: Data())
        return try decoder.decode(TickerRefreshResponse.self, from: data)
    }

    func fetchTickerRefreshStatus(ticker: String) async throws -> TickerRefreshStatusResponse {
        let data = try await makeRequest(path: "/tickers/\(ticker)/refresh-status")
        return try decoder.decode(TickerRefreshStatusResponse.self, from: data)
    }

    func fetchSchedulerStatus() async throws -> SchedulerStatusResponse {
        let data = try await makeRequest(path: "/scheduler/status")
        return try decoder.decode(SchedulerStatusResponse.self, from: data)
    }

    // MARK: - Watchlists

    struct WatchlistItemCreate: Encodable {
        let ticker: String
    }

    func fetchWatchlists(timeoutInterval: TimeInterval = 12) async throws -> [Watchlist] {
        let data = try await makeRequest(path: "/watchlists", timeoutInterval: timeoutInterval)
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

    func fetchDigestStatus(timeoutInterval: TimeInterval = 15) async throws -> DigestStatusResponse {
        let data = try await makeRequest(path: "/digest/status", timeoutInterval: timeoutInterval)
        return try decoder.decode(DigestStatusResponse.self, from: data)
    }

    // MARK: - Positions

    func fetchPositionDetail(id: String) async throws -> PositionDetailResponse {
        let data = try await makeRequest(path: "/positions/\(id)")
        return try decoder.decode(PositionDetailResponse.self, from: data)
    }

    // MARK: - Alerts

    struct AlertsResponse: Codable {
        let alerts: [Alert]
    }

    func fetchAlerts(timeoutInterval: TimeInterval = 12) async throws -> [Alert] {
        let data = try await makeRequest(path: "/alerts", timeoutInterval: timeoutInterval)
        let response = try decoder.decode(AlertsResponse.self, from: data)
        return response.alerts
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

    func fetchLatestAnalysisRun(timeoutInterval: TimeInterval = 12) async throws -> AnalysisRun? {
        let data = try await makeRequest(path: "/analysis-runs/latest", timeoutInterval: timeoutInterval)
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

    func fetchPreferences(timeoutInterval: TimeInterval = 10) async throws -> PreferencesResponse {
        let data = try await makeRequest(path: "/preferences", timeoutInterval: timeoutInterval, suppressSessionExpired: true)
        return try decoder.decode(PreferencesResponse.self, from: data)
    }

    func fetchBrokerageStatus(timeoutInterval: TimeInterval = 12) async throws -> BrokerageStatusResponse {
        let data = try await makeRequest(path: "/brokerage/status", timeoutInterval: timeoutInterval)
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
        print("[API] POST /preferences/acknowledge — sending request")
        do {
            let data = try await makeRequest(path: "/preferences/acknowledge", method: "POST")
            print("[API] POST /preferences/acknowledge — response: \(String(data: data, encoding: .utf8) ?? "<non-utf8>")")
        } catch let error as APIError {
            print("[API] POST /preferences/acknowledge — APIError: \(error)")
            throw error
        } catch {
            print("[API] POST /preferences/acknowledge — error: \(error)")
            throw error
        }
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

    // MARK: - Score History

    func fetchScoreHistory(ticker: String, days: Int = 90) async throws -> ScoreHistoryResponse {
        let data = try await makeRequest(path: "/tickers/\(ticker)/score-history?days=\(days)", timeoutInterval: 30)
        return try decoder.decode(ScoreHistoryResponse.self, from: data)
    }

    // MARK: - Alerts (v2)

    func markAlertRead(id: String) async throws {
        _ = try await makeRequest(path: "/alerts/\(id)/read", method: "POST")
    }

    func markAllAlertsRead() async throws {
        _ = try await makeRequest(path: "/alerts/read-all", method: "POST")
    }

    // MARK: - Today envelope

    func fetchToday(timeoutInterval: TimeInterval = 18) async throws -> TodayResponse {
        let data = try await makeRequest(path: "/today", timeoutInterval: timeoutInterval)
        return try decoder.decode(TodayResponse.self, from: data)
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
    let dimensionBreakdown: DimensionBreakdown?
    let latestEventAnalyses: [EventAnalysis]
    let recentNews: [NewsItem]
    let recentAlerts: [Alert]

    enum CodingKeys: String, CodingKey {
        case position
        case currentScore = "current_score"
        case currentAnalysis = "current_analysis"
        case methodology
        case dimensionBreakdown = "dimension_breakdown"
        case latestEventAnalyses = "latest_event_analyses"
        case recentNews = "recent_news"
        case recentAlerts = "recent_alerts"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        position = try container.decode(Position.self, forKey: .position)
        currentScore = try? container.decodeIfPresent(RiskScore.self, forKey: .currentScore)
        currentAnalysis = try? container.decodeIfPresent(PositionAnalysis.self, forKey: .currentAnalysis)
        methodology = try container.decodeIfPresent(String.self, forKey: .methodology)
        dimensionBreakdown = try? container.decodeIfPresent(DimensionBreakdown.self, forKey: .dimensionBreakdown)
        latestEventAnalyses = (try? container.decode([EventAnalysis].self, forKey: .latestEventAnalyses)) ?? []
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
    let sharedAnalysis: SharedTickerAnalysisSummary?
    let portfolioOverlay: PortfolioOverlay?

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
        case sharedAnalysis = "shared_analysis"
        case portfolioOverlay = "portfolio_overlay"
    }

    var resolvedGrade: String? {
        sharedAnalysis?.currentGrade ?? grade
    }

    var resolvedSafetyScore: Double? {
        sharedAnalysis?.currentScore ?? safetyScore
    }

    var resolvedSummary: String? {
        sharedAnalysis?.gradeRationale ?? summary
    }

    var resolvedAnalysisAsOf: Date? {
        sharedAnalysis?.freshness.analysisAsOf ?? analysisAsOf
    }

    var resolvedCompanyName: String? {
        sharedAnalysis?.companyName ?? companyName
    }
}

struct TickerDetailResponse: Codable {
    let ticker: String
    let profile: TickerProfile
    let position: Position
    let latestPrice: TickerLatestPrice
    let source: String?
    let analysisState: TickerAnalysisState?
    let latestAnalysisRun: AnalysisRun?
    let latestRefreshJob: TickerRefreshJob?
    let coverageState: String?
    let latestRiskSnapshot: TickerRiskSnapshot?
    let currentScore: RiskScore?
    let currentAnalysis: PositionAnalysis?
    let methodology: String?
    let dimensionBreakdown: DimensionBreakdown?
    let latestEventAnalyses: [EventAnalysis]
    let recentNews: [MethodologyArticle]
    let recentAlerts: [Alert]
    let freshness: TickerFreshness
    let userContext: TickerUserContext
    let sharedAnalysis: SharedTickerAnalysisDetail?
    let portfolioOverlay: PortfolioOverlay?

    enum CodingKeys: String, CodingKey {
        case ticker
        case profile
        case position
        case latestPrice = "latest_price"
        case source
        case analysisState = "analysis_state"
        case latestAnalysisRun = "latest_analysis_run"
        case latestRefreshJob = "latest_refresh_job"
        case coverageState = "coverage_state"
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
        case sharedAnalysis = "shared_analysis"
        case portfolioOverlay = "portfolio_overlay"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        ticker = try container.decode(String.self, forKey: .ticker)
        profile = try container.decode(TickerProfile.self, forKey: .profile)
        position = try container.decode(Position.self, forKey: .position)
        latestPrice = try container.decode(TickerLatestPrice.self, forKey: .latestPrice)
        source = try container.decodeIfPresent(String.self, forKey: .source)
        analysisState = try? container.decodeIfPresent(TickerAnalysisState.self, forKey: .analysisState)
        latestAnalysisRun = try? container.decodeIfPresent(AnalysisRun.self, forKey: .latestAnalysisRun)
        latestRefreshJob = try? container.decodeIfPresent(TickerRefreshJob.self, forKey: .latestRefreshJob)
        coverageState = try container.decodeIfPresent(String.self, forKey: .coverageState)
        latestRiskSnapshot = try? container.decodeIfPresent(TickerRiskSnapshot.self, forKey: .latestRiskSnapshot)
        currentScore = try? container.decodeIfPresent(RiskScore.self, forKey: .currentScore)
        currentAnalysis = try? container.decodeIfPresent(PositionAnalysis.self, forKey: .currentAnalysis)
        methodology = try container.decodeIfPresent(String.self, forKey: .methodology)
        dimensionBreakdown = try? container.decodeIfPresent(DimensionBreakdown.self, forKey: .dimensionBreakdown)
        latestEventAnalyses = (try? container.decode([EventAnalysis].self, forKey: .latestEventAnalyses)) ?? []
        recentNews = (try? container.decode([MethodologyArticle].self, forKey: .recentNews)) ?? []
        recentAlerts = (try? container.decode([Alert].self, forKey: .recentAlerts)) ?? []
        freshness = try container.decode(TickerFreshness.self, forKey: .freshness)
        userContext = try container.decode(TickerUserContext.self, forKey: .userContext)
        sharedAnalysis = try? container.decodeIfPresent(SharedTickerAnalysisDetail.self, forKey: .sharedAnalysis)
        portfolioOverlay = try? container.decodeIfPresent(PortfolioOverlay.self, forKey: .portfolioOverlay)
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
    let id: String?
    let ticker: String
    let grade: String?
    let safetyScore: Double?
    let structuralBaseScore: Double?
    let confidence: Double?
    let factorBreakdown: FactorBreakdown?
    let reasoning: String?
    let newsSummary: String?
    let analysisAsOf: Date?

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
    let lastNewsRefreshAt: Date?
    let newsRefreshStatus: String?
    let newsAsOf: Date?

    enum CodingKeys: String, CodingKey {
        case priceAsOf = "price_as_of"
        case analysisAsOf = "analysis_as_of"
        case lastNewsRefreshAt = "last_news_refresh_at"
        case newsRefreshStatus = "news_refresh_status"
        case newsAsOf = "news_as_of"
    }
}

struct TickerAnalysisState: Codable {
    let status: String
    let source: String?
    let coverageState: String?
    let latestAnalysisRunId: String?
    let latestAnalysisStatus: String?
    let latestRefreshJobId: String?
    let latestRefreshStatus: String?
    let newsRefreshStatus: String?
    let lastSuccessAt: Date?
    let lastFailureAt: Date?
    let analysisAsOf: Date?
    let scoreSource: String?
    let scoreAsOf: Date?
    let scoreVersion: String?
    let lastNewsRefreshAt: Date?
    let priceAsOf: Date?
    let newsAsOf: Date?

    enum CodingKeys: String, CodingKey {
        case status
        case source
        case coverageState = "coverage_state"
        case latestAnalysisRunId = "latest_analysis_run_id"
        case latestAnalysisStatus = "latest_analysis_status"
        case latestRefreshJobId = "latest_refresh_job_id"
        case latestRefreshStatus = "latest_refresh_status"
        case newsRefreshStatus = "news_refresh_status"
        case lastSuccessAt = "last_success_at"
        case lastFailureAt = "last_failure_at"
        case analysisAsOf = "analysis_as_of"
        case scoreSource = "score_source"
        case scoreAsOf = "score_as_of"
        case scoreVersion = "score_version"
        case lastNewsRefreshAt = "last_news_refresh_at"
        case priceAsOf = "price_as_of"
        case newsAsOf = "news_as_of"
    }
}

struct TickerRefreshJob: Codable {
    let id: String?
    let ticker: String?
    let jobType: String?
    let status: String?
    let startedAt: Date?
    let completedAt: Date?
    let errorMessage: String?

    enum CodingKeys: String, CodingKey {
        case id
        case ticker
        case jobType = "job_type"
        case status
        case startedAt = "started_at"
        case completedAt = "completed_at"
        case errorMessage = "error_message"
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
    let sharedAnalysis: SharedTickerAnalysisSummary?
    let portfolioOverlay: PortfolioOverlay?
    let latestEventAnalyses: [EventAnalysis]?

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
        case sharedAnalysis = "shared_analysis"
        case portfolioOverlay = "portfolio_overlay"
        case latestEventAnalyses = "latest_event_analyses"
    }

    var resolvedGrade: String? {
        sharedAnalysis?.currentGrade ?? grade
    }

    var resolvedSafetyScore: Double? {
        sharedAnalysis?.currentScore ?? safetyScore
    }

    var resolvedSummary: String? {
        sharedAnalysis?.gradeRationale ?? summary
    }

    var resolvedAnalysisAsOf: Date? {
        sharedAnalysis?.freshness.analysisAsOf ?? analysisAsOf
    }

    var resolvedCompanyName: String? {
        sharedAnalysis?.companyName ?? companyName
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

struct SchedulerStatusResponse: Codable {
    let userId: String
    let digestTime: String
    let notificationsEnabled: Bool
    let runtimeJobPresent: Bool
    let runtimeNextRunAt: Date?
    let lastSuccessAt: Date?
    let lastFailureAt: Date?
    let lastRunStatus: String?

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case digestTime = "digest_time"
        case notificationsEnabled = "notifications_enabled"
        case runtimeJobPresent = "runtime_job_present"
        case runtimeNextRunAt = "runtime_next_run_at"
        case lastSuccessAt = "last_success_at"
        case lastFailureAt = "last_failure_at"
        case lastRunStatus = "last_run_status"
    }
}
