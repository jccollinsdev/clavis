# In-App / Website Legal Copy — Snippets for V1

**Created:** 2026-06-01
**Status:** DRAFT — NEEDS PARENT/LAWYER REVIEW
**All snippets use placeholders — no real names included.**

---

## 1. In-App Settings → Legal Footer

**Location:** `SettingsView.swift` — Support & Legal section

**Proposed addition** above the existing Terms/Privacy/Methodology links:

```
Clavix is operated by Andover Digital LLC.
The iOS app is distributed on the App Store by an authorized individual developer account.
```

Or for a compact label row:

```
SettingsValueRow("Operator", value: "Andover Digital LLC")
SettingsValueRow("App Store Distributor", value: "[Individual Developer Account]")
```

---

## 2. Privacy Policy Page Intro

**Suggested addition at the top of the Privacy Policy page:**

> Clavix is operated by Andover Digital LLC. The Clavix iOS app is distributed on the Apple App Store through an Individual Apple Developer account held by [Individual Apple Developer Account Holder], who acts as the App Store distributor/seller for Apple distribution purposes. [Individual Apple Developer Account Holder] does not receive or access user personal data through their role as App Store distributor. Andover Digital LLC is responsible for operating the Clavix service, handling personal information, providing support, and managing the product experience.

---

## 3. Terms of Service Page Intro

**Suggested addition at the top of the Terms page:**

> These Terms are between you and Andover Digital LLC, the operator of Clavix. The Clavix iOS app is distributed on the Apple App Store by [Individual Apple Developer Account Holder], who acts as the App Store seller for Apple distribution purposes. Andover Digital LLC is solely responsible for the Clavix service, support, and the terms governing your use of the app.

---

## 4. App Store "Privacy Policy" Support Page Note

**If Apple requests a note in the App Store review about the operator vs seller structure:**

> Clavix is operated by Andover Digital LLC. The iOS app is distributed on the Apple App Store through an individual Apple Developer account. The App Store seller name may display the individual account holder's name for Apple distribution purposes. Andover Digital LLC is the service operator and data controller.

---

## 5. TestFlight-Only Notice (if needed)

> This is a pre-release version of Clavix for testing purposes. Clavix is operated by Andover Digital LLC. The iOS app is distributed through an individual Apple Developer account. By using this TestFlight build, you agree that this is pre-release software and may contain bugs or incomplete features.

---

## 6. Public Launch Note (if Individual structure remains)

For the website footer or an in-app "About" screen:

> Clavix is operated by Andover Digital LLC. The Clavix iOS app is distributed on the Apple App Store through an authorized individual developer account holder for Apple distribution purposes. See our Privacy Policy and Terms of Service for details.

---

## 7. Suggested "About" Section for iOS Settings

**New section in Settings (before Support & Legal):**

```
Section: ABOUT
Row: "Service Operator" → "Andover Digital LLC"
Row: "App Store Distribution" → "Individual Developer Account"
Row: "Support" → "support@getclavix.com"
```

---

## 8. Website Footer Update

**Current footer:** `© 2026 Clavix. All rights reserved.`

**Proposed revision:**

> © 2026 Andover Digital LLC. Clavix is a product of Andover Digital LLC.
> The Clavix iOS app is distributed on the Apple App Store by [Individual Apple Developer Account Holder].
>
> [Privacy] [Terms] [Refund] [Methodology] [Contact]

---

## 9. Onboarding / Login Screen Disclosure

**Current** (`LoginView.swift`):
> "Clavix is informational only. Risk grades and scores reflect risk signals derived from public data and model outputs. They are not recommendations to buy, sell, or hold any security."

This is good and should stay. Consider adding a brief operator line on the same screen:

> "Clavix is operated by Andover Digital LLC."

---

## 10. Template for All Legal Pages When Organization Account Is Created

Once the Apple Developer account transitions to an Organization account under Andover Digital LLC, simplify all references:

> Clavix is operated and distributed by Andover Digital LLC.

All individual account disclosure language can be removed at that point.

---

## Placeholder Key

| Placeholder | Meaning |
|---|---|
| `[Individual Apple Developer Account Holder]` | The real name of the person holding the Apple Developer account. DO NOT fill in automatically. Must be approved by the individual. |
| `[Individual Developer Account]` | Same as above, abbreviated context |
| `[Distributor]` | The individual Apple account holder in distribution context |
