import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import '../../models/class.dart';
import '../../models/attendance.dart';
import '../../providers/auth_provider.dart';
import '../../services/static_api_service.dart';
import '../../widgets/custom_widgets.dart';

class StudentStatisticsScreen extends StatefulWidget {
  final ClassModel? selectedClass;

  const StudentStatisticsScreen({Key? key, this.selectedClass})
    : super(key: key);

  @override
  State<StudentStatisticsScreen> createState() =>
      _StudentStatisticsScreenState();
}

class _StudentStatisticsScreenState extends State<StudentStatisticsScreen>
    with TickerProviderStateMixin {
  List<ClassModel> _classes = [];
  List<AttendanceRecord> _attendanceRecords = [];
  ClassModel? _selectedClass;
  bool _isLoading = false;

  late TabController _tabController;
  String _selectedPeriod = 'This Month';
  final List<String> _periods = [
    'This Week',
    'This Month',
    'This Semester',
    'All Time',
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _selectedClass = widget.selectedClass;
    _loadClasses();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadClasses() async {
    setState(() => _isLoading = true);
    try {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      final classes = await StaticApiService.getMyClasses(
        auth.user!.id.toString(),
      );
      setState(() {
        _classes = classes;
        if (_selectedClass == null && classes.isNotEmpty) {
          _selectedClass = classes.first;
        }
      });
      if (_selectedClass != null) {
        _loadAttendanceRecords();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error loading classes: $e')));
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadAttendanceRecords() async {
    if (_selectedClass == null) return;

    setState(() => _isLoading = true);
    try {
      final records = await StaticApiService.getStudentAttendance(
        _selectedClass!.id.toString(),
        _selectedPeriod,
      );
      setState(() {
        _attendanceRecords = records;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error loading attendance: $e')));
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Color _getAttendanceColor(double percentage) {
    if (percentage >= 80) return Colors.green;
    if (percentage >= 60) return Colors.orange;
    return Colors.red;
  }

  String _getAttendanceStatus(double percentage) {
    if (percentage >= 80) return 'Excellent';
    if (percentage >= 60) return 'Moderate';
    return 'Critical';
  }

  IconData _getAttendanceIcon(double percentage) {
    if (percentage >= 80) return Icons.trending_up;
    if (percentage >= 60) return Icons.trending_flat;
    return Icons.trending_down;
  }

  double _calculateOverallAttendance() {
    if (_attendanceRecords.isEmpty) return 0.0;

    int totalSessions = 0;
    int presentSessions = 0;

    for (final record in _attendanceRecords) {
      totalSessions++;
      if (record.isPresent) presentSessions++;
    }

    return totalSessions > 0 ? (presentSessions / totalSessions) * 100 : 0.0;
  }

  Map<String, int> _getAttendanceStats() {
    int present = 0, absent = 0, total = 0;

    for (final record in _attendanceRecords) {
      total++;
      if (record.isPresent) {
        present++;
      } else {
        absent++;
      }
    }

    return {'present': present, 'absent': absent, 'total': total};
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'My Attendance',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadAttendanceRecords,
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Overview', icon: Icon(Icons.dashboard)),
            Tab(text: 'Details', icon: Icon(Icons.list)),
            Tab(text: 'Trends', icon: Icon(Icons.analytics)),
          ],
        ),
      ),
      body: Column(
        children: [
          _buildClassSelector(),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildOverviewTab(),
                _buildDetailsTab(),
                _buildTrendsTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildClassSelector() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: DropdownButtonFormField<ClassModel>(
              value: _selectedClass,
              decoration: const InputDecoration(
                labelText: 'Select Class',
                border: OutlineInputBorder(),
              ),
              items: _classes.map((classModel) {
                return DropdownMenuItem(
                  value: classModel,
                  child: Text(classModel.name),
                );
              }).toList(),
              onChanged: (ClassModel? newClass) {
                setState(() {
                  _selectedClass = newClass;
                });
                _loadAttendanceRecords();
              },
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: DropdownButtonFormField<String>(
              value: _selectedPeriod,
              decoration: const InputDecoration(
                labelText: 'Period',
                border: OutlineInputBorder(),
              ),
              items: _periods.map((period) {
                return DropdownMenuItem(value: period, child: Text(period));
              }).toList(),
              onChanged: (String? newPeriod) {
                setState(() {
                  _selectedPeriod = newPeriod ?? 'This Month';
                });
                _loadAttendanceRecords();
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOverviewTab() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_selectedClass == null) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.class_, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text(
              'No classes found',
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
            Text(
              'Join a class to view attendance',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    final overallAttendance = _calculateOverallAttendance();
    final stats = _getAttendanceStats();

    return RefreshIndicator(
      onRefresh: _loadAttendanceRecords,
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        physics: const AlwaysScrollableScrollPhysics(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Overall Attendance Card
            AnimatedCard(
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      _getAttendanceColor(overallAttendance),
                      _getAttendanceColor(overallAttendance).withOpacity(0.7),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Overall Attendance',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 16,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '${overallAttendance.toStringAsFixed(1)}%',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 36,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              _getAttendanceStatus(overallAttendance),
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                        Icon(
                          _getAttendanceIcon(overallAttendance),
                          color: Colors.white,
                          size: 48,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

            // Statistics Cards
            const Text(
              'Statistics',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),

            Row(
              children: [
                Expanded(
                  child: AnimatedCard(
                    child: _buildStatCard(
                      'Present',
                      stats['present']!,
                      Icons.check_circle,
                      Colors.green,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: AnimatedCard(
                    child: _buildStatCard(
                      'Absent',
                      stats['absent']!,
                      Icons.cancel,
                      Colors.red,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: AnimatedCard(
                    child: _buildStatCard(
                      'Total',
                      stats['total']!,
                      Icons.event,
                      Colors.blue,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 24),

            // Class Information
            AnimatedCard(
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: Theme.of(context).colorScheme.primary,
                  child: const Icon(Icons.class_, color: Colors.white),
                ),
                title: Text(
                  _selectedClass!.name,
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                subtitle: Text(_selectedClass!.description),
                trailing: Chip(
                  label: Text(_selectedClass!.joinCode),
                  backgroundColor: Theme.of(
                    context,
                  ).colorScheme.primary.withOpacity(0.1),
                ),
              ),
            ),

            const SizedBox(height: 24),

            // Attendance Guidelines
            const Text(
              'Attendance Guidelines',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),

            AnimatedCard(
              child: Column(
                children: [
                  _buildGuidelineItem(
                    '80% and above',
                    'Excellent attendance',
                    Colors.green,
                    Icons.star,
                  ),
                  const Divider(),
                  _buildGuidelineItem(
                    '60% - 79%',
                    'Moderate attendance',
                    Colors.orange,
                    Icons.warning,
                  ),
                  const Divider(),
                  _buildGuidelineItem(
                    'Below 60%',
                    'Critical - Needs improvement',
                    Colors.red,
                    Icons.error,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard(String title, int value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 8),
          Text(
            '$value',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            title,
            style: TextStyle(fontSize: 12, color: color.withOpacity(0.8)),
          ),
        ],
      ),
    );
  }

  Widget _buildGuidelineItem(
    String range,
    String description,
    Color color,
    IconData icon,
  ) {
    return ListTile(
      leading: Icon(icon, color: color),
      title: Text(range, style: const TextStyle(fontWeight: FontWeight.bold)),
      subtitle: Text(description),
      trailing: Container(
        width: 12,
        height: 12,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      ),
    );
  }

  Widget _buildDetailsTab() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_attendanceRecords.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.event_busy, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text(
              'No attendance records found',
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
            Text(
              'Records will appear once attendance is taken',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadAttendanceRecords,
      child: AnimationLimiter(
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: _attendanceRecords.length,
          itemBuilder: (context, index) {
            final record = _attendanceRecords[index];
            return AnimationConfiguration.staggeredList(
              position: index,
              duration: const Duration(milliseconds: 375),
              child: SlideAnimation(
                verticalOffset: 50.0,
                child: FadeInAnimation(
                  child: _buildAttendanceRecordCard(record),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildAttendanceRecordCard(AttendanceRecord record) {
    final isPresent = record.isPresent;
    final color = isPresent ? Colors.green : Colors.red;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.2),
          child: Icon(isPresent ? Icons.check : Icons.close, color: color),
        ),
        title: Text(
          'Session ${record.sessionId}',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${record.markedAt.day}/${record.markedAt.month}/${record.markedAt.year}',
            ),
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: color.withOpacity(0.3)),
              ),
              child: Text(
                isPresent ? 'Present' : 'Absent',
                style: TextStyle(
                  color: color,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
        trailing: Icon(
          isPresent
              ? Icons.sentiment_very_satisfied
              : Icons.sentiment_very_dissatisfied,
          color: color,
        ),
      ),
    );
  }

  Widget _buildTrendsTab() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Attendance Trends',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),

          // Trend Chart Placeholder
          AnimatedCard(
            child: Container(
              height: 200,
              padding: const EdgeInsets.all(20),
              child: const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.show_chart, size: 48, color: Colors.grey),
                    SizedBox(height: 16),
                    Text(
                      'Attendance Trend Chart',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey,
                      ),
                    ),
                    Text('Coming Soon!', style: TextStyle(color: Colors.grey)),
                  ],
                ),
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Insights
          const Text(
            'Insights',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),

          if (_attendanceRecords.isNotEmpty) ...[
            _buildInsightCard(
              'Most Recent Session',
              _attendanceRecords.last.isPresent ? 'Present' : 'Absent',
              _attendanceRecords.last.isPresent ? Colors.green : Colors.red,
              Icons.event,
            ),
            const SizedBox(height: 12),
            _buildInsightCard(
              'Best Performance',
              'Week of ${_getBestWeek()}',
              Colors.blue,
              Icons.trending_up,
            ),
          ] else
            const Center(
              child: Text(
                'No data available for trends',
                style: TextStyle(color: Colors.grey),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildInsightCard(
    String title,
    String value,
    Color color,
    IconData icon,
  ) {
    return AnimatedCard(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.2),
          child: Icon(icon, color: color),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(value),
        trailing: Icon(Icons.arrow_forward_ios, color: color, size: 16),
      ),
    );
  }

  String _getBestWeek() {
    if (_attendanceRecords.isEmpty) return 'N/A';

    // Simple implementation - return the week of the first present record
    final firstPresent = _attendanceRecords.firstWhere(
      (record) => record.isPresent,
      orElse: () => _attendanceRecords.first,
    );

    return '${firstPresent.markedAt.day}/${firstPresent.markedAt.month}';
  }
}
