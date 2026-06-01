import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var email = ""
    @State private var password = ""
    @State private var mode: AuthMode = .welcome
    @FocusState private var focusedField: Field?

    private enum AuthMode {
        case welcome
        case signIn
        case signUp
        case forgotPassword
    }

    enum Field: Hashable {
        case email
        case password
    }

    private var requiresPassword: Bool {
        switch mode {
        case .signIn, .signUp:
            return true
        case .welcome, .forgotPassword:
            return false
        }
    }

    private var isFormValid: Bool {
        let hasEmail = !email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        if requiresPassword {
            return hasEmail && !password.isEmpty
        }
        return hasEmail
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.clavixPage.ignoresSafeArea()

                switch mode {
                case .welcome:
                    welcomeSurface
                case .signIn, .signUp, .forgotPassword:
                    formSurface
                }
            }
            .ignoresSafeArea(.keyboard, edges: .bottom)
        }
    }

    private var welcomeSurface: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Spacer(minLength: 32)

                Text("Portfolio risk,\nmeasured.")
                    .font(ClavisTypography.clavixSerif(40, weight: .medium))
                    .tracking(-0.5)
                    .foregroundColor(.clavixInk)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.bottom, 14)

                Text("Every morning, Clavix scores your positions across five risk dimensions — macro, sector, financials, news, and volatility — and explains the reasoning.")
                    .font(ClavisTypography.inter(15, weight: .regular))
                    .foregroundColor(.clavixInk2)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.bottom, 28)

                ClavixCard {
                    VStack(alignment: .leading, spacing: 8) {
                        ClavixEyebrow("Morning Report")
                        Text("One briefing. Every grade audited.")
                            .font(ClavisTypography.clavixSerif(20, weight: .medium))
                            .foregroundColor(.clavixInk)
                        Text("Macro conditions, sector exposure, and position-level risk in a single daily view. The math behind each grade is always inspectable.")
                            .font(ClavisTypography.inter(14, weight: .regular))
                            .foregroundColor(.clavixInk2)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .padding(.bottom, 32)

                AuthActionButton(
                    title: "Create account",
                    fill: .clavixInk,
                    foreground: .clavixPaper
                ) {
                    mode = .signUp
                    focusedField = .email
                }
                .padding(.bottom, 10)

                AuthActionButton(
                    title: "Sign in",
                    fill: .clear,
                    foreground: .clavixInk,
                    bordered: true
                ) {
                    mode = .signIn
                    focusedField = .email
                }
                .padding(.bottom, 20)

                Text(ClavisCopy.riskAcknowledgment)
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk3)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .multilineTextAlignment(.center)
                    .padding(.bottom, 6)

                Text("Clavix is operated by Andover Digital LLC.")
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk4)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .multilineTextAlignment(.center)
                    .padding(.bottom, 8)

                termsFooter
                    .padding(.bottom, 16)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 32)
            .frame(maxWidth: 520)
            .frame(maxWidth: .infinity)
        }
        .safeAreaInset(edge: .top, spacing: 0) {
            ClavixStickyBar()
        }
    }

    private var formSurface: some View {
        ClavixScreen(
            eyebrow: formEyebrow,
            title: formTitle,
            trailing: AnyView(
                Button("Back") {
                    withAnimation(.easeInOut(duration: 0.15)) {
                        mode = .welcome
                    }
                }
                .font(ClavisTypography.clavixMono(10, weight: .semibold))
                .foregroundColor(.clavixAccent)
                .buttonStyle(.plain)
            )
        ) {
            if let statusCard {
                statusCard
            }

            ClavixCard {
                VStack(spacing: 12) {
                    AuthInputField(
                        title: "Email",
                        text: $email,
                        focusedField: $focusedField,
                        field: .email,
                        submitLabel: requiresPassword ? .next : .go
                    ) {
                        if requiresPassword {
                            focusedField = .password
                        } else {
                            submit()
                        }
                    }

                    if requiresPassword {
                        VStack(alignment: .trailing, spacing: 10) {
                            SecureField("Password", text: $password)
                                .font(ClavisTypography.inter(15, weight: .regular))
                                .foregroundColor(.clavixInk)
                                .textContentType(mode == .signUp ? .newPassword : .password)
                                .submitLabel(mode == .signUp ? .join : .go)
                                .focused($focusedField, equals: .password)
                                .onSubmit { submit() }
                                .padding(.horizontal, 12)
                                .frame(height: 48)
                                .background(Color.clavixPaper2)
                                .overlay(
                                    RoundedRectangle(cornerRadius: ClavixLayout.controlRadius)
                                        .stroke(Color.clavixRule, lineWidth: 1)
                                )
                                .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous))

                            if mode == .signIn {
                                Button("Forgot password?") {
                                    withAnimation(.easeInOut(duration: 0.15)) {
                                        mode = .forgotPassword
                                        focusedField = .email
                                    }
                                }
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixAccent)
                                .buttonStyle(.plain)
                            }
                        }
                    }

                    AuthActionButton(
                        title: submitTitle,
                        fill: .clavixInk,
                        foreground: .clavixPaper,
                        isLoading: authViewModel.isLoading,
                        isEnabled: isFormValid
                    ) {
                        submit()
                    }
                }
            }

            if let caption = formCaption {
                Text(caption)
                    .font(ClavisTypography.clavixCaption)
                    .foregroundColor(.clavixInk3)
            }

            secondaryActions
            termsFooter
        }
        .scrollDismissesKeyboard(.interactively)
    }

    @ViewBuilder
    private var secondaryActions: some View {
        switch mode {
        case .signIn:
            Button("Create account") {
                withAnimation(.easeInOut(duration: 0.15)) {
                    mode = .signUp
                    focusedField = .email
                }
            }
            .font(ClavisTypography.inter(14, weight: .semibold))
            .foregroundColor(.clavixInk)
            .buttonStyle(.plain)
        case .signUp:
            Button("Already have an account? Sign in") {
                withAnimation(.easeInOut(duration: 0.15)) {
                    mode = .signIn
                    focusedField = .email
                }
            }
            .font(ClavisTypography.inter(14, weight: .semibold))
            .foregroundColor(.clavixInk)
            .buttonStyle(.plain)
        case .forgotPassword:
            Button("Back to sign in") {
                withAnimation(.easeInOut(duration: 0.15)) {
                    mode = .signIn
                    focusedField = .email
                }
            }
            .font(ClavisTypography.inter(14, weight: .semibold))
            .foregroundColor(.clavixInk)
            .buttonStyle(.plain)
        case .welcome:
            EmptyView()
        }
    }

    private var formEyebrow: String {
        switch mode {
        case .signIn:
            return "Account"
        case .signUp:
            return "Account"
        case .forgotPassword:
            return "Account recovery"
        case .welcome:
            return ""
        }
    }

    private var formTitle: String {
        switch mode {
        case .signIn:
            return "Sign in"
        case .signUp:
            return "Create account"
        case .forgotPassword:
            return "Reset password"
        case .welcome:
            return ""
        }
    }

    private var submitTitle: String {
        switch mode {
        case .signUp:
            return "Continue"
        case .signIn:
            return "Sign in"
        case .forgotPassword:
            return "Send reset link"
        case .welcome:
            return ""
        }
    }

    private var formCaption: String? {
        switch mode {
        case .signUp:
            return "Your first report appears after your portfolio is added."
        case .signIn:
            return "Welcome back to Clavix."
        case .forgotPassword:
            return nil
        case .welcome:
            return nil
        }
    }

    private var statusCard: AnyView? {
        if let error = authViewModel.errorMessage?.sanitizedDisplayText, !error.isEmpty {
            return AnyView(ClavixCard(fill: .clavixBadSoft) {
                Text(error)
                    .font(ClavisTypography.inter(14, weight: .regular))
                    .foregroundColor(.clavixInk2)
                    .fixedSize(horizontal: false, vertical: true)
            })
        } else if let status = authViewModel.statusMessage?.sanitizedDisplayText, !status.isEmpty {
            return AnyView(ClavixCard(fill: .clavixAccentSoft) {
                Text(status)
                    .font(ClavisTypography.inter(14, weight: .regular))
                    .foregroundColor(.clavixAccentInk)
                    .fixedSize(horizontal: false, vertical: true)
            })
        }
        return nil
    }

    private var termsFooter: some View {
        VStack(spacing: 2) {
            Text("By continuing you agree to our")
            HStack(spacing: 4) {
                Link("Terms of Service", destination: URL(string: "https://getclavix.com/terms")!)
                    .foregroundColor(.clavixAccent)
                Text("and")
                Link("Privacy Policy", destination: URL(string: "https://getclavix.com/privacy")!)
                    .foregroundColor(.clavixAccent)
            }
        }
        .font(ClavisTypography.clavixMono(10, weight: .regular))
        .foregroundColor(.clavixInk3)
        .multilineTextAlignment(.center)
        .frame(maxWidth: .infinity)
    }

    private func submit() {
        guard isFormValid, !authViewModel.isLoading else { return }
        Task {
            switch mode {
            case .signUp:
                await authViewModel.signUp(email: email, password: password)
            case .signIn:
                await authViewModel.signIn(email: email, password: password)
            case .forgotPassword:
                await authViewModel.resetPassword(email: email)
            case .welcome:
                return
            }
        }
    }
}

