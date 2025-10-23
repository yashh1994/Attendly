import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:camera/camera.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import 'package:permission_handler/permission_handler.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/custom_widgets.dart';
import '../../utils/app_theme.dart';
import '../../utils/routes.dart';

class FaceCaptureScreen extends StatefulWidget {
  const FaceCaptureScreen({super.key});

  @override
  State<FaceCaptureScreen> createState() => _FaceCaptureScreenState();
}

class _FaceCaptureScreenState extends State<FaceCaptureScreen>
    with TickerProviderStateMixin {
  CameraController? _cameraController;
  List<CameraDescription>? _cameras;
  bool _isCameraInitialized = false;
  bool _isCapturing = false;
  List<String> _capturedImages = [];
  int _currentImageIndex = 0;
  final int _totalImages = 10;

  late AnimationController _progressAnimationController;
  late Animation<double> _progressAnimation;
  late AnimationController _instructionAnimationController;
  late Animation<double> _instructionAnimation;

  final List<String> _instructions = [
    'Look straight at the camera',
    'Turn your head slightly to the left',
    'Turn your head slightly to the right',
    'Tilt your head up slightly',
    'Tilt your head down slightly',
    'Smile naturally',
    'Keep a neutral expression',
    'Look straight again',
    'Blink and look at the camera',
    'Final photo - perfect!',
  ];

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
    _requestPermissions();
  }

  void _initializeAnimations() {
    _progressAnimationController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _progressAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _progressAnimationController,
        curve: Curves.easeInOut,
      ),
    );

    _instructionAnimationController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _instructionAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _instructionAnimationController,
        curve: Curves.easeInOut,
      ),
    );
  }

  Future<void> _requestPermissions() async {
    final cameraStatus = await Permission.camera.request();

    if (cameraStatus.isGranted) {
      _initializeCamera();
    } else {
      _showPermissionDialog();
    }
  }

  void _showPermissionDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('Camera Permission Required'),
        content: const Text(
          'To capture your facial data for attendance recognition, we need access to your camera.',
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              Navigator.pushReplacementNamed(context, Routes.login);
            },
            child: const Text('Skip'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _requestPermissions();
            },
            child: const Text('Grant Permission'),
          ),
        ],
      ),
    );
  }

  Future<void> _initializeCamera() async {
    try {
      _cameras = await availableCameras();

      if (_cameras != null && _cameras!.isNotEmpty) {
        // Use FRONT camera for selfie registration
        final frontCamera = _cameras!.firstWhere(
          (camera) => camera.lensDirection == CameraLensDirection.front,
          orElse: () => _cameras!.first,
        );

        print(
          '🔥 FLUTTER: Using ${frontCamera.lensDirection} camera for face registration',
        );

        _cameraController = CameraController(
          frontCamera,
          ResolutionPreset.high, // High quality for better face recognition
          enableAudio: false,
          imageFormatGroup: ImageFormatGroup.jpeg, // Ensure JPEG format
        );

        await _cameraController!.initialize();

        print(
          '🔥 FLUTTER: Camera initialized - Resolution: ${_cameraController!.value.previewSize}',
        );

        if (mounted) {
          setState(() {
            _isCameraInitialized = true;
          });
          _instructionAnimationController.forward();
        }
      }
    } catch (e) {
      print('Error initializing camera: $e');
      _showCameraError();
    }
  }

  void _showCameraError() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Camera Error'),
        content: const Text('Failed to initialize camera. Please try again.'),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              Navigator.pushReplacementNamed(context, Routes.login);
            },
            child: const Text('Go Back'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _initializeCamera();
            },
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Future<void> _captureImage() async {
    if (!_isCameraInitialized || _isCapturing || _cameraController == null)
      return;

    setState(() {
      _isCapturing = true;
    });

    try {
      final image = await _cameraController!.takePicture();
      final imageBytes = await File(image.path).readAsBytes();
      final base64Image = base64Encode(imageBytes);

      setState(() {
        _capturedImages.add('data:image/jpeg;base64,$base64Image');
        _currentImageIndex++;
        _isCapturing = false;
      });

      // Update progress
      _progressAnimationController.forward();

      // Animate to next instruction
      if (_currentImageIndex < _totalImages) {
        _instructionAnimationController.reverse().then((_) {
          _instructionAnimationController.forward();
        });
      }

      // Check if all images captured
      if (_currentImageIndex >= _totalImages) {
        _uploadImages();
      }

      // Clean up the temporary image file
      await File(image.path).delete();
    } catch (e) {
      setState(() {
        _isCapturing = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to capture image: $e'),
          backgroundColor: AppTheme.errorColor,
        ),
      );
    }
  }

  Future<void> _uploadImages() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);

    final success = await authProvider.uploadFaceData(_capturedImages);

    if (!mounted) return;

    if (success) {
      Navigator.pushReplacementNamed(context, Routes.studentHome);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(authProvider.error ?? 'Failed to upload face data'),
          backgroundColor: AppTheme.errorColor,
        ),
      );

      // Allow retry
      setState(() {
        _capturedImages.clear();
        _currentImageIndex = 0;
      });
      _progressAnimationController.reset();
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _progressAnimationController.dispose();
    _instructionAnimationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Consumer<AuthProvider>(
        builder: (context, authProvider, child) {
          return LoadingOverlay(
            isLoading: authProvider.isLoading,
            message: 'Uploading facial data...',
            child: SafeArea(
              child: Column(
                children: [
                  // Header
                  Container(
                    padding: const EdgeInsets.all(20),
                    child: AnimationLimiter(
                      child: Column(
                        children: AnimationConfiguration.toStaggeredList(
                          duration: const Duration(milliseconds: 600),
                          childAnimationBuilder: (widget) => SlideAnimation(
                            verticalOffset: 30.0,
                            child: FadeInAnimation(child: widget),
                          ),
                          children: [
                            Row(
                              children: [
                                IconButton(
                                  icon: const Icon(
                                    Icons.close,
                                    color: Colors.white,
                                  ),
                                  onPressed: () {
                                    Navigator.pushReplacementNamed(
                                      context,
                                      Routes.login,
                                    );
                                  },
                                ),
                                const Spacer(),
                                Text(
                                  'Face Capture',
                                  style: Theme.of(context)
                                      .textTheme
                                      .headlineSmall
                                      ?.copyWith(
                                        color: Colors.white,
                                        fontWeight: FontWeight.w600,
                                      ),
                                ),
                                const Spacer(),
                                const SizedBox(
                                  width: 48,
                                ), // Balance the close button
                              ],
                            ),

                            const SizedBox(height: 16),

                            // Progress Bar
                            Container(
                              height: 4,
                              margin: const EdgeInsets.symmetric(
                                horizontal: 20,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.2),
                                borderRadius: BorderRadius.circular(2),
                              ),
                              child: AnimatedBuilder(
                                animation: _progressAnimation,
                                builder: (context, child) {
                                  return FractionallySizedBox(
                                    alignment: Alignment.centerLeft,
                                    widthFactor:
                                        _currentImageIndex / _totalImages,
                                    child: Container(
                                      decoration: BoxDecoration(
                                        gradient: AppTheme.primaryGradient,
                                        borderRadius: BorderRadius.circular(2),
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),

                            const SizedBox(height: 8),

                            Text(
                              '${_currentImageIndex + 1} of $_totalImages',
                              style: Theme.of(context).textTheme.bodyMedium
                                  ?.copyWith(
                                    color: Colors.white.withOpacity(0.8),
                                  ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),

                  // Camera Preview
                  Expanded(
                    child: _isCameraInitialized
                        ? Stack(
                            children: [
                              // Camera Preview
                              Container(
                                margin: const EdgeInsets.all(20),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(20),
                                  border: Border.all(
                                    color: Colors.white.withOpacity(0.3),
                                    width: 2,
                                  ),
                                ),
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(18),
                                  child: AspectRatio(
                                    aspectRatio: 3 / 4,
                                    child: CameraPreview(_cameraController!),
                                  ),
                                ),
                              ),

                              // Camera Type Indicator (Top-right)
                              Positioned(
                                top: 30,
                                right: 30,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12,
                                    vertical: 6,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.blue.withOpacity(0.9),
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(
                                        Icons.camera_front,
                                        color: Colors.white,
                                        size: 16,
                                      ),
                                      const SizedBox(width: 4),
                                      Text(
                                        'Selfie Camera',
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),

                              // Face Overlay
                              Center(
                                child: Container(
                                  width: 250,
                                  height: 300,
                                  decoration: BoxDecoration(
                                    border: Border.all(
                                      color: AppTheme.primaryColor,
                                      width: 3,
                                    ),
                                    borderRadius: BorderRadius.circular(150),
                                  ),
                                ),
                              ),
                            ],
                          )
                        : const Center(
                            child: CircularProgressIndicator(
                              valueColor: AlwaysStoppedAnimation<Color>(
                                Colors.white,
                              ),
                            ),
                          ),
                  ),

                  // Instructions and Capture Button
                  Container(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      children: [
                        // Instruction Text
                        AnimatedBuilder(
                          animation: _instructionAnimation,
                          builder: (context, child) {
                            return FadeTransition(
                              opacity: _instructionAnimation,
                              child: SlideTransition(
                                position: Tween<Offset>(
                                  begin: const Offset(0, 0.5),
                                  end: Offset.zero,
                                ).animate(_instructionAnimation),
                                child: Container(
                                  padding: const EdgeInsets.all(16),
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Text(
                                    _currentImageIndex < _instructions.length
                                        ? _instructions[_currentImageIndex]
                                        : 'Uploading...',
                                    style: Theme.of(context).textTheme.bodyLarge
                                        ?.copyWith(
                                          color: Colors.white,
                                          fontWeight: FontWeight.w500,
                                        ),
                                    textAlign: TextAlign.center,
                                  ),
                                ),
                              ),
                            );
                          },
                        ),

                        const SizedBox(height: 32),

                        // Capture Button
                        if (_currentImageIndex < _totalImages)
                          GestureDetector(
                            onTap: _captureImage,
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 200),
                              width: 80,
                              height: 80,
                              decoration: BoxDecoration(
                                color: _isCapturing
                                    ? Colors.white.withOpacity(0.5)
                                    : Colors.white,
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: AppTheme.primaryColor,
                                  width: 4,
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: AppTheme.primaryColor.withOpacity(
                                      0.3,
                                    ),
                                    blurRadius: 10,
                                    spreadRadius: 2,
                                  ),
                                ],
                              ),
                              child: Icon(
                                _isCapturing
                                    ? Icons.hourglass_empty
                                    : Icons.camera_alt,
                                color: AppTheme.primaryColor,
                                size: 32,
                              ),
                            ),
                          ),

                        const SizedBox(height: 20),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
