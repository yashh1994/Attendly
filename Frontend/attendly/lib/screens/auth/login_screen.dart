import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/custom_widgets.dart';
import '../../utils/app_theme.dart';
import '../../utils/routes.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    final authProvider = Provider.of<AuthProvider>(context, listen: false);

    final success = await authProvider.login(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );

    if (!mounted) return;

    if (success) {
      // Navigate based on user role - clear entire navigation stack
      if (authProvider.userRole == 'student') {
        Navigator.pushNamedAndRemoveUntil(
          context,
          Routes.studentHome,
          (route) => false, // Remove all previous routes
        );
      } else {
        Navigator.pushNamedAndRemoveUntil(
          context,
          Routes.teacherHome,
          (route) => false, // Remove all previous routes
        );
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(authProvider.error ?? 'Login failed'),
          backgroundColor: AppTheme.errorColor,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Consumer<AuthProvider>(
        builder: (context, authProvider, child) {
          return LoadingOverlay(
            isLoading: authProvider.isLoading,
            message: 'Logging in...',
            child: SafeArea(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: Form(
                  key: _formKey,
                  child: AnimationLimiter(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: AnimationConfiguration.toStaggeredList(
                        duration: const Duration(milliseconds: 600),
                        childAnimationBuilder: (widget) => SlideAnimation(
                          verticalOffset: 50.0,
                          child: FadeInAnimation(child: widget),
                        ),
                        children: [
                          const SizedBox(height: 40),

                          // Logo and Welcome Text
                          Center(
                            child: Column(
                              children: [
                                Container(
                                  width: 80,
                                  height: 80,
                                  decoration: BoxDecoration(
                                    gradient: AppTheme.primaryGradient,
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: const Icon(
                                    Icons.face_retouching_natural,
                                    size: 40,
                                    color: Colors.white,
                                  ),
                                ),
                                const SizedBox(height: 24),
                                Text(
                                  'Welcome Back!',
                                  style: Theme.of(context)
                                      .textTheme
                                      .displaySmall
                                      ?.copyWith(
                                        fontWeight: FontWeight.bold,
                                        color: AppTheme.textPrimary,
                                      ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Sign in to your account',
                                  style: Theme.of(context).textTheme.bodyLarge
                                      ?.copyWith(color: AppTheme.textSecondary),
                                ),
                              ],
                            ),
                          ),

                          const SizedBox(height: 40),

                          // Login Form
                          AnimatedCard(
                            padding: const EdgeInsets.all(24),
                            child: Column(
                              children: [
                                CustomTextField(
                                  label: 'Email',
                                  hint: 'Enter your email address',
                                  controller: _emailController,
                                  keyboardType: TextInputType.emailAddress,
                                  prefixIcon: Icons.email_outlined,
                                  validator: (value) {
                                    if (value?.isEmpty ?? true) {
                                      return 'Please enter your email';
                                    }
                                    if (!RegExp(
                                      r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$',
                                    ).hasMatch(value!)) {
                                      return 'Please enter a valid email';
                                    }
                                    return null;
                                  },
                                ),

                                const SizedBox(height: 20),

                                CustomTextField(
                                  label: 'Password',
                                  hint: 'Enter your password',
                                  controller: _passwordController,
                                  obscureText: true,
                                  prefixIcon: Icons.lock_outline,
                                  validator: (value) {
                                    if (value?.isEmpty ?? true) {
                                      return 'Please enter your password';
                                    }
                                    if (value!.length < 6) {
                                      return 'Password must be at least 6 characters';
                                    }
                                    return null;
                                  },
                                ),

                                const SizedBox(height: 8),

                                // Forgot Password
                                Align(
                                  alignment: Alignment.centerRight,
                                  child: TextButton(
                                    onPressed: () {
                                      // TODO: Implement forgot password
                                    },
                                    child: const Text('Forgot Password?'),
                                  ),
                                ),

                                const SizedBox(height: 24),

                                // Login Button
                                CustomButton(
                                  text: 'Sign In',
                                  width: double.infinity,
                                  onPressed: _handleLogin,
                                  isLoading: authProvider.isLoading,
                                  icon: Icons.login,
                                ),
                              ],
                            ),
                          ),

                          const SizedBox(height: 32),

                          // Sign Up Link
                          Center(
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  'Don\'t have an account? ',
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                TextButton(
                                  onPressed: () {
                                    Navigator.pushNamed(context, Routes.signup);
                                  },
                                  child: const Text(
                                    'Sign Up',
                                    style: TextStyle(
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),

                          const SizedBox(height: 40),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