private struct AuthActionButton: View {
    let title: String
    let fill: Color
    let foreground: Color
    var bordered: Bool = false
    var isLoading: Bool = false
    var isEnabled: Bool = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack {
                RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous)
                    .fill(backgroundFill)
                    .frame(height: 48)
                    .overlay(
                        RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous)
                            .stroke(borderColor, lineWidth: bordered || !isEnabled ? 1 : 0)
                    )

                if isLoading {
                    ProgressView()
                        .tint(foreground)
                } else {
                    Text(title)
                        .font(ClavisTypography.inter(15, weight: .semibold))
                        .foregroundColor(isEnabled ? foreground : .clavixInk4)
                }
            }
            .opacity(isEnabled ? 1 : 0.7)
        }
        .buttonStyle(.plain)
        .disabled(!isEnabled || isLoading)
    }

    private var backgroundFill: Color {
        if !isEnabled {
            return .clavixPaper2
        }
        return fill
    }

    private var borderColor: Color {
        if bordered || !isEnabled {
            return .clavixRule
        }
        return .clear
    }
}

private struct AuthInputField: View {
    let title: String
    @Binding var text: String
    var focusedField: FocusState<LoginView.Field?>.Binding
    let field: LoginView.Field
    let submitLabel: SubmitLabel
    let onSubmit: () -> Void

    var body: some View {
        TextField(title, text: $text)
            .font(ClavisTypography.inter(15, weight: .regular))
            .foregroundColor(.clavixInk)
            .textContentType(.emailAddress)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .keyboardType(.emailAddress)
            .submitLabel(submitLabel)
            .focused(focusedField, equals: field)
            .onSubmit(onSubmit)
            .padding(.horizontal, 12)
            .frame(height: 48)
            .background(Color.clavixPaper2)
            .overlay(
                RoundedRectangle(cornerRadius: ClavixLayout.controlRadius)
                    .stroke(Color.clavixRule, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous))
    }
}
