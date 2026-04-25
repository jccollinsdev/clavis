import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var email = ""
    @State private var password = ""
    @State private var isSignUp = false
    @FocusState private var focusedField: Field?

    private enum Field: Hashable { case email, password }

    private var isFormValid: Bool {
        !email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !password.isEmpty
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.backgroundPrimary.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 0) {
                        VStack(spacing: 16) {
                            ClavisMonogram(size: 56, cornerRadius: 14)

                            Text("CLAVIX")
                                .font(.custom("Inter", size: 20).weight(.bold))
                                .foregroundColor(.brandCream)
                                .tracking(4)

                            Text("Portfolio intelligence for self-directed investors")
                                .font(.system(size: 14, weight: .regular))
                                .foregroundColor(.textSecondary)
                                .multilineTextAlignment(.center)
                                .lineSpacing(4)
                                .frame(maxWidth: 260)
                        }
                        .padding(.top, 56)
                        .padding(.bottom, 40)

                        VStack(spacing: 14) {
                            TextField("Email address", text: $email)
                                .textFieldStyle(ClavisTextFieldStyle())
                                .textContentType(.emailAddress)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .keyboardType(.emailAddress)
                                .submitLabel(.next)
                                .focused($focusedField, equals: .email)
                                .onSubmit { focusedField = .password }

                            VStack(alignment: .trailing, spacing: 10) {
                                SecureField("Password", text: $password)
                                    .textFieldStyle(ClavisTextFieldStyle())
                                    .textContentType(isSignUp ? .newPassword : .password)
                                    .submitLabel(isSignUp ? .join : .go)
                                    .focused($focusedField, equals: .password)
                                    .onSubmit { submit() }

                                if !isSignUp {
                                    Button("Forgot password?") {
                                        Task { await authViewModel.resetPassword(email: email) }
                                    }
                                    .font(.system(size: 13, weight: .regular))
                                    .foregroundColor(.informational)
                                    .disabled(authViewModel.isLoading || email.isEmpty)
                                }
                            }

                            statusMessage
                                .frame(maxWidth: .infinity, alignment: .leading)

                            ClavisPrimaryButton(
                                title: isSignUp ? "Create account" : "Sign in",
                                isLoading: authViewModel.isLoading,
                                isEnabled: isFormValid
                            ) {
                                submit()
                            }
                        }
                        .frame(maxWidth: 420)

                        Button {
                            withAnimation(.easeInOut(duration: 0.15)) { isSignUp.toggle() }
                        } label: {
                            HStack(spacing: 0) {
                                Text(isSignUp ? "Already have one? " : "Don't have an account? ")
                                    .foregroundColor(.textSecondary)
                                Text(isSignUp ? "Sign in" : "Sign up")
                                    .foregroundColor(.informational)
                                    .fontWeight(.medium)
                            }
                            .font(.system(size: 14, weight: .regular))
                        }
                        .buttonStyle(.plain)
                        .padding(.top, 24)
                    }
                    .padding(.horizontal, 24)
                    .padding(.bottom, 40)
                }
                .scrollDismissesKeyboard(.interactively)

                VStack {
                    Spacer()
                    termsFooter
                }
                .allowsHitTesting(true)
            }
            .ignoresSafeArea(.keyboard, edges: .bottom)
        }
    }

    @ViewBuilder
    private var statusMessage: some View {
        if let error = authViewModel.errorMessage {
            Text(error)
                .font(.system(size: 12, weight: .regular))
                .foregroundColor(.riskF)
                .fixedSize(horizontal: false, vertical: true)
        } else if let status = authViewModel.statusMessage {
            Text(status)
                .font(.system(size: 12, weight: .regular))
                .foregroundColor(.informational)
                .fixedSize(horizontal: false, vertical: true)
        } else {
            Color.clear.frame(height: 14)
        }
    }

    private var termsFooter: some View {
        VStack(spacing: 2) {
            Text("By continuing you agree to our")
            HStack(spacing: 4) {
                Link("Terms of Service", destination: URL(string: "https://getclavix.com/terms")!)
                    .foregroundColor(.textSecondary)
                Text("and")
                Link("Privacy Policy", destination: URL(string: "https://getclavix.com/privacy")!)
                    .foregroundColor(.textSecondary)
            }
        }
        .font(.system(size: 11, weight: .regular))
        .foregroundColor(.textTertiary)
        .multilineTextAlignment(.center)
        .padding(.bottom, 28)
    }

    private func submit() {
        guard isFormValid, !authViewModel.isLoading else { return }
        Task {
            if isSignUp {
                await authViewModel.signUp(email: email, password: password)
            } else {
                await authViewModel.signIn(email: email, password: password)
            }
        }
    }
}
