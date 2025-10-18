import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'dart:io';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import '../../models/class.dart';
import '../../services/static_api_service.dart';
import '../../widgets/custom_widgets.dart';

class AttendanceCaptureScreen extends StatefulWidget {
  final ClassModel classModel;
  final VoidCallback? onAttendanceTaken;

  const AttendanceCaptureScreen({
    Key? key,
    required this.classModel,
    this.onAttendanceTaken,
  }) : super(key: key);

  @override
  State<AttendanceCaptureScreen> createState() =>
      _AttendanceCaptureScreenState();
}

class _AttendanceCaptureScreenState extends State<AttendanceCaptureScreen>
    with TickerProviderStateMixin {
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  bool _isCameraInitialized = false;
  bool _isProcessing = false;
  bool _hasPhoto = false;
  String? _capturedImagePath;

  List<dynamic> _recognizedStudents = [];
  List<dynamic> _allStudents = [];
  List<String> _presentStudentIds = [];

  late AnimationController _cameraAnimationController;
  late AnimationController _processingAnimationController;
  late Animation<double> _cameraScaleAnimation;
  late Animation<double> _processingRotation;

  @override
  void initState() {
    super.initState();
    _initAnimations();
    _initCamera();
    _loadStudents();
  }

  void _initAnimations() {
    _cameraAnimationController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );

    _processingAnimationController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    );

    _cameraScaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(
      CurvedAnimation(
        parent: _cameraAnimationController,
        curve: Curves.easeInOut,
      ),
    );

    _processingRotation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _processingAnimationController,
        curve: Curves.linear,
      ),
    );
  }

  Future<void> _initCamera() async {
    try {
      _cameras = await availableCameras();

      // Find front camera, fallback to first available camera
      CameraDescription selectedCamera = _cameras!.first;
      for (var camera in _cameras!) {
        if (camera.lensDirection == CameraLensDirection.front) {
          selectedCamera = camera;
          break;
        }
      }

      _controller = CameraController(
        selectedCamera,
        ResolutionPreset.medium,
        enableAudio: false,
      );

      await _controller!.initialize();

      if (mounted) {
        setState(() {
          _isCameraInitialized = true;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error initializing camera: $e')),
        );
      }
    }
  }

  Future<void> _loadStudents() async {
    try {
      final students = await StaticApiService.getClassStudents(
        widget.classModel.id.toString(),
      );
      setState(() {
        _allStudents = students;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error loading students: $e')));
      }
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    _cameraAnimationController.dispose();
    _processingAnimationController.dispose();
    super.dispose();
  }

  Future<void> _capturePhoto() async {
    if (!_controller!.value.isInitialized) return;

    _cameraAnimationController.forward().then((_) {
      _cameraAnimationController.reverse();
    });

    try {
      final XFile photo = await _controller!.takePicture();
      setState(() {
        _hasPhoto = true;
        _capturedImagePath = photo.path;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error capturing photo: $e')));
      }
    }
  }

  Future<void> _markAttendance() async {
    try {
      await StaticApiService.markAttendance({
        'class_id': widget.classModel.id.toString(),
        'present_student_ids': _presentStudentIds,
        'date': DateTime.now().toIso8601String(),
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Attendance marked successfully!'),
            backgroundColor: Colors.green,
          ),
        );

        // Call callback to refresh data
        widget.onAttendanceTaken?.call();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error marking attendance: $e')));
      }
    }
  }

  void _retakePhoto() {
    setState(() {
      _hasPhoto = false;
      _capturedImagePath = null;
      _recognizedStudents.clear();
      _presentStudentIds.clear();
    });
  }

  void _toggleStudentAttendance(String studentId) {
    setState(() {
      if (_presentStudentIds.contains(studentId)) {
        _presentStudentIds.remove(studentId);
      } else {
        _presentStudentIds.add(studentId);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Take Attendance',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          if (_hasPhoto && !_isProcessing)
            IconButton(
              icon: const Icon(Icons.check),
              onPressed: _finalizeAttendance,
            ),
        ],
      ),
      body: Column(
        children: [
          // Camera/Photo Section
          Expanded(flex: _hasPhoto ? 1 : 2, child: _buildCameraSection()),

          // Controls Section
          if (!_hasPhoto) _buildCameraControls(),

          // Processing/Results Section
          if (_hasPhoto)
            Expanded(
              flex: 2,
              child: _isProcessing
                  ? _buildProcessingSection()
                  : _buildResultsSection(),
            ),
        ],
      ),
    );
  }

  Widget _buildCameraSection() {
    return Container(
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 10,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: AnimatedBuilder(
          animation: _cameraScaleAnimation,
          builder: (context, child) {
            return Transform.scale(
              scale: _cameraScaleAnimation.value,
              child: _hasPhoto ? _buildCapturedImage() : _buildCameraPreview(),
            );
          },
        ),
      ),
    );
  }

  Widget _buildCameraPreview() {
    if (!_isCameraInitialized) {
      return Container(
        height: 300,
        decoration: BoxDecoration(
          color: Colors.grey.shade300,
          borderRadius: BorderRadius.circular(20),
        ),
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 16),
              Text('Initializing camera...'),
            ],
          ),
        ),
      );
    }

    return AspectRatio(
      aspectRatio: _controller!.value.aspectRatio,
      child: Stack(
        children: [
          CameraPreview(_controller!),
          // Overlay with instructions
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.black.withOpacity(0.3),
                  Colors.transparent,
                  Colors.black.withOpacity(0.3),
                ],
              ),
            ),
          ),
          Positioned(
            top: 20,
            left: 20,
            right: 20,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.7),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Text(
                'Position students in the camera view',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCapturedImage() {
    return Stack(
      children: [
        Image.file(
          File(_capturedImagePath!),
          width: double.infinity,
          height: double.infinity,
          fit: BoxFit.cover,
        ),
        if (!_isProcessing)
          Positioned(
            top: 10,
            right: 10,
            child: IconButton(
              onPressed: _retakePhoto,
              icon: const Icon(Icons.refresh, color: Colors.white),
              style: IconButton.styleFrom(
                backgroundColor: Colors.black.withOpacity(0.7),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildCameraControls() {
    return Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              IconButton(
                onPressed: () {},
                icon: const Icon(Icons.flash_off, size: 32),
                style: IconButton.styleFrom(
                  backgroundColor: Colors.grey.shade200,
                  padding: const EdgeInsets.all(16),
                ),
              ),
              GestureDetector(
                onTap: _capturePhoto,
                child: Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primary,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: Theme.of(
                          context,
                        ).colorScheme.primary.withOpacity(0.3),
                        blurRadius: 20,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.camera_alt,
                    color: Colors.white,
                    size: 32,
                  ),
                ),
              ),
              IconButton(
                onPressed: () {},
                icon: const Icon(Icons.flip_camera_ios, size: 32),
                style: IconButton.styleFrom(
                  backgroundColor: Colors.grey.shade200,
                  padding: const EdgeInsets.all(16),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Tap to capture attendance photo',
            style: TextStyle(fontSize: 16, color: Colors.grey.shade600),
          ),
        ],
      ),
    );
  }

  Widget _buildProcessingSection() {
    return Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          AnimatedBuilder(
            animation: _processingRotation,
            builder: (context, child) {
              return Transform.rotate(
                angle: _processingRotation.value * 2 * 3.14159,
                child: Icon(
                  Icons.psychology,
                  size: 64,
                  color: Theme.of(context).colorScheme.primary,
                ),
              );
            },
          ),
          const SizedBox(height: 24),
          const Text(
            'Processing Image...',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          Text(
            'AI is analyzing faces and recognizing students',
            style: TextStyle(fontSize: 16, color: Colors.grey.shade600),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          LinearProgressIndicator(
            backgroundColor: Colors.grey.shade300,
            valueColor: AlwaysStoppedAnimation<Color>(
              Theme.of(context).colorScheme.primary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResultsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(Icons.people, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 8),
              Text(
                'Recognition Results',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),
              const Spacer(),
              Chip(
                label: Text('${_recognizedStudents.length} recognized'),
                backgroundColor: Colors.green.withOpacity(0.2),
              ),
            ],
          ),
        ),
        Expanded(
          child: _allStudents.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : AnimationLimiter(
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: _allStudents.length,
                    itemBuilder: (context, index) {
                      final student = _allStudents[index];
                      final isRecognized = _recognizedStudents.any(
                        (s) => s['id'] == student['id'],
                      );
                      final isPresent = _presentStudentIds.contains(
                        student['id'].toString(),
                      );

                      return AnimationConfiguration.staggeredList(
                        position: index,
                        duration: const Duration(milliseconds: 375),
                        child: SlideAnimation(
                          verticalOffset: 50.0,
                          child: FadeInAnimation(
                            child: _buildStudentResultCard(
                              student,
                              isRecognized,
                              isPresent,
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
        ),
        _buildActionButtons(),
      ],
    );
  }

  Widget _buildStudentResultCard(
    dynamic student,
    bool isRecognized,
    bool isPresent,
  ) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: isPresent ? Colors.green : Colors.grey.shade400,
          child: Icon(
            isPresent ? Icons.check : Icons.person,
            color: Colors.white,
          ),
        ),
        title: Text(
          student['name'] ?? 'Unknown',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(student['email'] ?? ''),
            if (isRecognized)
              Container(
                margin: const EdgeInsets.only(top: 4),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.blue.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  'Recognized by AI',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.blue,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
          ],
        ),
        trailing: Switch(
          value: isPresent,
          onChanged: (value) {
            _toggleStudentAttendance(student['id'].toString());
          },
          activeColor: Colors.green,
        ),
      ),
    );
  }

  Widget _buildActionButtons() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: CustomButton(
              text: 'Retake Photo',
              onPressed: _retakePhoto,
              isOutlined: true,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: CustomButton(
              text: 'Mark Attendance',
              onPressed: _finalizeAttendance,
            ),
          ),
        ],
      ),
    );
  }

  void _finalizeAttendance() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm Attendance'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${_presentStudentIds.length} students marked present'),
            const SizedBox(height: 8),
            Text(
              '${_allStudents.length - _presentStudentIds.length} students marked absent',
            ),
            const SizedBox(height: 16),
            const Text('This action cannot be undone. Continue?'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _markAttendance().then((_) {
                Navigator.pop(context);
              });
            },
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }
}
