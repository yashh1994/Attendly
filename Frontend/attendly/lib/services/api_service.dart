import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/user.dart';
import '../models/class.dart';
import '../models/attendance.dart';

class ApiService {
  static const String baseUrl = 'http://localhost:5000';

  String? _token;

  void setToken(String? token) {
    _token = token;
  }

  Map<String, String> get headers {
    final headers = {'Content-Type': 'application/json'};

    if (_token != null) {
      headers['Authorization'] = 'Bearer $_token';
    }

    return headers;
  }

  // Helper method to handle API responses
  Map<String, dynamic> _handleResponse(http.Response response) {
    final body = response.body;
    print('🔥 FLUTTER: _handleResponse - Status: ${response.statusCode}');
    print('🔥 FLUTTER: _handleResponse - Body: $body');

    final data = jsonDecode(body);
    print('🔥 FLUTTER: _handleResponse - Parsed data: $data');

    if (response.statusCode >= 200 && response.statusCode < 300) {
      print('🔥 FLUTTER: _handleResponse - Success response');
      return data;
    } else {
      print('🔥 FLUTTER: _handleResponse - Error response');
      throw Exception(data['error'] ?? 'Unknown error occurred');
    }
  }

  // Authentication endpoints
  Future<Map<String, dynamic>> register({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
  }) async {
    print('🔥 FLUTTER: Starting registration');
    print('🔥 FLUTTER: URL: $baseUrl/auth/signup');
    print('🔥 FLUTTER: Headers: $headers');
    print(
      '🔥 FLUTTER: Data: firstName=$firstName, lastName=$lastName, email=$email',
    );

    final requestBody = {
      'first_name': firstName,
      'last_name': lastName,
      'email': email,
      'password': password,
      'role': 'student', // Default role, will be updated later
    };

    print('🔥 FLUTTER: Request body: $requestBody');

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/signup'),
        headers: headers,
        body: jsonEncode(requestBody),
      );

      print('🔥 FLUTTER: Response status: ${response.statusCode}');
      print('🔥 FLUTTER: Response headers: ${response.headers}');
      print('🔥 FLUTTER: Response body: ${response.body}');

      return _handleResponse(response);
    } catch (e) {
      print('🔥 FLUTTER: Exception in register: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: headers,
      body: jsonEncode({'email': email, 'password': password}),
    );

    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> updateUserRole(String role) async {
    final response = await http.put(
      Uri.parse('$baseUrl/auth/update-role'),
      headers: headers,
      body: jsonEncode({'role': role}),
    );

    return _handleResponse(response);
  }

  Future<void> logout() async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/logout'),
      headers: headers,
    );

    _handleResponse(response);
  }

  // Face data endpoints
  Future<Map<String, dynamic>> uploadFaceData(List<String> images) async {
    final response = await http.post(
      Uri.parse('$baseUrl/face-data/upload'),
      headers: headers,
      body: jsonEncode({'images': images}),
    );

    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> getFaceData() async {
    final response = await http.get(
      Uri.parse('$baseUrl/face-data/my-data'),
      headers: headers,
    );

    return _handleResponse(response);
  }

  // Class endpoints
  Future<Map<String, dynamic>> createClass({
    required String name,
    required String description,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/classes/create'),
      headers: headers,
      body: jsonEncode({'name': name, 'description': description}),
    );

    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> joinClass(String joinCode) async {
    final response = await http.post(
      Uri.parse('$baseUrl/classes/join'),
      headers: headers,
      body: jsonEncode({'join_code': joinCode}),
    );

    return _handleResponse(response);
  }

  Future<List<ClassModel>> getMyClasses() async {
    final response = await http.get(
      Uri.parse('$baseUrl/classes/my-classes'),
      headers: headers,
    );

    final data = _handleResponse(response);
    final classes = data['classes'] as List;
    return classes.map((json) => ClassModel.fromJson(json)).toList();
  }

  Future<ClassModel> getClassDetail(int classId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/classes/$classId'),
      headers: headers,
    );

    final data = _handleResponse(response);
    return ClassModel.fromJson(data['class']);
  }

  // Attendance endpoints
  Future<Map<String, dynamic>> recognizeFaces({
    required int classId,
    required List<String> images,
    double tolerance = 0.6,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/attendance/recognize-faces'),
      headers: headers,
      body: jsonEncode({
        'class_id': classId,
        'images': images,
        'tolerance': tolerance,
      }),
    );

    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> createAttendanceSession({
    required int classId,
    required String sessionName,
    required DateTime sessionDate,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/attendance/create-session'),
      headers: headers,
      body: jsonEncode({
        'class_id': classId,
        'session_name': sessionName,
        'session_date': sessionDate.toIso8601String().split('T')[0],
      }),
    );

    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> markAttendance({
    required int sessionId,
    required List<int> studentIds,
    String recognitionMethod = 'face_recognition',
    Map<String, double>? confidenceScores,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/attendance/mark-attendance'),
      headers: headers,
      body: jsonEncode({
        'session_id': sessionId,
        'student_ids': studentIds,
        'recognition_method': recognitionMethod,
        'confidence_scores': confidenceScores ?? {},
      }),
    );

    return _handleResponse(response);
  }

  Future<List<AttendanceSession>> getClassSessions(int classId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/attendance/sessions/$classId'),
      headers: headers,
    );

    final data = _handleResponse(response);
    final sessions = data['sessions'] as List;
    return sessions.map((json) => AttendanceSession.fromJson(json)).toList();
  }

  Future<Map<String, dynamic>> getSessionAttendance(int sessionId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/attendance/session/$sessionId/records'),
      headers: headers,
    );

    return _handleResponse(response);
  }

  // Student endpoints
  Future<List<User>> getClassStudents(int classId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/classes/$classId/students'),
      headers: headers,
    );

    final data = _handleResponse(response);
    final students = data['students'] as List;
    return students.map((json) => User.fromJson(json)).toList();
  }

  Future<Map<String, dynamic>> getStudentAttendanceStats(
    int studentId,
    int classId,
  ) async {
    final response = await http.get(
      Uri.parse(
        '$baseUrl/students/$studentId/attendance-stats?class_id=$classId',
      ),
      headers: headers,
    );

    return _handleResponse(response);
  }

  Future<List<AttendanceRecord>> getStudentAttendanceRecords({
    required String classId,
    required String period,
  }) async {
    final response = await http.get(
      Uri.parse(
        '$baseUrl/attendance/student-records?class_id=$classId&period=$period',
      ),
      headers: headers,
    );

    final data = _handleResponse(response);
    final records = data['records'] as List;
    return records.map((json) => AttendanceRecord.fromJson(json)).toList();
  }
}
