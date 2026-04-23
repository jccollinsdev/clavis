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

                GeometryReader { geo in
                    VStack(spacing: 0) {
                        Spacer(minLength: 12)

                        VStack(spacing: ClavisTheme.mediumSpacing) {
                            VStack(spacing: 10) {
                                Image("AppLogo")
                                    .resizable()
                                    .scaledToFit()
                                    .frame(width: 96, height: 96)

                                VStack(spacing: 6) {
                                    Text("CLAVIX")
                                        .font(ClavisTypography.brandWordmark)
                                        .foregroundColor(.brandCream)
                                        .kerning(2.2)

                                    Text("Portfolio intelligence for self-directed investors")
                                        .font(ClavisTypography.bodyEmphasis)
                                        .foregroundColor(.textSecondary)
                                        .multilineTextAlignment(.center)
                                }
                            }

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
                                        .minimumScaleFactor(0.9)
                                }

                                if let status = authViewModel.statusMessage {
                                    Text(status)
                                        .font(ClavisTypography.footnote)
                                        .foregroundColor(.informational)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .minimumScaleFactor(0.9)
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
                                            .font(ClavisTypography.bodyEmphasis)
                                            .frame(maxWidth: .infinity)
                                    }
                                }
                                .buttonStyle(.borderedProminent)
                                .tint(Color.informational)
                                .controlSize(.regular)
                                .padding(.vertical, 2)
                                .disabled(authViewModel.isLoading || email.isEmpty || password.isEmpty)

                                Button(isSignUp ? "Already have an account? Sign In" : "Don't have an account? Sign Up") {
                                    isSignUp.toggle()
                                }
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.textSecondary)

                                Button("Forgot password?") {
                                    Task {
                                        await authViewModel.resetPassword(email: email)
                                    }
                                }
                                .font(ClavisTypography.footnote)
                                .foregroundColor(.informational)
                                .disabled(authViewModel.isLoading || email.isEmpty)
                            }
                            .padding(ClavisTheme.largeSpacing)
                            .clavisCardStyle()
                        }
                        .frame(maxWidth: 420)
                        .frame(maxWidth: .infinity)
                        .padding(.horizontal, 20)

                        Spacer(minLength: 12)
                    }
                    .frame(width: geo.size.width, height: geo.size.height)
                    .ignoresSafeArea(.keyboard, edges: .bottom)
                }
            }
        }
    }
}
