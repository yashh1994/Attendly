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
    print('🔥 FLUTTER: URL: $baseUrl/api/auth/signup');
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
        Uri.parse('$baseUrl/api/auth/signup'),
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
      Uri.parse('$baseUrl/api/auth/login'),
      headers: headers,
      body: jsonEncode({'email': email, 'password': password}),
    );

    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> updateUserRole(String role) async {
    print('🔥 FLUTTER: Starting updateUserRole');
    print('🔥 FLUTTER: Role: $role');
    print('🔥 FLUTTER: URL: $baseUrl/api/auth/update-role');
    print('🔥 FLUTTER: Headers: $headers');

    final requestBody = {'role': role};
    print('🔥 FLUTTER: Request body: $requestBody');

    try {
      final response = await http.put(
        Uri.parse('$baseUrl/api/auth/update-role'),
        headers: headers,
        body: jsonEncode(requestBody),
      );

      print('🔥 FLUTTER: UpdateRole response status: ${response.statusCode}');
      print('🔥 FLUTTER: UpdateRole response headers: ${response.headers}');
      print('🔥 FLUTTER: UpdateRole response body: ${response.body}');

      return _handleResponse(response);
    } catch (e) {
      print('🔥 FLUTTER: Exception in updateUserRole: $e');
      rethrow;
    }
  }

  Future<void> logout() async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/auth/logout'),
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
    print('🔥 FLUTTER: Creating class: $name');
    print('🔥 FLUTTER: URL: $baseUrl/api/classes/create');

    final requestBody = {'name': name, 'description': description};
    print('🔥 FLUTTER: Request body: $requestBody');

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/classes/create'),
        headers: headers,
        body: jsonEncode(requestBody),
      );

      print('🔥 FLUTTER: CreateClass response status: ${response.statusCode}');
      print('🔥 FLUTTER: CreateClass response body: ${response.body}');

      return _handleResponse(response);
    } catch (e) {
      print('🔥 FLUTTER: Exception in createClass: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> joinClass(String joinCode) async {
    print('🔥 FLUTTER: Joining class with code: $joinCode');
    print('🔥 FLUTTER: URL: $baseUrl/api/classes/join');

    final requestBody = {'join_code': joinCode};
    print('🔥 FLUTTER: Request body: $requestBody');

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/classes/join'),
        headers: headers,
        body: jsonEncode(requestBody),
      );

      print('🔥 FLUTTER: JoinClass response status: ${response.statusCode}');
      print('🔥 FLUTTER: JoinClass response body: ${response.body}');

      return _handleResponse(response);
    } catch (e) {
      print('🔥 FLUTTER: Exception in joinClass: $e');
      rethrow;
    }
  }

  Future<List<ClassModel>> getMyClasses() async {
    print('🔥 FLUTTER: Getting my classes');
    print('🔥 FLUTTER: URL: $baseUrl/api/classes/my-classes');
    print('🔥 FLUTTER: Headers: $headers');

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/classes/my-classes'),
        headers: headers,
      );

      print('🔥 FLUTTER: GetMyClasses response status: ${response.statusCode}');
      print('🔥 FLUTTER: GetMyClasses response body: ${response.body}');

      final data = _handleResponse(response);
      final classes = data['classes'] as List;
      return classes.map((json) => ClassModel.fromJson(json)).toList();
    } catch (e) {
      print('🔥 FLUTTER: Exception in getMyClasses: $e');
      rethrow;
    }
  }

  Future<ClassModel> getClassDetail(int classId) async {
    print('🔥 FLUTTER: Getting class detail for ID: $classId');
    print('🔥 FLUTTER: URL: $baseUrl/api/classes/$classId');

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/classes/$classId'),
        headers: headers,
      );

      print(
        '🔥 FLUTTER: GetClassDetail response status: ${response.statusCode}',
      );
      print('🔥 FLUTTER: GetClassDetail response body: ${response.body}');

      final data = _handleResponse(response);
      return ClassModel.fromJson(data['class']);
    } catch (e) {
      print('🔥 FLUTTER: Exception in getClassDetail: $e');
      rethrow;
    }
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
