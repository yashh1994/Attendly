import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/custom_widgets.dart';
import '../../utils/app_theme.dart';
import '../../models/class.dart';

class TeacherHomeScreen extends StatefulWidget {
  const TeacherHomeScreen({super.key});

  @override
  State<TeacherHomeScreen> createState() => _TeacherHomeScreenState();
}

class _TeacherHomeScreenState extends State<TeacherHomeScreen> {
  final _classNameController = TextEditingController();
  final _descriptionController = TextEditingController();
  List<ClassModel> _createdClasses = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadCreatedClasses();
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
    });

    // TODO: Load created classes from API
    await Future.delayed(const Duration(seconds: 1));

    setState(() {
      _isLoading = false;
      // Mock data for now
      _createdClasses = [
        ClassModel(
          id: 1,
          name: 'Computer Science 101',
          description: 'Introduction to Programming',
          joinCode: 'CS101ABC',
          teacherId: 1,
          teacherName: 'Dr. Smith',
          totalStudents: 25,
          createdAt: DateTime.now().subtract(const Duration(days: 30)),
        ),
        ClassModel(
          id: 2,
          name: 'Data Structures',
          description: 'Advanced Data Structures and Algorithms',
          joinCode: 'DS202XYZ',
          teacherId: 1,
          teacherName: 'Dr. Smith',
          totalStudents: 30,
          createdAt: DateTime.now().subtract(const Duration(days: 15)),
        ),
      ];
    });
  }

  Future<void> _createClass() async {
    final className = _classNameController.text.trim();

    if (className.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a class name'),
          backgroundColor: AppTheme.errorColor,
        ),
      );
      return;
    }

    // TODO: Implement create class API call
    Navigator.pop(context);
    _classNameController.clear();
    _descriptionController.clear();

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Class created successfully!'),
        backgroundColor: AppTheme.successColor,
      ),
    );

    _loadCreatedClasses();
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
              // TODO: Show profile
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadCreatedClasses,
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
                                '${_createdClasses.length}',
                                Icons.school,
                                AppTheme.primaryColor,
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: _buildStatCard(
                                'Total Students',
                                '${_createdClasses.fold<int>(0, (sum, c) => sum + c.totalStudents)}',
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
                                '3',
                                Icons.today,
                                AppTheme.warningColor,
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: _buildStatCard(
                                'Avg. Attendance',
                                '87%',
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
        // TODO: Navigate to class detail screen with calendar and student list
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
                  // TODO: Handle menu actions
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
