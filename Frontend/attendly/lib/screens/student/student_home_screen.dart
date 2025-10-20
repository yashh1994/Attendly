import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/custom_widgets.dart';
import '../../utils/app_theme.dart';
import '../../utils/routes.dart';
import '../../models/class.dart';
import '../account_screen.dart';

class StudentHomeScreen extends StatefulWidget {
  const StudentHomeScreen({super.key});

  @override
  State<StudentHomeScreen> createState() => _StudentHomeScreenState();
}

class _StudentHomeScreenState extends State<StudentHomeScreen>
    with TickerProviderStateMixin {
  final _joinCodeController = TextEditingController();
  final ApiService _apiService = ApiService();
  List<ClassModel> _enrolledClasses = [];
  bool _isLoading = false;
  bool _hasFaceData = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    await Future.wait([_loadEnrolledClasses(), _checkFaceDataStatus()]);
  }

  Future<void> _checkFaceDataStatus() async {
    try {
      // Get token from auth provider and set in API service
      final authProvider = context.read<AuthProvider>();
      if (authProvider.token != null) {
        _apiService.setToken(authProvider.token);
      }

      final response = await _apiService.getStudentFaceDataStatus();
      print('🔥 FLUTTER: Face data status response: $response');
      print('🔥 FLUTTER: Registered value: ${response['registered']}');
      setState(() {
        _hasFaceData = response['registered'] ?? false;
        print('🔥 FLUTTER: _hasFaceData set to: $_hasFaceData');
      });
    } catch (e) {
      print('🔥 FLUTTER: Error checking face data status: $e');
      // Don't show error for face data status, it's not critical
    }
  }

  @override
  void dispose() {
    _joinCodeController.dispose();
    super.dispose();
  }

  Future<void> _loadEnrolledClasses() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // Get token from auth provider and set in API service
      final authProvider = context.read<AuthProvider>();
      if (authProvider.token != null) {
        _apiService.setToken(authProvider.token);
      }

      print('🔥 FLUTTER: Loading enrolled classes from API...');
      final classes = await _apiService.getMyClasses();

      setState(() {
        _enrolledClasses = classes;
        _isLoading = false;
      });

      print('🔥 FLUTTER: Loaded ${classes.length} enrolled classes');
    } catch (e) {
      print('🔥 FLUTTER: Error loading enrolled classes: $e');
      setState(() {
        _error = e.toString();
        _isLoading = false;
        _enrolledClasses = []; // Clear any existing data
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to load classes: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  Future<void> _joinClass() async {
    final joinCode = _joinCodeController.text.trim();
    if (joinCode.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a join code'),
          backgroundColor: AppTheme.errorColor,
        ),
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      // Get token from auth provider and set in API service
      final authProvider = context.read<AuthProvider>();
      if (authProvider.token != null) {
        _apiService.setToken(authProvider.token);
      }

      print('🔥 FLUTTER: Joining class with code: $joinCode');
      await _apiService.joinClass(joinCode);

      Navigator.pop(context);
      _joinCodeController.clear();

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Successfully joined class!'),
          backgroundColor: AppTheme.successColor,
        ),
      );

      // Reload the classes list
      _loadEnrolledClasses();
    } catch (e) {
      print('🔥 FLUTTER: Error joining class: $e');
      setState(() {
        _isLoading = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to join class: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  void _showJoinClassDialog() {
    // Check if student has registered facial data first
    if (!_hasFaceData) {
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          title: Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: Colors.amber.shade700),
              const SizedBox(width: 8),
              const Text('Facial Data Required'),
            ],
          ),
          content: const Text(
            'You need to register your facial data before joining a class. Please register your face data from the Account page.',
            style: TextStyle(fontSize: 15),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context);
                Navigator.pushNamed(context, Routes.faceCapture);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.amber.shade700,
              ),
              child: const Text(
                'Register Now',
                style: TextStyle(color: Colors.white),
              ),
            ),
          ],
        ),
      );
      return;
    }

    // Show join class dialog if facial data is registered
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Join Class'),
        content: CustomTextField(
          controller: _joinCodeController,
          hint: 'Enter join code',
          prefixIcon: Icons.vpn_key,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(onPressed: _joinClass, child: const Text('Join')),
        ],
      ),
    );
  }

  void _showLeaveClassDialog(ClassModel classModel) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: AppTheme.warningColor),
            const SizedBox(width: 8),
            const Text('Leave Class'),
          ],
        ),
        content: Text(
          'Are you sure you want to leave "${classModel.name}"?\n\nYou will lose access to all class materials and attendance records.',
          style: const TextStyle(fontSize: 15),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _leaveClass(classModel);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.errorColor,
            ),
            child: const Text(
              'Leave Class',
              style: TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _leaveClass(ClassModel classModel) async {
    try {
      setState(() {
        _isLoading = true;
      });

      print(
        '🔥 FLUTTER: Leaving class: ${classModel.name} (ID: ${classModel.id})',
      );

      await _apiService.leaveClass(classId: classModel.id);

      if (!mounted) return;

      // Remove the class from the list
      setState(() {
        _enrolledClasses.removeWhere((c) => c.id == classModel.id);
        _isLoading = false;
      });

      // Show success message
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Successfully left "${classModel.name}"'),
          backgroundColor: AppTheme.successColor,
          behavior: SnackBarBehavior.floating,
        ),
      );

      print('🔥 FLUTTER: Successfully left class');
    } catch (e) {
      print('🔥 FLUTTER: Error leaving class: $e');

      if (!mounted) return;

      setState(() {
        _isLoading = false;
      });

      // Show error message
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to leave class: ${e.toString()}'),
          backgroundColor: AppTheme.errorColor,
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 4),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Welcome back,', style: Theme.of(context).textTheme.bodySmall),
            Text(
              authProvider.user?.firstName ?? 'Student',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () {
              // TODO: Show notifications
            },
          ),
          IconButton(
            icon: const Icon(Icons.account_circle),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const AccountScreen()),
              );
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                padding: const EdgeInsets.all(20),
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
                        // Quick Actions
                        Row(
                          children: [
                            Expanded(
                              child: AnimatedCard(
                                onTap: _showJoinClassDialog,
                                padding: const EdgeInsets.all(20),
                                child: Column(
                                  children: [
                                    Container(
                                      width: 50,
                                      height: 50,
                                      decoration: BoxDecoration(
                                        color: AppTheme.primaryColor
                                            .withOpacity(0.1),
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: const Icon(
                                        Icons.add,
                                        color: AppTheme.primaryColor,
                                        size: 24,
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      'Join Class',
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleSmall
                                          ?.copyWith(
                                            fontWeight: FontWeight.w600,
                                          ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: AnimatedCard(
                                onTap: () {
                                  // Check if student has facial data before allowing QR scan
                                  if (!_hasFaceData) {
                                    showDialog(
                                      context: context,
                                      builder: (context) => AlertDialog(
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.circular(
                                            16,
                                          ),
                                        ),
                                        title: Row(
                                          children: [
                                            Icon(
                                              Icons.warning_amber_rounded,
                                              color: Colors.amber.shade700,
                                            ),
                                            const SizedBox(width: 8),
                                            const Text('Facial Data Required'),
                                          ],
                                        ),
                                        content: const Text(
                                          'You need to register your facial data before joining a class. Please register your face data from the Account page.',
                                          style: TextStyle(fontSize: 15),
                                        ),
                                        actions: [
                                          TextButton(
                                            onPressed: () =>
                                                Navigator.pop(context),
                                            child: const Text('Cancel'),
                                          ),
                                          ElevatedButton(
                                            onPressed: () {
                                              Navigator.pop(context);
                                              Navigator.pushNamed(
                                                context,
                                                Routes.faceCapture,
                                              );
                                            },
                                            style: ElevatedButton.styleFrom(
                                              backgroundColor:
                                                  Colors.amber.shade700,
                                            ),
                                            child: const Text(
                                              'Register Now',
                                              style: TextStyle(
                                                color: Colors.white,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    );
                                    return;
                                  }
                                  // TODO: Show QR scanner
                                },
                                padding: const EdgeInsets.all(20),
                                child: Column(
                                  children: [
                                    Container(
                                      width: 50,
                                      height: 50,
                                      decoration: BoxDecoration(
                                        color: AppTheme.secondaryColor
                                            .withOpacity(0.1),
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: const Icon(
                                        Icons.qr_code_scanner,
                                        color: AppTheme.secondaryColor,
                                        size: 24,
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      'Scan QR',
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleSmall
                                          ?.copyWith(
                                            fontWeight: FontWeight.w600,
                                          ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(height: 32),

                        // My Classes Section
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              'My Classes',
                              style: Theme.of(context).textTheme.headlineSmall
                                  ?.copyWith(fontWeight: FontWeight.bold),
                            ),
                            if (_enrolledClasses.isNotEmpty)
                              TextButton(
                                onPressed: () {
                                  // TODO: Show all classes
                                },
                                child: const Text('View All'),
                              ),
                          ],
                        ),

                        const SizedBox(height: 16),

                        // Classes List
                        if (_enrolledClasses.isEmpty)
                          AnimatedCard(
                            padding: const EdgeInsets.all(32),
                            child: Column(
                              children: [
                                Icon(
                                  Icons.school_outlined,
                                  size: 64,
                                  color: AppTheme.textSecondary.withOpacity(
                                    0.5,
                                  ),
                                ),
                                const SizedBox(height: 16),
                                Text(
                                  'No Classes Yet',
                                  style: Theme.of(context).textTheme.titleLarge
                                      ?.copyWith(color: AppTheme.textSecondary),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Join your first class using a join code or QR code',
                                  textAlign: TextAlign.center,
                                  style: Theme.of(context).textTheme.bodyMedium
                                      ?.copyWith(color: AppTheme.textSecondary),
                                ),
                                const SizedBox(height: 20),
                                CustomButton(
                                  text: 'Join Class',
                                  onPressed: _showJoinClassDialog,
                                  icon: Icons.add,
                                ),
                              ],
                            ),
                          )
                        else
                          ...AnimationConfiguration.toStaggeredList(
                            duration: const Duration(milliseconds: 400),
                            childAnimationBuilder: (widget) => SlideAnimation(
                              horizontalOffset: 50.0,
                              child: FadeInAnimation(child: widget),
                            ),
                            children: _enrolledClasses.map((classModel) {
                              return Padding(
                                padding: const EdgeInsets.only(bottom: 16),
                                child: _buildClassCard(classModel),
                              );
                            }).toList(),
                          ),

                        const SizedBox(height: 20),
                      ],
                    ),
                  ),
                ),
              ),
      ),
    );
  }

  Widget _buildClassCard(ClassModel classModel) {
    return AnimatedCard(
      onTap: () {
        // TODO: Navigate to class detail
      },
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      classModel.name,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'by ${classModel.teacherName}',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: AppTheme.successColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  'Active',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppTheme.successColor,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          Text(
            classModel.description,
            style: Theme.of(context).textTheme.bodyMedium,
          ),

          const SizedBox(height: 16),

          Row(
            children: [
              Icon(
                Icons.people_outline,
                size: 16,
                color: AppTheme.textSecondary,
              ),
              const SizedBox(width: 4),
              Text(
                '${classModel.totalStudents} students',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppTheme.textSecondary),
              ),
              const Spacer(),
              Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: AppTheme.successColor,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '85% Attendance',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ],
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Leave Class Button
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => _showLeaveClassDialog(classModel),
              icon: const Icon(Icons.exit_to_app, size: 18),
              label: const Text('Leave Class'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.errorColor,
                side: BorderSide(color: AppTheme.errorColor.withOpacity(0.5)),
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
