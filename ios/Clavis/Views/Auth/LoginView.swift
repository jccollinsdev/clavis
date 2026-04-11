import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var email = ""
    @State private var password = ""
    @State private var isSignUp = false

    var body: some View {
        NavigationStack {
            ZStack {
                ClavisAtmosphereBackground()

                VStack(spacing: ClavisTheme.largeSpacing) {
                    VStack(spacing: ClavisTheme.smallSpacing) {
                        Text("Clavis")
                            .font(.system(size: 34, weight: .bold))
                            .foregroundColor(.textPrimary)

                        Text("Portfolio intelligence for self-directed investors")
                            .font(.body)
                            .foregroundColor(.textSecondary)
                            .multilineTextAlignment(.center)
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
                                .font(.footnote)
                                .foregroundColor(.red)
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
                                    .tint(.white)
                                    .frame(maxWidth: .infinity)
                            } else {
                                Text(isSignUp ? "Create Account" : "Sign In")
                                    .font(.headline)
                                    .frame(maxWidth: .infinity)
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                        .disabled(authViewModel.isLoading || email.isEmpty || password.isEmpty)

                        Button(isSignUp ? "Already have an account? Sign In" : "Don't have an account? Sign Up") {
                            isSignUp.toggle()
                        }
                        .font(.footnote)
                    }
                    .padding(ClavisTheme.largeSpacing)
                    .background(Color.cardBackground)
                    .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                            .stroke(Color.borderSubtle, lineWidth: 1)
                    )
                }
                .padding(.horizontal, 20)
            }
        }
    }
}
