import Foundation

struct MethodologyResponse: Codable {
    let ticker: String
    let dimensions: MethodologyDimensions
    let composite: MethodologyComposite
}

struct MethodologyDimensions: Codable {
    let financialHealth: MethodologyFinancialHealth
    let newsSentiment: MethodologyNewsSentiment
    let macroExposure: MethodologyMacroExposure
    let sectorExposure: MethodologySectorExposure
    let volatility: MethodologyVolatility

    enum CodingKeys: String, CodingKey {
        case financialHealth = "financial_health"
        case newsSentiment = "news_sentiment"
        case macroExposure = "macro_exposure"
        case sectorExposure = "sector_exposure"
        case volatility
    }
}

protocol MethodologyDimensionProtocol {
    var score: Double? { get }
    var label: String { get }
}

struct MethodologyFinancialHealth: Codable, MethodologyDimensionProtocol {
    let score: Double?
    let debtToEquity: Double?
    let fcfMargin: Double?
    let interestCoverage: Double?
    let currentRatio: Double?
    let revenueGrowthTrend: String?
    let profitabilityTrend: String?
    let asOfDate: String?
    let dataSource: String?

    var label: String { "Financial Health" }

    enum CodingKeys: String, CodingKey {
        case score
        case debtToEquity = "debt_to_equity"
        case fcfMargin = "fcf_margin"
        case interestCoverage = "interest_coverage"
        case currentRatio = "current_ratio"
        case revenueGrowthTrend = "revenue_growth_trend"
        case profitabilityTrend = "profitability_trend"
        case asOfDate = "as_of_date"
        case dataSource = "data_source"
    }
}

struct MethodologyNewsSentiment: Codable, MethodologyDimensionProtocol {
    let score: Double?
    let articleCount7d: Int?
    let volumeSignal: Bool?
    let weightedScore: Double?
    let articles: [MethodologyArticle]

    var label: String { "News Sentiment" }

    enum CodingKeys: String, CodingKey {
        case score
        case articleCount7d = "article_count_7d"
        case volumeSignal = "volume_signal"
        case weightedScore = "weighted_score"
        case articles
    }
}

struct MethodologyMacroExposure: Codable, MethodologyDimensionProtocol {
    let score: Double?
    let rSquared: Double?
    let tradingDaysUsed: Int?
    let limitedData: Bool?
    let asOfDate: String?
    let coefficients: [String: Double]?
    let currentFactorLevels: [String: Double]?
    let narrative: String?

    var label: String { "Macro Exposure" }

    enum CodingKeys: String, CodingKey {
        case score
        case rSquared = "r_squared"
        case tradingDaysUsed = "trading_days_used"
        case limitedData = "limited_data"
        case asOfDate = "as_of_date"
        case coefficients
        case currentFactorLevels = "current_factor_levels"
        case narrative
    }
}

struct MethodologySectorExposure: Codable, MethodologyDimensionProtocol {
    let score: Double?
    let sector: String?
    let sectorEtf: String?
    let sectorBeta: Double?
    let sectorMomentum30d: Double?
    let sectorBreadth: Double?
    let narrative: String?

    var label: String { "Sector Exposure" }

    enum CodingKeys: String, CodingKey {
        case score
        case sector
        case sectorEtf = "sector_etf"
        case sectorBeta = "sector_beta"
        case sectorMomentum30d = "sector_momentum_30d"
        case sectorBreadth = "sector_breadth"
        case narrative
    }
}

struct MethodologyVolatility: Codable, MethodologyDimensionProtocol {
    let score: Double?
    let realizedVol30d: Double?
    let realizedVol90d: Double?
    let volRatio: Double?
    let maxDrawdown252d: Double?
    let betaToSpy: Double?
    let asOfDate: String?

    var label: String { "Volatility" }

    enum CodingKeys: String, CodingKey {
        case score
        case realizedVol30d = "realized_vol_30d"
        case realizedVol90d = "realized_vol_90d"
        case volRatio = "vol_ratio"
        case maxDrawdown252d = "max_drawdown_252d"
        case betaToSpy = "beta_to_spy"
        case asOfDate = "as_of_date"
    }
}

struct MethodologyArticle: Codable, Identifiable {
    let id: String
    let title: String?
    let source: String?
    let publishedAt: String?
    let sourceTier: Int?
    let recencyWeight: Double?
    let sentimentScore: Double?
    let sentimentReason: String?
    let impactTag: String?
    let tldr: String?
    let whatItMeans: String?
    let keyImplications: [String]?
    let sourceUrl: String?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case source
        case publishedAt = "published_at"
        case sourceTier = "source_tier"
        case recencyWeight = "recency_weight"
        case sentimentScore = "sentiment_score"
        case sentimentReason = "sentiment_reason"
        case impactTag = "impact_tag"
        case tldr
        case whatItMeans = "what_it_means"
        case keyImplications = "key_implications"
        case sourceUrl = "source_url"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decodeIfPresent(String.self, forKey: .id) ?? UUID().uuidString
        title = try container.decodeIfPresent(String.self, forKey: .title)
        source = try container.decodeIfPresent(String.self, forKey: .source)
        publishedAt = try container.decodeIfPresent(String.self, forKey: .publishedAt)
        sourceTier = try container.decodeIfPresent(Int.self, forKey: .sourceTier)
        recencyWeight = try container.decodeIfPresent(Double.self, forKey: .recencyWeight)
        sentimentScore = try container.decodeIfPresent(Double.self, forKey: .sentimentScore)
        sentimentReason = try container.decodeIfPresent(String.self, forKey: .sentimentReason)
        impactTag = try container.decodeIfPresent(String.self, forKey: .impactTag)
        tldr = try container.decodeIfPresent(String.self, forKey: .tldr)
        whatItMeans = try container.decodeIfPresent(String.self, forKey: .whatItMeans)
        keyImplications = try container.decodeIfPresent([String].self, forKey: .keyImplications)
        sourceUrl = try container.decodeIfPresent(String.self, forKey: .sourceUrl)
    }
}

struct MethodologyComposite: Codable {
    let grade: String?
    let score: Double?
    let methodologyVersion: String?

    enum CodingKeys: String, CodingKey {
        case grade
        case score
        case methodologyVersion = "methodology_version"
    }
}
