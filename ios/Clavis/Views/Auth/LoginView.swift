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
                        Spacer(minLength: 0)

                        VStack(spacing: 0) {
                            VStack(spacing: 0) {
                                ZStack {
                                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                                        .fill(Color.surface)
                                        .frame(width: 56, height: 56)
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                                .stroke(Color.border, lineWidth: 1)
                                        )

                                    Text("C")
                                        .font(.system(size: 26, weight: .bold, design: .monospaced))
                                        .foregroundColor(.brandCream)
                                }
                                .padding(.bottom, 16)

                                Text("CLAVIX")
                                    .font(.custom("JetBrainsMono-Regular", size: 20))
                                    .fontWeight(.bold)
                                    .foregroundColor(.brandCream)
                                    .tracking(4)
                                    .padding(.bottom, 10)

                                Text("Portfolio intelligence for self-directed investors")
                                    .font(.system(size: 14, weight: .regular))
                                    .foregroundColor(.textSecondary)
                                    .multilineTextAlignment(.center)
                                    .lineSpacing(4)
                                    .frame(maxWidth: 240)
                                    .padding(.bottom, 36)
                            }

                            VStack(spacing: 12) {
                                TextField("Email address", text: $email)
                                    .textFieldStyle(ClavisTextFieldStyle())
                                    .textContentType(.emailAddress)
                                    .textInputAutocapitalization(.never)
                                    .autocorrectionDisabled()
                                    .keyboardType(.emailAddress)

                                VStack(alignment: .trailing, spacing: 8) {
                                    SecureField("Password", text: $password)
                                        .textFieldStyle(ClavisTextFieldStyle())
                                        .textContentType(isSignUp ? .newPassword : .password)

                                    if !isSignUp {
                                        Button("Forgot password?") {
                                            Task {
                                                await authViewModel.resetPassword(email: email)
                                            }
                                        }
                                        .font(.system(size: 13, weight: .regular))
                                        .foregroundColor(.informational)
                                        .disabled(authViewModel.isLoading || email.isEmpty)
                                    }
                                }

                                Group {
                                    if let error = authViewModel.errorMessage {
                                        Text(error)
                                            .foregroundColor(.riskF)
                                    } else if let status = authViewModel.statusMessage {
                                        Text(status)
                                            .foregroundColor(.informational)
                                    } else {
                                        Color.clear
                                    }
                                }
                                .font(.system(size: 12, weight: .regular))
                                .frame(maxWidth: .infinity, minHeight: 18, alignment: .leading)

                                Button {
                                    Task {
                                        if isSignUp {
                                            await authViewModel.signUp(email: email, password: password)
                                        } else {
                                            await authViewModel.signIn(email: email, password: password)
                                        }
                                    }
                                } label: {
                                    ZStack {
                                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                                            .fill(Color.textPrimary)
                                            .frame(height: 50)

                                        if authViewModel.isLoading {
                                            ProgressView()
                                                .tint(.backgroundPrimary)
                                        } else {
                                            Text(isSignUp ? "Create Account" : "Sign In")
                                                .font(.system(size: 16, weight: .semibold))
                                                .foregroundColor(.backgroundPrimary)
                                        }
                                    }
                                }
                                .buttonStyle(.plain)
                                .disabled(authViewModel.isLoading || email.isEmpty || password.isEmpty)
                            }
                            .frame(maxWidth: 420)

                            Button {
                                isSignUp.toggle()
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
                            .padding(.top, 22)
                        }
                        .padding(.horizontal, 24)

                        Spacer(minLength: 0)

                        Text("By continuing you agree to our Terms of Service\nand Privacy Policy.")
                            .font(.system(size: 11, weight: .regular))
                            .foregroundColor(.textTertiary)
                            .multilineTextAlignment(.center)
                            .lineSpacing(4)
                            .padding(.bottom, 36)
                    }
                    .frame(width: geo.size.width, height: geo.size.height)
                    .ignoresSafeArea(.keyboard, edges: .bottom)
                }
            }
        }
    }
}
