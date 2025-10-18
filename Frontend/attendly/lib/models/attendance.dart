class AttendanceSession {
  final int id;
  final int classId;
  final String sessionName;
  final DateTime sessionDate;
  final int totalStudents;
  final int presentCount;
  final int absentCount;
  final int createdBy;
  final bool isActive;
  final DateTime createdAt;

  AttendanceSession({
    required this.id,
    required this.classId,
    required this.sessionName,
    required this.sessionDate,
    this.totalStudents = 0,
    this.presentCount = 0,
    this.absentCount = 0,
    required this.createdBy,
    this.isActive = true,
    required this.createdAt,
  });

  double get attendanceRate =>
      totalStudents > 0 ? (presentCount / totalStudents) : 0.0;

  factory AttendanceSession.fromJson(Map<String, dynamic> json) {
    return AttendanceSession(
      id: json['id'] ?? 0,
      classId: json['class_id'] ?? 0,
      sessionName: json['session_name'] ?? '',
      sessionDate: json['session_date'] != null
          ? DateTime.parse(json['session_date'])
          : DateTime.now(),
      totalStudents: json['total_students'] ?? 0,
      presentCount: json['present_count'] ?? 0,
      absentCount: json['absent_count'] ?? 0,
      createdBy: json['created_by'] ?? 0,
      isActive: json['is_active'] ?? true,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'class_id': classId,
      'session_name': sessionName,
      'session_date': sessionDate.toIso8601String(),
      'total_students': totalStudents,
      'present_count': presentCount,
      'absent_count': absentCount,
      'created_by': createdBy,
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

class AttendanceRecord {
  final int id;
  final int sessionId;
  final int studentId;
  final String studentName;
  final String status; // 'present' or 'absent'
  final String? recognitionMethod;
  final double? recognitionConfidence;
  final int markedBy;
  final DateTime markedAt;

  AttendanceRecord({
    required this.id,
    required this.sessionId,
    required this.studentId,
    required this.studentName,
    required this.status,
    this.recognitionMethod,
    this.recognitionConfidence,
    required this.markedBy,
    required this.markedAt,
  });

  bool get isPresent => status == 'present';

  factory AttendanceRecord.fromJson(Map<String, dynamic> json) {
    return AttendanceRecord(
      id: json['id'] ?? 0,
      sessionId: json['session_id'] ?? 0,
      studentId: json['student_id'] ?? 0,
      studentName: json['student_name'] ?? '',
      status: json['status'] ?? 'absent',
      recognitionMethod: json['recognition_method'],
      recognitionConfidence: json['recognition_confidence']?.toDouble(),
      markedBy: json['marked_by'] ?? 0,
      markedAt: json['marked_at'] != null
          ? DateTime.parse(json['marked_at'])
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'session_id': sessionId,
      'student_id': studentId,
      'student_name': studentName,
      'status': status,
      'recognition_method': recognitionMethod,
      'recognition_confidence': recognitionConfidence,
      'marked_by': markedBy,
      'marked_at': markedAt.toIso8601String(),
    };
  }
}
