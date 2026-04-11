import Foundation
import UserNotifications
import UIKit

class PushNotificationManager: NSObject, UNUserNotificationCenterDelegate {
    static let shared = PushNotificationManager()

    private override init() {
        super.init()
        UNUserNotificationCenter.current().delegate = self
    }

    func requestPermission() async -> Bool {
        do {
            let granted = try await UNUserNotificationCenter.current().requestAuthorization(
                options: [.alert, .badge, .sound]
            )
            if granted {
                await MainActor.run {
                    registerForRemoteNotifications()
                }
            }
            return granted
        } catch {
            print("Push permission error: \(error)")
            return false
        }
    }

    func registerForRemoteNotifications() {
        DispatchQueue.main.async {
            UIApplication.shared.registerForRemoteNotifications()
        }
    }

    func getDeviceToken() -> String? {
        return UserDefaults.standard.string(forKey: "apns_device_token")
    }

    func saveDeviceToken(_ token: Data) {
        let tokenString = token.map { String(format: "%02.2hhx", $0) }.joined()
        UserDefaults.standard.set(tokenString, forKey: "apns_device_token")
        Task {
            await sendTokenToBackend(tokenString)
        }
    }

    private func sendTokenToBackend(_ token: String) async {
        do {
            try await APIService.shared.registerDeviceToken(token)
        } catch {
            print("Failed to register device token: \(error)")
        }
    }

    func handleRemoteNotificationRegistration(_ deviceToken: Data?, error: Error?) {
        if let error = error {
            print("Failed to register for remote notifications: \(error)")
            return
        }
        if let token = deviceToken {
            saveDeviceToken(token)
        }
    }

    func clearBadge() {
        UNUserNotificationCenter.current().setBadgeCount(0) { _ in }
    }

    func updateBadgeCount(_ count: Int) {
        UNUserNotificationCenter.current().setBadgeCount(count) { _ in }
    }

    // MARK: - UNUserNotificationCenterDelegate

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        completionHandler([.banner, .badge, .sound])
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        let userInfo = response.notification.request.content.userInfo

            if let type = userInfo["type"] as? String {
            switch type {
            case "digest":
                NotificationCenter.default.post(name: .openDigest, object: nil)
            case "grade_change":
                if let ticker = userInfo["ticker"] as? String {
                    NotificationCenter.default.post(name: .openPositionDetail, object: ticker)
                }
            case "major_event":
                if let ticker = userInfo["ticker"] as? String {
                    NotificationCenter.default.post(name: .openPositionDetail, object: ticker)
                }
            case "position_analysis":
                if let ticker = userInfo["ticker"] as? String {
                    NotificationCenter.default.post(
                        name: .positionAnalysisComplete,
                        object: ticker,
                        userInfo: userInfo
                    )
                }
            default:
                break
            }
        }

        clearBadge()
        completionHandler()
    }
}

extension Notification.Name {
    static let openDigest = Notification.Name("openDigest")
    static let openPositionDetail = Notification.Name("openPositionDetail")
    static let positionAnalysisComplete = Notification.Name("positionAnalysisComplete")
}
