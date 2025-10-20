import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:provider/provider.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:http/http.dart' as http;
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';
import '../../utils/app_theme.dart';

class FaceRegistrationScreen extends StatefulWidget {
  const FaceRegistrationScreen({super.key});

  @override
  State<FaceRegistrationScreen> createState() => _FaceRegistrationScreenState();
}

class _FaceRegistrationScreenState extends State<FaceRegistrationScreen> {
  List<CameraDescription>? cameras;
  CameraController? controller;
  bool isInitialized = false;
  bool isCapturing = false;

  List<String> capturedImages = [];
  int targetImages = 10; // Capture 10 images for good facial data
  bool isProcessing = false;

  final ApiService _apiService = ApiService();

  @override
  void initState() {
    super.initState();
    _checkAuthenticationAndInitialize();
  }

  Future<void> _checkAuthenticationAndInitialize() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);

    print('🔥 FLUTTER: Checking authentication on Face Registration Screen');

    // Test server connectivity
    await _testServerConnectivity();
    print('🔥 FLUTTER: Auth state: ${authProvider.isAuthenticated}');
    print('🔥 FLUTTER: User: ${authProvider.user?.email}');

    if (!authProvider.isAuthenticated || authProvider.token == null) {
      print('🔥 FLUTTER: User not authenticated, redirecting to login');
      _showToast('Please log in first to register face data', isSuccess: false);

      // Navigate back or to login screen
      if (mounted) {
        Navigator.pop(context);
      }
      return;
    }

    _initializeCamera();
  }

  Future<void> _testServerConnectivity() async {
    try {
      print('🔥 FLUTTER: Testing server connectivity...');
      // Test a simple endpoint that doesn't require authentication
      final response = await http.get(Uri.parse('http://10.0.2.2:5000/health'));
      print(
        '🔥 FLUTTER: Health check response: ${response.statusCode} - ${response.body}',
      );

      if (response.statusCode == 200) {
        print('🔥 FLUTTER: Server connectivity test successful');
      } else {
        print(
          '🔥 FLUTTER: Server responded with status: ${response.statusCode}',
        );
        _showToast(
          'Warning: Server returned status ${response.statusCode}',
          isSuccess: false,
        );
      }
    } catch (e) {
      print('🔥 FLUTTER: Server connectivity test failed: $e');
      _showToast('Cannot connect to server: ${e.toString()}', isSuccess: false);
    }
  }

  Future<void> _initializeCamera() async {
    try {
      print('🔥 FLUTTER: Initializing camera...');

      cameras = await availableCameras();
      print('🔥 FLUTTER: Found ${cameras?.length ?? 0} cameras');

      if (cameras!.isNotEmpty) {
        // Use front camera if available
        final frontCamera = cameras!.firstWhere(
          (camera) => camera.lensDirection == CameraLensDirection.front,
          orElse: () => cameras!.first,
        );

        print(
          '🔥 FLUTTER: Using camera: ${frontCamera.name} (${frontCamera.lensDirection})',
        );

        controller = CameraController(
          frontCamera,
          ResolutionPreset.medium,
          enableAudio: false,
        );

        await controller!.initialize();
        print('🔥 FLUTTER: Camera initialized successfully');

        setState(() {
          isInitialized = true;
        });
      } else {
        print('🔥 FLUTTER: No cameras found');
        _showToast('No cameras found on this device', isSuccess: false);
        _showErrorSnackBar('No cameras found on this device');
      }
    } catch (e) {
      print('🔥 FLUTTER: Error initializing camera: $e');
      _showToast(
        'Failed to initialize camera: ${e.toString()}',
        isSuccess: false,
      );
      _showErrorSnackBar('Failed to initialize camera');
    }
  }

  @override
  void dispose() {
    controller?.dispose();
    super.dispose();
  }

  Future<void> _captureImage() async {
    if (!controller!.value.isInitialized) {
      print('🔥 FLUTTER: Camera not initialized, cannot capture image');
      return;
    }

    try {
      print(
        '🔥 FLUTTER: Starting image capture ${capturedImages.length + 1}/$targetImages',
      );

      setState(() {
        isCapturing = true;
      });

      final XFile image = await controller!.takePicture();
      final Uint8List imageBytes = await image.readAsBytes();
      final String base64Image = base64Encode(imageBytes);
      final String dataUrl = 'data:image/jpeg;base64,$base64Image';

      print(
        '🔥 FLUTTER: Image captured successfully, size: ${imageBytes.length} bytes',
      );

      // Validate the captured image for face detection
      try {
        final authProvider = Provider.of<AuthProvider>(context, listen: false);
        if (authProvider.token != null) {
          _apiService.setToken(authProvider.token);

          print('🔥 FLUTTER: Validating captured image for face detection...');
          final validationResult = await _apiService.validateFaceImage(
            image: dataUrl,
          );

          print('🔥 FLUTTER: Image validation result: $validationResult');

          if (validationResult['face_detected'] == true) {
            print(
              '🔥 FLUTTER: Face detected in image ${capturedImages.length + 1}',
            );

            setState(() {
              capturedImages.add(dataUrl);
              isCapturing = false;
            });

            _showToast(
              'Photo ${capturedImages.length}/$targetImages captured successfully!',
              isSuccess: true,
            );
          } else {
            print('🔥 FLUTTER: No face detected in captured image');
            setState(() {
              isCapturing = false;
            });

            _showToast(
              'No face detected. Please position your face clearly and try again.',
              isSuccess: false,
            );
            return; // Don't add the image or continue
          }
        } else {
          // If no auth token, just add the image (fallback)
          setState(() {
            capturedImages.add(dataUrl);
            isCapturing = false;
          });
        }
      } catch (e) {
        print('🔥 FLUTTER: Face validation failed: $e');
        // On validation error, still add the image but warn user
        setState(() {
          capturedImages.add(dataUrl);
          isCapturing = false;
        });

        _showToast(
          'Image captured but face validation failed. Continuing...',
          isSuccess: false,
        );
      }

      print(
        '🔥 FLUTTER: Total images captured: ${capturedImages.length}/$targetImages',
      );

      // Auto-capture next image after a short delay
      if (capturedImages.length < targetImages) {
        await Future.delayed(const Duration(milliseconds: 1200));
        if (mounted) {
          _captureImage();
        }
      } else {
        print('🔥 FLUTTER: All images captured, showing completion dialog');
        // All images captured, show completion dialog
        _showCompletionDialog();
      }
    } catch (e) {
      print('🔥 FLUTTER: Error capturing image: $e');
      setState(() {
        isCapturing = false;
      });
      _showToast('Failed to capture image: ${e.toString()}', isSuccess: false);
      _showErrorSnackBar('Failed to capture image');
    }
  }

  void _showCompletionDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Capture Complete!'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.check_circle, color: AppTheme.primaryColor, size: 64),
            const SizedBox(height: 16),
            Text(
              'Successfully captured ${capturedImages.length} images.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            const Text(
              'Would you like to register your facial data now?',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _resetCapture();
            },
            child: const Text('Retake'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _registerFaceData();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryColor,
            ),
            child: const Text(
              'Register',
              style: TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  void _resetCapture() {
    setState(() {
      capturedImages.clear();
    });
  }

  Future<void> _registerFaceData() async {
    print(
      '🔥 FLUTTER: Starting face data registration with ${capturedImages.length} images',
    );

    setState(() {
      isProcessing = true;
    });

    try {
      print('🔥 FLUTTER: Setting up API service with authentication...');

      // Get token from auth provider and set in API service
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      print('🔥 FLUTTER: AuthProvider state:');
      print('  - isAuthenticated: ${authProvider.isAuthenticated}');
      print('  - user: ${authProvider.user?.email}');
      print('  - token length: ${authProvider.token?.length ?? 0}');

      if (authProvider.token != null && authProvider.token!.isNotEmpty) {
        _apiService.setToken(authProvider.token);
        print('🔥 FLUTTER: Token set successfully');
        print(
          '🔥 FLUTTER: Token preview: ${authProvider.token!.substring(0, 10)}...',
        );
      } else {
        print('🔥 FLUTTER: WARNING - No authentication token found');
        print(
          '🔥 FLUTTER: Auth state - isAuthenticated: ${authProvider.isAuthenticated}',
        );
        _showToast(
          'Authentication error. Please login again.',
          isSuccess: false,
        );
        return;
      }

      print('🔥 FLUTTER: Calling batch upload API with progress tracking...');

      // Use the new batch upload with progress API
      final response = await _apiService.uploadBatchWithProgress(
        images: capturedImages,
      );

      print('🔥 FLUTTER: Batch upload API Response: $response');

      if (response['success'] == true) {
        print('🔥 FLUTTER: Face registration successful!');

        // Show detailed success information
        final successRate = response['success_rate'] ?? 0;
        final successfulImages = response['successful_images'] ?? 0;
        final totalImages = response['total_images'] ?? capturedImages.length;

        _showToast(
          'Face registration successful! $successfulImages/$totalImages images processed (${successRate.round()}% success rate)',
          isSuccess: true,
        );
        _showDetailedSuccessDialog(response);
      } else {
        print('🔥 FLUTTER: Face registration failed - ${response['message']}');

        // Show detailed error information
        _showDetailedErrorDialog(response);
      }
    } catch (e) {
      print('🔥 FLUTTER: Face registration error: $e');

      // Parse error message for better user feedback
      String errorMessage = 'Error: ${e.toString()}';

      if (e.toString().contains('Insufficient valid face images')) {
        errorMessage =
            'Could not detect your face clearly in enough images. Please try again and ensure good lighting and face visibility.';
      } else if (e.toString().contains('At least 5 images are required')) {
        errorMessage =
            'Not enough images captured. Please capture at least 5 images.';
      } else if (e.toString().contains('Already has registered facial data')) {
        errorMessage =
            'Your face is already registered. You can proceed to join classes.';
      } else if (e.toString().contains('Connection refused') ||
          e.toString().contains('Failed host lookup')) {
        errorMessage =
            'Cannot connect to server. Please check your internet connection.';
      } else if (e.toString().contains('401') ||
          e.toString().contains('Unauthorized')) {
        errorMessage = 'Authentication failed. Please login again.';
      } else if (e.toString().contains('404') ||
          e.toString().contains('Not Found')) {
        errorMessage =
            'Server endpoint not found. Please check server configuration.';
      }

      _showToast(errorMessage, isSuccess: false);
      _showErrorSnackBar(errorMessage);
    } finally {
      setState(() {
        isProcessing = false;
      });
    }
  }

  void _showToast(String message, {required bool isSuccess}) {
    Fluttertoast.showToast(
      msg: message,
      toastLength: Toast.LENGTH_LONG,
      gravity: ToastGravity.BOTTOM,
      timeInSecForIosWeb: 3,
      backgroundColor: isSuccess ? AppTheme.successColor : AppTheme.errorColor,
      textColor: Colors.white,
      fontSize: 16.0,
    );
  }

  void _showDetailedSuccessDialog(Map<String, dynamic> response) {
    final successRate = response['success_rate']?.round() ?? 0;
    final successfulImages = response['successful_images'] ?? 0;
    final totalImages = response['total_images'] ?? capturedImages.length;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Icon(Icons.check_circle, color: AppTheme.primaryColor, size: 28),
            const SizedBox(width: 8),
            const Text('Registration Successful!'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.face, color: AppTheme.primaryColor, size: 64),
            const SizedBox(height: 16),
            const Text(
              'Your facial data has been registered successfully!',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.primaryColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Processing Results:',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: AppTheme.primaryColor,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text('📷 Total Images: $totalImages'),
                  Text('✅ Valid Images: $successfulImages'),
                  Text('📊 Success Rate: $successRate%'),
                ],
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'You can now join classes and mark attendance using facial recognition.',
              style: TextStyle(fontSize: 14),
            ),
          ],
        ),
        actions: [
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context); // Close dialog
              Navigator.pop(context); // Go back to previous screen
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryColor,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: const Text(
              'Continue',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showDetailedErrorDialog(Map<String, dynamic> response) {
    final message = response['message'] ?? 'Registration failed';
    final successfulImages = response['successful_images'] ?? 0;
    final totalImages = response['total_images'] ?? capturedImages.length;
    final recommendation = response['recommendation'] ?? 'Please try again';
    final results = response['results'] as List<dynamic>? ?? [];

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Icon(Icons.error, color: AppTheme.errorColor, size: 28),
            const SizedBox(width: 8),
            const Text('Registration Failed'),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                message,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.errorColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Processing Results:',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: AppTheme.errorColor,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text('📷 Total Images: $totalImages'),
                    Text('✅ Valid Images: $successfulImages'),
                    if (results.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        'Image Analysis:',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: AppTheme.errorColor,
                        ),
                      ),
                      ...results.take(5).map((result) {
                        final imageNum = result['image_number'] ?? 0;
                        final success = result['success'] ?? false;
                        final faceDetected = result['face_detected'] ?? false;
                        return Text(
                          'Image $imageNum: ${success ? '✅' : '❌'} ${faceDetected ? 'Face detected' : 'No face'}',
                          style: const TextStyle(fontSize: 12),
                        );
                      }).toList(),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '💡 Recommendation:',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(recommendation),
                  ],
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _resetCapture();
            },
            child: const Text('Try Again'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context); // Close dialog
              Navigator.pop(context); // Go back to previous screen
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryColor,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: const Text('Back', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: AppTheme.errorColor),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Face Registration'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: isProcessing
          ? _buildProcessingView()
          : !isInitialized
          ? _buildLoadingView()
          : _buildCameraView(),
    );
  }

  Widget _buildProcessingView() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('Processing facial data...', style: TextStyle(fontSize: 16)),
          SizedBox(height: 8),
          Text(
            'Please wait while we register your face',
            style: TextStyle(fontSize: 14, color: Colors.grey),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingView() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('Initializing camera...'),
        ],
      ),
    );
  }

  Widget _buildCameraView() {
    return AnimationLimiter(
      child: Column(
        children: AnimationConfiguration.toStaggeredList(
          duration: const Duration(milliseconds: 375),
          childAnimationBuilder: (widget) => SlideAnimation(
            verticalOffset: 50.0,
            child: FadeInAnimation(child: widget),
          ),
          children: [
            // Instructions
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              margin: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.primaryColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: AppTheme.primaryColor.withOpacity(0.3),
                ),
              ),
              child: Column(
                children: [
                  Icon(Icons.face, color: AppTheme.primaryColor, size: 32),
                  const SizedBox(height: 8),
                  const Text(
                    'Face Registration',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'We need to capture ${targetImages} images of your face for accurate recognition. Keep your face centered and look directly at the camera.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 14,
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ],
              ),
            ),

            // Progress indicator
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Progress: ${capturedImages.length}/$targetImages',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        '${((capturedImages.length / targetImages) * 100).round()}%',
                        style: TextStyle(
                          fontSize: 14,
                          color: AppTheme.primaryColor,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  LinearProgressIndicator(
                    value: capturedImages.length / targetImages,
                    backgroundColor: Colors.grey[300],
                    valueColor: AlwaysStoppedAnimation<Color>(
                      AppTheme.primaryColor,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // Camera preview
            Expanded(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isCapturing
                        ? AppTheme.primaryColor
                        : Colors.grey[300]!,
                    width: 3,
                  ),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(17),
                  child: CameraPreview(controller!),
                ),
              ),
            ),

            const SizedBox(height: 20),

            // Capture button
            Container(
              margin: const EdgeInsets.all(16),
              child: Column(
                children: [
                  if (capturedImages.length < targetImages)
                    ElevatedButton.icon(
                      onPressed: isCapturing ? null : _captureImage,
                      icon: Icon(
                        isCapturing ? Icons.hourglass_empty : Icons.camera_alt,
                        color: Colors.white,
                      ),
                      label: Text(
                        isCapturing
                            ? 'Capturing...'
                            : capturedImages.isEmpty
                            ? 'Start Capture'
                            : 'Continue (${capturedImages.length}/$targetImages)',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryColor,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 32,
                          vertical: 16,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        elevation: 8,
                        shadowColor: AppTheme.primaryColor.withOpacity(0.3),
                      ),
                    ),

                  if (capturedImages.isNotEmpty)
                    TextButton.icon(
                      onPressed: _resetCapture,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Reset and Start Over'),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
