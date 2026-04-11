import Foundation

extension KeyedDecodingContainer {
    func decodeFlexibleDouble(forKey key: Key) throws -> Double {
        if let value = try? decode(Double.self, forKey: key) {
            return value
        }
        if let stringValue = try? decode(String.self, forKey: key),
           let value = Double(stringValue) {
            return value
        }
        throw DecodingError.dataCorruptedError(forKey: key, in: self, debugDescription: "Expected Double or numeric String")
    }

    func decodeFlexibleDoubleIfPresent(forKey key: Key) throws -> Double? {
        if let value = try? decodeIfPresent(Double.self, forKey: key) {
            return value
        }
        if let stringValue = try? decodeIfPresent(String.self, forKey: key) {
            if let value = Double(stringValue) {
                return value
            }
            return nil
        }
        return nil
    }

    func decodeFlexibleIntIfPresent(forKey key: Key) throws -> Int? {
        if let value = try? decodeIfPresent(Int.self, forKey: key) {
            return value
        }
        if let stringValue = try? decodeIfPresent(String.self, forKey: key) {
            if let value = Int(stringValue) {
                return value
            }
            return nil
        }
        return nil
    }

    func decodeFlexibleStringArrayIfPresent(forKey key: Key) throws -> [String]? {
        if let values = try? decodeIfPresent([String].self, forKey: key) {
            let cleaned = values.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
            return cleaned.isEmpty ? nil : cleaned
        }

        if let raw = try? decodeIfPresent(String.self, forKey: key) {
            let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else { return nil }

            if let data = trimmed.data(using: .utf8),
               let values = try? JSONDecoder().decode([String].self, from: data) {
                let cleaned = values.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
                return cleaned.isEmpty ? nil : cleaned
            }

            return [trimmed]
        }

        return nil
    }
}

enum FlexibleDateDecoder {
    private static let iso8601Fractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let iso8601Basic: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static let postgresFractional: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss.SSSSSSXXXXX"
        return formatter
    }()

    private static let postgresBasic: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ssXXXXX"
        return formatter
    }()

    static func decode(_ string: String) -> Date? {
        if let date = iso8601Fractional.date(from: string) {
            return date
        }
        if let date = iso8601Basic.date(from: string) {
            return date
        }
        if let date = postgresFractional.date(from: string) {
            return date
        }
        if let date = postgresBasic.date(from: string) {
            return date
        }
        return nil
    }
}
