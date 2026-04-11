import Foundation

struct Alert: Identifiable, Codable {
    let id: String
    let userId: String
    let positionTicker: String?
    let type: AlertType
    let previousGrade: String?
    let newGrade: String?
    let message: String
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case positionTicker = "position_ticker"
        case type
        case previousGrade = "previous_grade"
        case newGrade = "new_grade"
        case message
        case createdAt = "created_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decodeIfPresent(String.self, forKey: .id) ?? UUID().uuidString
        userId = try container.decodeIfPresent(String.self, forKey: .userId) ?? ""
        positionTicker = try container.decodeIfPresent(String.self, forKey: .positionTicker)
        type = (try? container.decode(AlertType.self, forKey: .type)) ?? .digestReady
        previousGrade = try container.decodeIfPresent(String.self, forKey: .previousGrade)
        newGrade = try container.decodeIfPresent(String.self, forKey: .newGrade)
        message = try container.decodeIfPresent(String.self, forKey: .message) ?? ""
        createdAt = try container.decodeIfPresent(Date.self, forKey: .createdAt) ?? Date()
    }
}

enum AlertType: String, Codable {
    case gradeChange = "grade_change"
    case majorEvent = "major_event"
    case portfolioGradeChange = "portfolio_grade_change"
    case digestReady = "digest_ready"
    case safetyDeterioration = "safety_deterioration"
    case concentrationDanger = "concentration_danger"
    case clusterRisk = "cluster_risk"
    case macroShock = "macro_shock"
    case structuralFragility = "structural_fragility"
    case portfolioSafetyThresholdBreach = "portfolio_safety_threshold_breach"

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let rawValue = (try? container.decode(String.self)) ?? ""
        self = AlertType(rawValue: rawValue) ?? .digestReady
    }

    var displayName: String {
        switch self {
        case .gradeChange: return "Grade Change"
        case .majorEvent: return "Major Event"
        case .portfolioGradeChange: return "Portfolio Grade Change"
        case .digestReady: return "Digest Ready"
        case .safetyDeterioration: return "Safety Deterioration"
        case .concentrationDanger: return "Concentration Danger"
        case .clusterRisk: return "Cluster Risk"
        case .macroShock: return "Macro Shock"
        case .structuralFragility: return "Structural Fragility"
        case .portfolioSafetyThresholdBreach: return "Portfolio Safety Threshold"
        }
    }

    var iconName: String {
        switch self {
        case .gradeChange: return "arrow.up.arrow.down"
        case .majorEvent: return "exclamationmark.triangle"
        case .portfolioGradeChange: return "chart.pie"
        case .digestReady: return "doc.text"
        case .safetyDeterioration: return "chart.line.downtrend.xyaxis"
        case .concentrationDanger: return "chart.bar"
        case .clusterRisk: return "square.stack.3d.up"
        case .macroShock: return "globe"
        case .structuralFragility: return "building.columns"
        case .portfolioSafetyThresholdBreach: return "shield.slash"
        }
    }
}
