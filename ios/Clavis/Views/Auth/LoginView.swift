import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var email = ""
    @State private var password = ""
    @State private var isSignUp = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.backgroundPrimary.ignoresSafeArea()

                VStack(spacing: ClavisTheme.largeSpacing) {
                    // Logo + wordmark
                    VStack(spacing: ClavisTheme.mediumSpacing) {
                        Image("clavix_logo")
                            .resizable()
                            .scaledToFit()
                            .frame(height: 64)

                        VStack(spacing: 4) {
                            Text("CLAVIX")
                                .font(ClavisTypography.h1)
                                .foregroundColor(.textPrimary)
                                .kerning(-0.56)   // -0.02em at 28px

                            Text("Portfolio intelligence for self-directed investors")
                                .font(ClavisTypography.body)
                                .foregroundColor(.textSecondary)
                                .multilineTextAlignment(.center)
                        }
                    }

                    // Auth form
                    VStack(spacing: ClavisTheme.mediumSpacing) {
                        TextField("Email", text: $email)
                            .textFieldStyle(.roundedBorder)
                            .textContentType(.emailAddress)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .keyboardType(.emailAddress)

                        SecureField("Password", text: $password)
                            .textFieldStyle(.roundedBorder)
                            .textContentType(isSignUp ? .newPassword : .password)

                        if let error = authViewModel.errorMessage {
                            Text(error)
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.riskF)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }

                        Button {
                            Task {
                                if isSignUp {
                                    await authViewModel.signUp(email: email, password: password)
                                } else {
                                    await authViewModel.signIn(email: email, password: password)
                                }
                            }
                        } label: {
                            if authViewModel.isLoading {
                                ProgressView()
                                    .tint(.textPrimary)
                                    .frame(maxWidth: .infinity)
                            } else {
                                Text(isSignUp ? "Create Account" : "Sign In")
                                    .font(ClavisTypography.action)
                                    .frame(maxWidth: .infinity)
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(Color.informational)
                        .controlSize(.large)
                        .disabled(authViewModel.isLoading || email.isEmpty || password.isEmpty)

                        Button(isSignUp ? "Already have an account? Sign In" : "Don't have an account? Sign Up") {
                            isSignUp.toggle()
                        }
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                    }
                    .padding(ClavisTheme.largeSpacing)
                    .clavisCardStyle()
                }
                .padding(.horizontal, 20)
            }
        }
    }
}
