import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:intl/intl.dart';
import 'dart:convert';
import 'dart:io';
import '../../providers/auth_provider.dart';
import 'package:provider/provider.dart';

class TakeAttendanceScreen extends StatefulWidget {
  final int classId;
  final String className;

  const TakeAttendanceScreen({
    Key? key,
    required this.classId,
    required this.className,
  }) : super(key: key);

  @override
  State<TakeAttendanceScreen> createState() => _TakeAttendanceScreenState();
}

class _TakeAttendanceScreenState extends State<TakeAttendanceScreen> {
  CameraController? _cameraController;
  List<CameraDescription>? _cameras;
  bool _isCameraInitialized = false;
  bool _isProcessing = false;
  bool _hasProcessedPhoto = false;

  // Student data
  List<Map<String, dynamic>> _allStudents = [];
  Set<int> _selectedStudentIds = {};
  Map<int, double> _recognitionConfidence = {};

  // Recognition stats
  int _totalFacesDetected = 0;
  int _totalRecognized = 0;
  double _recognitionRate = 0.0;

  @override
  void initState() {
    super.initState();
    print(
      '🔥 FLUTTER: TakeAttendanceScreen initState - Class ID: ${widget.classId}, Name: ${widget.className}',
    );
    _initializeCamera();
    _loadClassStudents();
  }

