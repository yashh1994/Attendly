import 'package:dio/dio.dart';
import '../models/class.dart';
import '../models/attendance.dart';
import '../utils/config.dart';

class StaticApiService {
  static String get baseUrl => AppConfig.backendBaseUrl;
  static final Dio _dio = Dio(
    BaseOptions(
      baseUrl: baseUrl,
      headers: {'Content-Type': 'application/json'},
    ),
  );

  // Set authentication token
  static void setToken(String? token) {
    if (token != null) {
      _dio.options.headers['Authorization'] = 'Bearer $token';
    } else {
      _dio.options.headers.remove('Authorization');
    }
  }

  // Get attendance sessions for a class
  static Future<List<AttendanceSession>> getAttendanceSessions(
    String classId,
  ) async {
    try {
      final response = await _dio.get('/attendance/sessions/$classId');

      final List<dynamic> sessionsJson = response.data['sessions'] ?? [];
      return sessionsJson
          .map((json) => AttendanceSession.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to load attendance sessions: $e');
    }
  }

  // Get students in a class
  static Future<List<dynamic>> getClassStudents(String classId) async {
    try {
      final response = await _dio.get('/classes/$classId/students');

      final List<dynamic> studentsJson = response.data['students'] ?? [];
      return studentsJson
          .map(
            (student) => {
              'id': student['id'],
              'name':
                  student['name'] ??
                  '${student['first_name']} ${student['last_name']}',
              'email': student['email'],
            },
          )
          .toList();
    } catch (e) {
      throw Exception('Failed to load class students: $e');
    }
  }

  // Recognize faces in an image
  static Future<Map<String, dynamic>> recognizeFaces(
    Map<String, dynamic> data,
  ) async {
    try {
      final response = await _dio.post(
        '/attendance/recognize-faces',
        data: data,
      );

      return response.data ??
          {'recognized_students': [], 'confidence_scores': {}};
    } catch (e) {
      throw Exception('Failed to recognize faces: $e');
    }
  }

  // Mark attendance for students
  static Future<void> markAttendance(Map<String, dynamic> data) async {
    try {
      await _dio.post('/attendance/mark-attendance', data: data);
    } catch (e) {
      throw Exception('Failed to mark attendance: $e');
    }
  }

  // Get student attendance records
  static Future<List<AttendanceRecord>> getStudentAttendance(
    String classId,
    String period,
  ) async {
    try {
      final response = await _dio.get(
        '/attendance/student-records',
        queryParameters: {'class_id': classId, 'period': period},
      );

      final List<dynamic> recordsJson = response.data['records'] ?? [];
      return recordsJson
          .map((json) => AttendanceRecord.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to load attendance records: $e');
    }
  }

  // Get user's classes
  static Future<List<ClassModel>> getMyClasses(String userId) async {
    try {
      final response = await _dio.get(
        '/classes/my-classes',
        queryParameters: {'user_id': userId},
      );

      final List<dynamic> classesJson = response.data['classes'] ?? [];
      return classesJson.map((json) => ClassModel.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Failed to load classes: $e');
    }
  }

  // Create a new class
  static Future<ClassModel> createClass(Map<String, dynamic> classData) async {
    try {
      final response = await _dio.post('/classes/create', data: classData);

      return ClassModel.fromJson(response.data['class']);
    } catch (e) {
      throw Exception('Failed to create class: $e');
    }
  }

  // Join a class
  static Future<void> joinClass(String joinCode, String userId) async {
    try {
      await _dio.post(
        '/classes/join',
        data: {'join_code': joinCode, 'user_id': userId},
      );
    } catch (e) {
      throw Exception('Failed to join class: $e');
    }
  }

  // Get class statistics
  static Future<Map<String, dynamic>> getClassStatistics(String classId) async {
    try {
      final response = await _dio.get('/classes/$classId/statistics');

      return response.data ??
          {
            'total_sessions': 0,
            'total_students': 0,
            'average_attendance': 0.0,
            'attendance_trend': [],
          };
    } catch (e) {
      throw Exception('Failed to load class statistics: $e');
    }
  }
}
