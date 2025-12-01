import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import 'package:provider/provider.dart';
import '../models/class.dart';
import '../models/attendance.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';
import '../widgets/custom_widgets.dart';
import '../utils/app_theme.dart';
import 'teacher/take_attendance_screen.dart';

class ClassDetailScreen extends StatefulWidget {
  final ClassModel classModel;

  const ClassDetailScreen({Key? key, required this.classModel})
    : super(key: key);

  @override
  State<ClassDetailScreen> createState() => _ClassDetailScreenState();
}

class _ClassDetailScreenState extends State<ClassDetailScreen>
    with TickerProviderStateMixin {
  late TabController _tabController;
  final ApiService _apiService = ApiService();
  DateTime _selectedDay = DateTime.now();
  DateTime _focusedDay = DateTime.now();

  List<AttendanceSession> _attendanceSessions = [];
  List<Map<String, dynamic>> _students = [];
  bool _isLoadingStudents = false;
  bool _isLoadingSessions = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadAttendanceSessions();
    _loadStudents();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadAttendanceSessions() async {
    setState(() {
      _isLoadingSessions = true;
      _error = null;
    });

    try {
      // Get token from auth provider and set in API service
      final authProvider = context.read<AuthProvider>();
      if (authProvider.token != null) {
        _apiService.setToken(authProvider.token);
      }

      print(
        '🔥 FLUTTER: Loading attendance sessions for class ${widget.classModel.id}',
      );
      final sessions = await _apiService.getClassSessions(widget.classModel.id);

      setState(() {
        _attendanceSessions = sessions;
        _isLoadingSessions = false;
      });

      print('🔥 FLUTTER: Loaded ${sessions.length} attendance sessions');
    } catch (e) {
      print('🔥 FLUTTER: Error loading attendance sessions: $e');
      setState(() {
        _error = e.toString();
        _isLoadingSessions = false;
        _attendanceSessions = [];
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Failed to load attendance sessions: ${e.toString()}',
            ),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  Future<void> _loadStudents() async {
    setState(() {
      _isLoadingStudents = true;
      _error = null;
    });

    try {
      // Get token from auth provider and set in API service
      final authProvider = context.read<AuthProvider>();
      if (authProvider.token != null) {
        _apiService.setToken(authProvider.token);
      }

      print('🔥 FLUTTER: Loading students for class ${widget.classModel.id}');
      final students = await _apiService.getClassStudents(widget.classModel.id);

      setState(() {
        _students = students;
        _isLoadingStudents = false;
      });

      print('🔥 FLUTTER: Loaded ${students.length} students');
    } catch (e) {
      print('🔥 FLUTTER: Error loading students: $e');
      setState(() {
        _error = e.toString();
        _isLoadingStudents = false;
        _students = [];
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to load students: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  List<AttendanceSession> _getSessionsForDay(DateTime day) {
    return _attendanceSessions.where((session) {
      return isSameDay(session.sessionDate, day);
    }).toList();
  }

  Color _getAttendanceColor(DateTime day) {
    final sessions = _getSessionsForDay(day);
    if (sessions.isEmpty) return Colors.grey.shade300;

    final session = sessions.first;
    final attendanceRate = session.presentCount / session.totalStudents;

    if (attendanceRate >= 0.8) return Colors.green;
    if (attendanceRate >= 0.6) return Colors.yellow.shade700;
    return Colors.red;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.classModel.name,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.share),
            onPressed: () => _shareClass(),
          ),
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () => _editClass(),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Calendar', icon: Icon(Icons.calendar_today)),
            Tab(text: 'Students', icon: Icon(Icons.people)),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [_buildCalendarTab(), _buildStudentsTab()],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _takeAttendanceForDay(DateTime.now()),
        icon: const Icon(Icons.camera_alt),
        label: const Text('Take Attendance'),
        backgroundColor: AppTheme.primaryColor,
      ),
    );
  }

  Widget _buildCalendarTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Card(
            child: Column(
              children: [
                TableCalendar<AttendanceSession>(
                  firstDay: DateTime.utc(2020, 1, 1),
                  lastDay: DateTime.utc(2030, 12, 31),
                  focusedDay: _focusedDay,
                  selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
                  eventLoader: _getSessionsForDay,
                  startingDayOfWeek: StartingDayOfWeek.monday,
                  calendarStyle: CalendarStyle(
                    outsideDaysVisible: false,
                    weekendTextStyle: const TextStyle(color: Colors.grey),
                    holidayTextStyle: const TextStyle(color: Colors.red),
                    markerDecoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primary,
                      shape: BoxShape.circle,
                    ),
                  ),
                  headerStyle: const HeaderStyle(
                    formatButtonVisible: false,
                    titleCentered: true,
                    leftChevronIcon: Icon(Icons.chevron_left),
                    rightChevronIcon: Icon(Icons.chevron_right),
                  ),
                  onDaySelected: (selectedDay, focusedDay) {
                    setState(() {
                      _selectedDay = selectedDay;
                      _focusedDay = focusedDay;
                    });
                  },
                  calendarBuilders: CalendarBuilders(
                    markerBuilder: (context, day, events) {
                      if (events.isNotEmpty) {
                        return Positioned(
                          bottom: 1,
                          child: Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: _getAttendanceColor(day),
                              shape: BoxShape.circle,
                            ),
                          ),
                        );
                      }
                      return null;
                    },
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _buildSelectedDayDetailsScrollable(),
        ],
      ),
    );
  }

  Widget _buildSelectedDayDetailsScrollable() {
    final sessions = _getSessionsForDay(_selectedDay);

    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(Icons.event, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  'Sessions for ${_selectedDay.day}/${_selectedDay.month}/${_selectedDay.year}',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
          const Divider(),
          if (sessions.isEmpty)
            Container(
              height: 200,
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.event_busy, size: 64, color: Colors.grey),
                    const SizedBox(height: 16),
                    const Text(
                      'No attendance taken for this day',
                      style: TextStyle(fontSize: 16, color: Colors.grey),
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton.icon(
                      onPressed: () => _takeAttendanceForDay(_selectedDay),
                      icon: const Icon(Icons.camera_alt),
                      label: const Text('Take Attendance'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryColor,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 24,
                          vertical: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            )
          else
            ...sessions.asMap().entries.map((entry) {
              final index = entry.key;
              final session = entry.value;
              return Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 4,
                ),
                child: AnimationConfiguration.staggeredList(
                  position: index,
                  duration: const Duration(milliseconds: 375),
                  child: SlideAnimation(
                    verticalOffset: 50.0,
                    child: FadeInAnimation(child: _buildSessionCard(session)),
                  ),
                ),
              );
            }).toList(),
          const SizedBox(height: 16), // Bottom padding for scrolling
        ],
      ),
    );
  }

  Widget _buildSessionCard(AttendanceSession session) {
    final attendanceRate = session.presentCount / session.totalStudents;
    final percentage = (attendanceRate * 100).round();

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getAttendanceColor(session.sessionDate),
          child: Text(
            '$percentage%',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ),
        title: Text(
          'Session ${session.id}',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Text(
          '${session.presentCount}/${session.totalStudents} present',
        ),
        trailing: IconButton(
          icon: const Icon(Icons.visibility),
          onPressed: () => _viewSessionDetails(session),
        ),
      ),
    );
  }

  void _takeAttendanceForDay(DateTime selectedDay) async {
    print(
      '🔥 FLUTTER: Navigating to Take Attendance screen for class ${widget.classModel.id}',
    );

    // Navigate to photo attendance screen
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => TakeAttendanceScreen(
          classId: widget.classModel.id,
          className: widget.classModel.name,
        ),
      ),
    );

    // Refresh attendance data if attendance was submitted
    if (result == true) {
      print('🔥 FLUTTER: Attendance submitted, refreshing data');
      _loadAttendanceSessions();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Attendance recorded successfully!'),
            backgroundColor: Colors.green,
            duration: Duration(seconds: 2),
          ),
        );
      }
    }
  }

  Future<void> _copyJoinCode() async {
    try {
      await Clipboard.setData(ClipboardData(text: widget.classModel.joinCode));

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.check, color: Colors.white),
                const SizedBox(width: 8),
                Text('Join code "${widget.classModel.joinCode}" copied!'),
              ],
            ),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to copy join code: $e'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  Widget _buildStudentsTab() {
    if (_isLoadingStudents) {
      return const Center(child: CircularProgressIndicator());
    }

    return RefreshIndicator(
      onRefresh: _loadStudents,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          const Icon(Icons.people, size: 32),
                          const SizedBox(height: 8),
                          Text(
                            '${_students.length}',
                            style: const TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const Text('Total Students'),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: InkWell(
                    onTap: () => _copyJoinCode(),
                    borderRadius: BorderRadius.circular(12),
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            const Icon(
                              Icons.copy,
                              size: 32,
                              color: Colors.green,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              widget.classModel.joinCode,
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const Text('Join Code'),
                            const SizedBox(height: 4),
                            const Text(
                              'Tap to copy',
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.grey,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: _students.isEmpty
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.people_outline,
                          size: 64,
                          color: Colors.grey,
                        ),
                        SizedBox(height: 16),
                        Text(
                          'No students enrolled yet',
                          style: TextStyle(fontSize: 16, color: Colors.grey),
                        ),
                      ],
                    ),
                  )
                : AnimationLimiter(
                    child: ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: _students.length,
                      itemBuilder: (context, index) {
                        final student = _students[index];
                        return AnimationConfiguration.staggeredList(
                          position: index,
                          duration: const Duration(milliseconds: 375),
                          child: SlideAnimation(
                            verticalOffset: 50.0,
                            child: FadeInAnimation(
                              child: _buildStudentCard(student, index),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildStudentCard(dynamic student, int index) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Theme.of(context).colorScheme.primary,
          child: Text(
            student['name'][0].toString().toUpperCase(),
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        title: Text(
          student['name'] ?? 'Unknown',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Text(student['email'] ?? ''),
        trailing: PopupMenuButton(
          itemBuilder: (context) => [
            const PopupMenuItem(
              value: 'view',
              child: Row(
                children: [
                  Icon(Icons.visibility),
                  SizedBox(width: 8),
                  Text('View Details'),
                ],
              ),
            ),
            const PopupMenuItem(
              value: 'remove',
              child: Row(
                children: [
                  Icon(Icons.remove_circle, color: Colors.red),
                  SizedBox(width: 8),
                  Text('Remove Student'),
                ],
              ),
            ),
          ],
          onSelected: (value) {
            if (value == 'view') {
              _viewStudentDetails(student);
            } else if (value == 'remove') {
              _removeStudent(student);
            }
          },
        ),
      ),
    );
  }

  void _shareClass() {
    // Copy join code and show sharing options
    _copyJoinCode();
  }

  void _editClass() {
    // TODO: Implement class editing
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Class'),
        content: const Text('Class editing feature coming soon!'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _viewSessionDetails(AttendanceSession session) {
    // TODO: Implement session details view
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Session ${session.id}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Date: ${session.sessionDate.day}/${session.sessionDate.month}/${session.sessionDate.year}',
            ),
            Text('Present: ${session.presentCount}/${session.totalStudents}'),
            Text(
              'Attendance: ${((session.presentCount / session.totalStudents) * 100).round()}%',
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _viewStudentDetails(dynamic student) {
    // TODO: Implement student details view
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(student['name']),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Email: ${student['email']}'),
            Text('ID: ${student['id']}'),
            const SizedBox(height: 16),
            const Text('Student details view coming soon!'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _removeStudent(dynamic student) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Student'),
        content: Text(
          'Are you sure you want to remove ${student['name']} from this class?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              // TODO: Implement student removal
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Student removal feature coming soon!'),
                ),
              );
            },
            child: const Text('Remove', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}
