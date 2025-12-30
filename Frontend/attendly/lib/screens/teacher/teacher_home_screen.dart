import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/custom_widgets.dart';
import '../../utils/app_theme.dart';
import '../../models/class.dart';
import '../class_detail_screen.dart';
import '../account_screen.dart';
import 'take_attendance_screen.dart';

class TeacherHomeScreen extends StatefulWidget {
  const TeacherHomeScreen({super.key});

  @override
  State<TeacherHomeScreen> createState() => _TeacherHomeScreenState();
}

class _TeacherHomeScreenState extends State<TeacherHomeScreen> {
  final _classNameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final ApiService _apiService = ApiService();
  List<ClassModel> _createdClasses = [];
  bool _isLoading = false;
  String? _error;

  // Dashboard statistics
  int _totalClasses = 0;
  int _totalStudents = 0;
  int _todaysSessions = 0;
  double _avgAttendance = 0.0;

  @override
  void initState() {
    super.initState();
    _loadCreatedClasses();
    _loadDashboardStats();
  }

  @override
  void dispose() {
    _classNameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _loadCreatedClasses() async {
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

      print('🔥 FLUTTER: Loading created classes from API...');
      final classes = await _apiService.getMyClasses();

      setState(() {
        _createdClasses = classes;
        _isLoading = false;
      });

      print('🔥 FLUTTER: Loaded ${classes.length} created classes');
    } catch (e) {
      print('🔥 FLUTTER: Error loading created classes: $e');
      setState(() {
        _error = e.toString();
        _isLoading = false;
        _createdClasses = []; // Clear any existing data
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

  Future<void> _loadDashboardStats() async {
    try {
      // Get token from auth provider and set in API service
      final authProvider = context.read<AuthProvider>();
      if (authProvider.token != null) {
        _apiService.setToken(authProvider.token);
        print('🔥 FLUTTER: Token set for dashboard stats API call');
      } else {
        print('🔥 FLUTTER: ERROR - No token available for dashboard stats');
        return;
      }

      print('🔥 FLUTTER: Loading dashboard statistics from API...');
      final statsData = await _apiService.getTeacherDashboardStats();

      print('🔥 FLUTTER: Raw stats data received: $statsData');

      if (statsData['statistics'] != null) {
        final stats = statsData['statistics'];
        print('🔥 FLUTTER: Statistics object: $stats');

        final totalClasses = stats['total_classes'] ?? 0;
        final totalStudents = stats['total_students'] ?? 0;
        final todaysSessions = stats['todays_sessions'] ?? 0;
        final avgAttendance = (stats['avg_attendance_rate'] ?? 0.0).toDouble();

        print(
          '🔥 FLUTTER: Parsed values - Classes: $totalClasses, Students: $totalStudents, Today: $todaysSessions, Avg: $avgAttendance',
        );

        setState(() {
          _totalClasses = totalClasses;
          _totalStudents = totalStudents;
          _todaysSessions = todaysSessions;
          _avgAttendance = avgAttendance;
        });

        print(
          '🔥 FLUTTER: State updated - Classes: $_totalClasses, Students: $_totalStudents, Today: $_todaysSessions, Avg: $_avgAttendance%',
        );
      } else {
        print('🔥 FLUTTER: ERROR - No statistics object in response');
      }
    } catch (e) {
      print('🔥 FLUTTER: Error loading dashboard stats: $e');
      print('🔥 FLUTTER: Error type: ${e.runtimeType}');
      // Don't show error to user for stats, just use default values
    }
  }

  Future<void> _createClass() async {
    final className = _classNameController.text.trim();
    final description = _descriptionController.text.trim();

    if (className.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a class name'),
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

      print('🔥 FLUTTER: Creating class: $className');
      await _apiService.createClass(name: className, description: description);

      Navigator.pop(context);
      _classNameController.clear();
      _descriptionController.clear();

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Class created successfully!'),
          backgroundColor: AppTheme.successColor,
        ),
      );

      // Reload the classes list and stats
      _loadCreatedClasses();
      _loadDashboardStats();
    } catch (e) {
      print('🔥 FLUTTER: Error creating class: $e');
      setState(() {
        _isLoading = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to create class: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  void _navigateToTakeAttendance(ClassModel classModel) async {
    print(
      '🔥 FLUTTER: Navigating to Take Attendance for class: ${classModel.name} (ID: ${classModel.id})',
    );

    try {
      final result = await Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => TakeAttendanceScreen(
            classId: classModel.id,
            className: classModel.name,
          ),
        ),
      );

      print('🔥 FLUTTER: Returned from Take Attendance. Result: $result');

      // Refresh classes list and stats if attendance was submitted
      if (result == true) {
        _loadCreatedClasses();
        _loadDashboardStats();
      }
    } catch (e) {
      print('🔥 FLUTTER: Error navigating to Take Attendance: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error opening attendance screen: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _shareClassCode(ClassModel classModel) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Share Class Code'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.primaryColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: AppTheme.primaryColor.withOpacity(0.3),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    classModel.joinCode,
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryColor,
                    ),
                  ),
                  IconButton(
                    onPressed: () => _copyJoinCode(classModel.joinCode),
                    icon: const Icon(Icons.copy),
                    tooltip: 'Copy Code',
                    style: IconButton.styleFrom(
                      backgroundColor: AppTheme.primaryColor,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Share this code with students to join ${classModel.name}',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
          ElevatedButton.icon(
            onPressed: () => _copyJoinCode(classModel.joinCode),
            icon: const Icon(Icons.copy),
            label: const Text('Copy Code'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryColor,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _copyJoinCode(String joinCode) async {
    try {
      await Clipboard.setData(ClipboardData(text: joinCode));

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.check, color: Colors.white),
                const SizedBox(width: 8),
                Text('Join code "$joinCode" copied to clipboard!'),
              ],
            ),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to copy code: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 2),
          ),
        );
      }
    }
  }

  void _showCreateClassDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Create New Class'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CustomTextField(
              controller: _classNameController,
              hint: 'Class name',
              prefixIcon: Icons.class_,
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _descriptionController,
              hint: 'Description (optional)',
              prefixIcon: Icons.description,
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(onPressed: _createClass, child: const Text('Create')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Good morning,', style: Theme.of(context).textTheme.bodySmall),
            Text(
              'Prof. ${authProvider.user?.firstName ?? 'Teacher'}',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.analytics_outlined),
            onPressed: () {
              // TODO: Show analytics
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
        onRefresh: () async {
          await Future.wait([_loadCreatedClasses(), _loadDashboardStats()]);
        },
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
                        // Statistics Cards
                        Row(
                          children: [
                            Expanded(
                              child: _buildStatCard(
                                'Total Classes',
                                '$_totalClasses',
                                Icons.school,
                                AppTheme.primaryColor,
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: _buildStatCard(
                                'Total Students',
                                '$_totalStudents',
                                Icons.people,
                                AppTheme.successColor,
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(height: 20),

                        Row(
                          children: [
                            Expanded(
                              child: _buildStatCard(
                                'Today\'s Sessions',
                                '$_todaysSessions',
                                Icons.today,
                                AppTheme.warningColor,
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: _buildStatCard(
                                'Avg. Attendance',
                                '${_avgAttendance.toStringAsFixed(1)}%',
                                Icons.trending_up,
                                AppTheme.secondaryColor,
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
                            if (_createdClasses.isNotEmpty)
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
                        if (_createdClasses.isEmpty)
                          AnimatedCard(
                            padding: const EdgeInsets.all(32),
                            child: Column(
                              children: [
                                Icon(
                                  Icons.add_circle_outline,
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
                                  'Create your first class to get started',
                                  textAlign: TextAlign.center,
                                  style: Theme.of(context).textTheme.bodyMedium
                                      ?.copyWith(color: AppTheme.textSecondary),
                                ),
                                const SizedBox(height: 20),
                                CustomButton(
                                  text: 'Create Class',
                                  onPressed: _showCreateClassDialog,
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
                            children: _createdClasses.map((classModel) {
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
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showCreateClassDialog,
        icon: const Icon(Icons.add),
        label: const Text('Create Class'),
        backgroundColor: AppTheme.primaryColor,
        foregroundColor: Colors.white,
      ),
    );
  }

  Widget _buildStatCard(
    String title,
    String value,
    IconData icon,
    Color color,
  ) {
    return AnimatedCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: color, size: 20),
              ),
              const Spacer(),
              Icon(Icons.trending_up, color: AppTheme.successColor, size: 16),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            value,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            title,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppTheme.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildClassCard(ClassModel classModel) {
    return AnimatedCard(
      onTap: () {
        // Navigate to class detail screen with calendar and student list
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ClassDetailScreen(classModel: classModel),
          ),
        );
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
                      'Code: ${classModel.joinCode}',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppTheme.primaryColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              PopupMenuButton(
                icon: const Icon(Icons.more_vert),
                itemBuilder: (context) => [
                  const PopupMenuItem(
                    value: 'edit',
                    child: Row(
                      children: [
                        Icon(Icons.edit, size: 16),
                        SizedBox(width: 8),
                        Text('Edit'),
                      ],
                    ),
                  ),
                  const PopupMenuItem(
                    value: 'share',
                    child: Row(
                      children: [
                        Icon(Icons.share, size: 16),
                        SizedBox(width: 8),
                        Text('Share Code'),
                      ],
                    ),
                  ),
                  const PopupMenuItem(
                    value: 'attendance',
                    child: Row(
                      children: [
                        Icon(Icons.camera_alt, size: 16),
                        SizedBox(width: 8),
                        Text('Take Attendance'),
                      ],
                    ),
                  ),
                ],
                onSelected: (value) {
                  print(
                    '🔥 FLUTTER: PopupMenu selected: $value for class: ${classModel.name}',
                  );
                  if (value == 'attendance') {
                    print('🔥 FLUTTER: Calling _navigateToTakeAttendance');
                    _navigateToTakeAttendance(classModel);
                  } else if (value == 'share') {
                    print('🔥 FLUTTER: Calling _shareClassCode');
                    _shareClassCode(classModel);
                  }
                  // TODO: Handle other menu actions
                },
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
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.primaryColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.people, size: 14, color: AppTheme.primaryColor),
                    const SizedBox(width: 4),
                    Text(
                      '${classModel.totalStudents}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppTheme.primaryColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.successColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.trending_up,
                      size: 14,
                      color: AppTheme.successColor,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '87%',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppTheme.successColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              Text(
                'Last session: Today',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppTheme.textSecondary),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
