import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/custom_widgets.dart';
import '../../utils/app_theme.dart';
import '../../utils/routes.dart';

class RoleSelectionScreen extends StatefulWidget {
  const RoleSelectionScreen({super.key});

  @override
  State<RoleSelectionScreen> createState() => _RoleSelectionScreenState();
}

class _RoleSelectionScreenState extends State<RoleSelectionScreen>
    with TickerProviderStateMixin {
  String? _selectedRole;
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeInOut),
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  Future<void> _handleRoleSelection() async {
    if (_selectedRole == null) return;

    final authProvider = Provider.of<AuthProvider>(context, listen: false);

    final success = await authProvider.setUserRole(_selectedRole!);

    if (!mounted) return;

    if (success) {
      if (_selectedRole == 'student') {
        // Student goes to home page - clear entire navigation stack
        Navigator.pushNamedAndRemoveUntil(
          context,
          Routes.studentHome,
          (route) => false, // Remove all previous routes
        );
      } else {
        // Teacher goes to home page - clear entire navigation stack
        Navigator.pushNamedAndRemoveUntil(
          context,
          Routes.teacherHome,
          (route) => false, // Remove all previous routes
        );
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(authProvider.error ?? 'Failed to set role'),
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
            message: 'Setting up your account...',
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: FadeTransition(
                  opacity: _fadeAnimation,
                  child: AnimationLimiter(
                    child: Column(
                      children: AnimationConfiguration.toStaggeredList(
                        duration: const Duration(milliseconds: 600),
                        childAnimationBuilder: (widget) => SlideAnimation(
                          verticalOffset: 50.0,
                          child: FadeInAnimation(child: widget),
                        ),
                        children: [
                          const Spacer(),

                          // Header
                          Column(
                            children: [
                              Container(
                                width: 100,
                                height: 100,
                                decoration: BoxDecoration(
                                  gradient: AppTheme.primaryGradient,
                                  borderRadius: BorderRadius.circular(25),
                                ),
                                child: const Icon(
                                  Icons.people_outline,
                                  size: 50,
                                  color: Colors.white,
                                ),
                              ),
                              const SizedBox(height: 32),
                              Text(
                                'Choose Your Role',
                                style: Theme.of(context).textTheme.displaySmall
                                    ?.copyWith(
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.textPrimary,
                                    ),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                'Select your role to personalize your experience',
                                style: Theme.of(context).textTheme.bodyLarge
                                    ?.copyWith(color: AppTheme.textSecondary),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),

                          const SizedBox(height: 48),

                          // Role Selection Cards
                          _buildRoleCard(
                            role: 'student',
                            title: 'Student',
                            subtitle: 'Join classes and track your attendance',
                            icon: Icons.school,
                            color: AppTheme.primaryColor,
                          ),

                          const SizedBox(height: 20),

                          _buildRoleCard(
                            role: 'teacher',
                            title: 'Teacher',
                            subtitle: 'Create classes and manage attendance',
                            icon: Icons.person_outline,
                            color: AppTheme.secondaryColor,
                          ),

                          const Spacer(),

                          // Continue Button
                          AnimatedOpacity(
                            opacity: _selectedRole != null ? 1.0 : 0.5,
                            duration: const Duration(milliseconds: 300),
                            child: CustomButton(
                              text: 'Continue',
                              width: double.infinity,
                              onPressed: _selectedRole != null
                                  ? _handleRoleSelection
                                  : null,
                              isLoading: authProvider.isLoading,
                              icon: Icons.arrow_forward,
                            ),
                          ),

                          const SizedBox(height: 32),
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

  Widget _buildRoleCard({
    required String role,
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
  }) {
    final isSelected = _selectedRole == role;

    return AnimatedCard(
      onTap: () {
        setState(() {
          _selectedRole = role;
        });
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? color : AppTheme.borderColor,
            width: isSelected ? 2 : 1,
          ),
          color: isSelected ? color.withOpacity(0.05) : Colors.white,
        ),
        child: Row(
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              width: 60,
              height: 60,
              decoration: BoxDecoration(
                color: isSelected ? color : color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(15),
              ),
              child: Icon(
                icon,
                color: isSelected ? Colors.white : color,
                size: 30,
              ),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: isSelected ? color : AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            AnimatedRotation(
              turns: isSelected ? 0.25 : 0,
              duration: const Duration(milliseconds: 300),
              child: Icon(
                isSelected ? Icons.check_circle : Icons.circle_outlined,
                color: isSelected ? color : AppTheme.textSecondary,
                size: 24,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
