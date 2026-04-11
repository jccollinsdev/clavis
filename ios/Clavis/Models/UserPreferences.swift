import Foundation

struct UserPreferences: Codable {
    let id: String
    let userId: String
    let digestTime: String
    let notificationsEnabled: Bool
    let apnsToken: String?

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case digestTime = "digest_time"
        case notificationsEnabled = "notifications_enabled"
        case apnsToken = "apns_token"
    }
}
