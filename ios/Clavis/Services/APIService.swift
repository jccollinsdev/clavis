import Foundation

enum Config {
    static let supabaseUrl = "https://uwvwulhkxtzabykelvam.supabase.co"
    static let supabaseAnonKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV3dnd1bGhreHR6YWJ5a2VsdmFtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUzMDU2NTQsImV4cCI6MjA5MDg4MTY1NH0.Dp38Ba7YH7icnaPlnnvcGNuwMBrDL4l_Lx0veKuQYwk"
    static let backendBaseUrl = "https://clavis.andoverdigital.com"
}

enum APIError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case unauthorized
    case serverError(Int)
    case decodingError(Error)
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Invalid URL"
        case .invalidResponse: return "Invalid response from server"
        case .unauthorized: return "Unauthorized - please log in again"
        case .serverError(let code): return "Server error: \(code)"
        case .decodingError(let error): return "Failed to decode response: \(error.localizedDescription)"
        case .networkError(let error): return "Network error: \(error.localizedDescription)"
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
        configuration.timeoutIntervalForResource = 20
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.urlCache = nil
        self.session = URLSession(configuration: configuration)
    }

    private func makeRequest(path: String, method: String = "GET", body: Data? = nil) async throws -> Data {
        guard let url = URL(string: "\(baseURL)\(path)") else {
            throw APIError.invalidURL
        }

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
            request.timeoutInterval = 12
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
            throw error
        } catch {
            throw APIError.networkError(error)
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

    func deleteHolding(id: String) async throws {
        _ = try await makeRequest(path: "/holdings/\(id)", method: "DELETE")
    }

    // MARK: - Digest

    func fetchTodayDigest() async throws -> DigestResponse {
        let data = try await makeRequest(path: "/digest")
        return try decoder.decode(DigestResponse.self, from: data)
    }

    func fetchDigestHistory(limit: Int = 7) async throws -> [Digest] {
        let data = try await makeRequest(path: "/digest/history?limit=\(limit)")
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

        enum CodingKeys: String, CodingKey {
            case digestTime = "digest_time"
            case notificationsEnabled = "notifications_enabled"
        }
    }

    func fetchPreferences() async throws -> PreferencesResponse {
        let data = try await makeRequest(path: "/preferences")
        return try decoder.decode(PreferencesResponse.self, from: data)
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
        let quiet_hours_enabled: Bool?
        let quiet_hours_start: String?
        let quiet_hours_end: String?
    }

    func updateAlertPreferences(
        gradeChanges: Bool,
        majorEvents: Bool,
        portfolioRisk: Bool,
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
            quiet_hours_enabled: quietHoursEnabled,
            quiet_hours_start: formatter.string(from: quietHoursStart),
            quiet_hours_end: formatter.string(from: quietHoursEnd)
        )
        let body = try JSONEncoder().encode(update)
        _ = try await makeRequest(path: "/preferences/alerts", method: "PATCH", body: body)
    }

    // MARK: - Prices

    func fetchPriceHistory(ticker: String, days: Int = 30) async throws -> PriceHistoryResponse {
        let data = try await makeRequest(path: "/prices/\(ticker)?days=\(days)")
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
