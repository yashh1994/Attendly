class ClassModel {
  final int id;
  final String name;
  final String description;
  final String joinCode;
  final int teacherId;
  final String teacherName;
  final int totalStudents;
  final bool isActive;
  final DateTime createdAt;
  final DateTime? updatedAt;

  ClassModel({
    required this.id,
    required this.name,
    required this.description,
    required this.joinCode,
    required this.teacherId,
    required this.teacherName,
    this.totalStudents = 0,
    this.isActive = true,
    required this.createdAt,
    this.updatedAt,
  });

  factory ClassModel.fromJson(Map<String, dynamic> json) {
    return ClassModel(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      joinCode: json['join_code'] ?? '',
      teacherId: json['teacher_id'] ?? 0,
      teacherName: json['teacher_name'] ?? '',
      totalStudents: json['total_students'] ?? 0,
      isActive: json['is_active'] ?? true,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'join_code': joinCode,
      'teacher_id': teacherId,
      'teacher_name': teacherName,
      'total_students': totalStudents,
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }

  @override
  String toString() {
    return 'ClassModel(id: $id, name: $name, students: $totalStudents)';
  }
}