  Future<void> _initializeCamera() async {
    print('🔥 FLUTTER: Initializing camera...');
    try {
      _cameras = await availableCameras();
      print('🔥 FLUTTER: Found ${_cameras?.length ?? 0} cameras');
      if (_cameras != null && _cameras!.isNotEmpty) {
        _cameraController = CameraController(
          _cameras![0],
          ResolutionPreset.high,
          enableAudio: false,
        );

        await _cameraController!.initialize();
        print('🔥 FLUTTER: Camera initialized successfully');

        if (mounted) {
          setState(() {
            _isCameraInitialized = true;
          });
        }
      } else {
        print('🔥 FLUTTER: No cameras found');
      }
    } catch (e) {
      print('🔥 FLUTTER: Error initializing camera: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to initialize camera: $e')),
        );
      }
    }
  }

  Future<void> _loadClassStudents() async {
    print('🔥 FLUTTER: Loading class students for class ID: ${widget.classId}');
    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final response = await authProvider.apiService
          .getClassStudentsWithFacialData(widget.classId);

      print('🔥 FLUTTER: API response: $response');

      if (response['students'] != null) {
        final students = List<Map<String, dynamic>>.from(
          response['students'].map(
            (s) => {
              'student_id': s['student_id'],
              'name': s['name'],
              'email': s['email'],
            },
          ),
        );
        print('🔥 FLUTTER: Loaded ${students.length} students');
        setState(() {
          _allStudents = students;
        });
      } else {
        print('🔥 FLUTTER: No students found in response');
      }
    } catch (e) {
      print('🔥 FLUTTER: Error loading students: $e');
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to load students: $e')));
    }
  }

  Future<void> _captureAndRecognize() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Camera not ready')));
      return;
    }

    setState(() {
      _isProcessing = true;
    });

    try {
      // Capture image
      final XFile photo = await _cameraController!.takePicture();

      // Convert to base64
      final bytes = await File(photo.path).readAsBytes();
      final base64Image = 'data:image/jpeg;base64,${base64Encode(bytes)}';

      // Call recognition API
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final response = await authProvider.apiService.recognizeStudentsFromPhoto(
        classId: widget.classId,
        imageBase64: base64Image,
        recognitionThreshold: 0.6,
      );

      if (response['success'] == true) {
        // Update recognition stats
        setState(() {
          _totalFacesDetected = response['total_faces_detected'] ?? 0;
          _totalRecognized = response['total_recognized'] ?? 0;
          _recognitionRate = (response['recognition_rate'] ?? 0.0).toDouble();
          _hasProcessedPhoto = true;
        });

        // Add recognized students to selection (merge with existing)
        final recognizedStudents =
            response['recognized_students'] as List? ?? [];
        for (var student in recognizedStudents) {
          final studentId = student['student_id'] as int;
          final confidence = (student['confidence'] as num).toDouble();

          setState(() {
            _selectedStudentIds.add(studentId);
            _recognitionConfidence[studentId] = confidence;
          });
        }

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Recognized $_totalRecognized students from $_totalFacesDetected faces',
            ),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 3),
          ),
        );
      } else {
        throw Exception(response['error'] ?? 'Recognition failed');
      }

      // Delete temporary photo file
      await File(photo.path).delete();
    } catch (e) {
      print('Error in recognition: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Recognition failed: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  Future<void> _submitAttendance() async {
    if (_selectedStudentIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No students selected for attendance')),
      );
      return;
    }

    // Show confirmation dialog
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Submit Attendance'),
        content: Text(
          'Mark ${_selectedStudentIds.length} students as present for ${DateFormat('MMM dd, yyyy').format(DateTime.now())}?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Submit'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    setState(() {
      _isProcessing = true;
    });

    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);

      // Create attendance session
      final sessionResponse = await authProvider.apiService.createAttendanceSession(
        classId: widget.classId,
        sessionName:
            'Attendance - ${DateFormat('MMM dd, yyyy').format(DateTime.now())}',
        sessionDate: DateTime.now(),
      );

      final sessionId = sessionResponse['session']['id'];

      // Mark attendance for selected students
      int successCount = 0;
      for (var studentId in _selectedStudentIds) {
        try {
          await authProvider.apiService.markStudentAttendance(
            sessionId: sessionId,
            studentId: studentId,
            status: 'present',
            recognitionConfidence: _recognitionConfidence[studentId],
            recognitionMethod: _recognitionConfidence.containsKey(studentId)
                ? 'ai_face'
                : 'manual',
          );
          successCount++;
        } catch (e) {
          print('Failed to mark attendance for student $studentId: $e');
        }
      }

      // Mark absent for unselected students
      final unselectedStudents = _allStudents
          .where((s) => !_selectedStudentIds.contains(s['student_id']))
          .toList();

      for (var student in unselectedStudents) {
        try {
          await authProvider.apiService.markStudentAttendance(
            sessionId: sessionId,
            studentId: student['student_id'],
            status: 'absent',
            recognitionMethod: 'manual',
          );
        } catch (e) {
          print(
            'Failed to mark absent for student ${student['student_id']}: $e',
          );
        }
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Attendance submitted successfully! $successCount students marked present',
            ),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.pop(context, true); // Return to previous screen
      }
    } catch (e) {
      print('Error submitting attendance: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to submit attendance: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }

  void _toggleStudentSelection(int studentId) {
    setState(() {
      if (_selectedStudentIds.contains(studentId)) {
        _selectedStudentIds.remove(studentId);
      } else {
        _selectedStudentIds.add(studentId);
      }
    });
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.className),
        actions: [
          if (_hasProcessedPhoto)
            TextButton.icon(
              onPressed: _isProcessing ? null : _submitAttendance,
              icon: const Icon(Icons.check, color: Colors.white),
              label: const Text(
                'Submit',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          // Camera Preview Section
          Container(
            height: 300,
            width: double.infinity,
            color: Colors.black,
            child: _isCameraInitialized
                ? CameraPreview(_cameraController!)
                : const Center(
                    child: CircularProgressIndicator(color: Colors.white),
                  ),
          ),

          // Camera Controls
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.grey[900],
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                // Cancel/Back button
                if (!_hasProcessedPhoto)
                  OutlinedButton.icon(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                    label: const Text('Cancel'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Colors.white),
                    ),
                  ),

                // Capture button
                ElevatedButton.icon(
                  onPressed: _isProcessing ? null : _captureAndRecognize,
                  icon: _isProcessing
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.camera_alt),
                  label: Text(
                    _hasProcessedPhoto ? 'Take Another Photo' : 'Capture Photo',
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 24,
                      vertical: 12,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Recognition Stats (if photo processed)
          if (_hasProcessedPhoto)
            Container(
              padding: const EdgeInsets.all(16),
              color: Colors.blue[50],
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _buildStatItem(
                    'Faces Detected',
                    _totalFacesDetected.toString(),
                    Icons.face,
                    Colors.blue,
                  ),
                  _buildStatItem(
                    'Recognized',
                    _totalRecognized.toString(),
                    Icons.check_circle,
                    Colors.green,
                  ),
                  _buildStatItem(
                    'Success Rate',
                    '${_recognitionRate.toStringAsFixed(1)}%',
                    Icons.analytics,
                    Colors.orange,
                  ),
                ],
              ),
            ),

          // Student List Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            color: Colors.grey[200],
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Students (${_selectedStudentIds.length}/${_allStudents.length} selected)',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                if (_allStudents.isNotEmpty)
                  TextButton(
                    onPressed: () {
                      setState(() {
                        if (_selectedStudentIds.length == _allStudents.length) {
                          _selectedStudentIds.clear();
                        } else {
                          _selectedStudentIds = _allStudents
                              .map((s) => s['student_id'] as int)
                              .toSet();
                        }
                      });
                    },
                    child: Text(
                      _selectedStudentIds.length == _allStudents.length
                          ? 'Deselect All'
                          : 'Select All',
                    ),
                  ),
              ],
            ),
          ),

          // Student List
          Expanded(
            child: _allStudents.isEmpty
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
                          'No students with facial data',
                          style: TextStyle(color: Colors.grey, fontSize: 16),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    itemCount: _allStudents.length,
                    itemBuilder: (context, index) {
                      final student = _allStudents[index];
                      final studentId = student['student_id'] as int;
                      final isSelected = _selectedStudentIds.contains(
                        studentId,
                      );
                      final confidence = _recognitionConfidence[studentId];
                      final wasRecognized = confidence != null;

                      return Card(
                        margin: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        elevation: isSelected ? 3 : 1,
                        color: isSelected ? Colors.green[50] : Colors.white,
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: isSelected
                                ? Colors.green
                                : Colors.grey[300],
                            child: Icon(
                              isSelected ? Icons.check : Icons.person,
                              color: isSelected
                                  ? Colors.white
                                  : Colors.grey[600],
                            ),
                          ),
                          title: Text(
                            student['name'],
                            style: TextStyle(
                              fontWeight: isSelected
                                  ? FontWeight.bold
                                  : FontWeight.normal,
                            ),
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(student['email']),
                              if (wasRecognized)
                                Container(
                                  margin: const EdgeInsets.only(top: 4),
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 8,
                                    vertical: 2,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.blue[100],
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Text(
                                    'AI Recognized (${(confidence * 100).toStringAsFixed(0)}% confidence)',
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: Colors.blue[900],
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                          trailing: Checkbox(
                            value: isSelected,
                            onChanged: (value) {
                              _toggleStudentSelection(studentId);
                            },
                            activeColor: Colors.green,
                          ),
                          onTap: () => _toggleStudentSelection(studentId),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Column(
      children: [
        Icon(icon, color: color, size: 28),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
      ],
    );
  }
}
