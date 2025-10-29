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
import '../../widgets/captured_image_preview.dart';

class OrientationFaceRegistrationScreen extends StatefulWidget {
  const OrientationFaceRegistrationScreen({super.key});

  @override
  State<OrientationFaceRegistrationScreen> createState() =>
      _OrientationFaceRegistrationScreenState();
}

class _OrientationFaceRegistrationScreenState
    extends State<OrientationFaceRegistrationScreen> {
  List<CameraDescription>? cameras;
  CameraController? controller;
  bool isInitialized = false;
  bool isCapturing = false;
  bool isProcessing = false;

  final ApiService _apiService = ApiService();

  // Orientation tracking
  List<String> orientations = ['front', 'left', 'right', 'up', 'down'];
  List<String> orientationLabels = [
    'Front View',
    'Turn Left',
    'Turn Right',
    'Look Up',
    'Look Down',
  ];
  List<String> orientationInstructions = [
    'Look straight at the camera',
    'Turn your head to the left (your left)',
    'Turn your head to the right (your right)',
    'Tilt your head up slightly',
    'Tilt your head down slightly',
  ];

  int currentOrientationIndex = 0;
  Map<String, String> capturedImages = {}; // orientation -> base64 image

  bool get isComplete =>
      capturedImages.length == 5; // All 5 orientations required
  bool get allOrientationsComplete =>
      capturedImages.length == orientations.length;

  String get currentOrientation => orientations[currentOrientationIndex];
  String get currentOrientationLabel =>
      orientationLabels[currentOrientationIndex];
  String get currentInstruction =>
      orientationInstructions[currentOrientationIndex];

  @override
  void initState() {
    super.initState();
    _checkAuthenticationAndInitialize();
  }

  Future<void> _checkAuthenticationAndInitialize() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);

    print(
      '🔥 FLUTTER: Checking authentication on Orientation Face Registration Screen',
    );

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
      final response = await http.get(
        Uri.parse('http://localhost:5000/health'),
      );
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

        // Show onboarding dialog after a short delay
        Future.delayed(const Duration(milliseconds: 500), () {
          if (mounted) _showOnboardingDialog();
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

  Future<void> _captureCurrentOrientation() async {
    if (!controller!.value.isInitialized) {
      print('🔥 FLUTTER: Camera not initialized, cannot capture image');
      return;
    }

    if (capturedImages.containsKey(currentOrientation)) {
      // Already captured this orientation, ask for confirmation
      final shouldRecapture = await _showRecaptureDialog();
      if (!shouldRecapture) return;
    }

    try {
      print(
        '🔥 FLUTTER: Starting capture for orientation: $currentOrientation',
      );

      setState(() {
        isCapturing = true;
      });

      final XFile image = await controller!.takePicture();
      final Uint8List imageBytes = await image.readAsBytes();
      final String base64Image = base64Encode(imageBytes);
      final String dataUrl = 'data:image/jpeg;base64,$base64Image';

      print(
        '🔥 FLUTTER: Image captured successfully for $currentOrientation, size: ${imageBytes.length} bytes',
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
            print('🔥 FLUTTER: Face detected in $currentOrientation image');

            setState(() {
              capturedImages[currentOrientation] = dataUrl;
              isCapturing = false;
            });

            _showToast(
              '$currentOrientationLabel captured successfully!',
              isSuccess: true,
            );

            // Move to next orientation if not completed
            _moveToNextOrientation();
          } else {
            print('🔥 FLUTTER: No face detected in captured image');
            setState(() {
              isCapturing = false;
            });

            _showToast(
              'No face detected. Please position your face clearly and try again.',
              isSuccess: false,
            );
            return;
          }
        }
      } catch (e) {
        print('🔥 FLUTTER: Image validation error: $e');
        setState(() {
          isCapturing = false;
        });
        _showToast(
          'Failed to validate image: ${e.toString()}',
          isSuccess: false,
        );
      }
    } catch (e) {
      print('🔥 FLUTTER: Error capturing image: $e');
      setState(() {
        isCapturing = false;
      });
      _showToast('Failed to capture image: ${e.toString()}', isSuccess: false);
    }
  }

  Future<bool> _showRecaptureDialog() async {
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Recapture Image'),
            content: Text(
              'You already captured an image for $currentOrientationLabel. Do you want to recapture it?',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Keep Current'),
              ),
              TextButton(
                onPressed: () => Navigator.of(context).pop(true),
                child: const Text('Recapture'),
              ),
            ],
          ),
        ) ??
        false;
  }

  void _moveToNextOrientation() {
    // Find next uncaptured orientation
    for (int i = 0; i < orientations.length; i++) {
      if (!capturedImages.containsKey(orientations[i])) {
        setState(() {
          currentOrientationIndex = i;
        });
        return;
      }
    }

    // All orientations captured
    setState(() {
      currentOrientationIndex = 0; // Reset to first for review
    });
  }

  void _selectOrientation(int index) {
    setState(() {
      currentOrientationIndex = index;
    });
  }

  void _removeOrientation(String orientation) {
    setState(() {
      capturedImages.remove(orientation);
    });
    _showToast('Removed $orientation image', isSuccess: true);
  }

  Future<void> _submitFacialData() async {
    if (!isComplete) {
      _showToast(
        'Please capture all 5 orientations before submitting',
        isSuccess: false,
      );
      return;
    }

    try {
      setState(() {
        isProcessing = true;
      });

      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      if (authProvider.token == null) {
        _showToast(
          'Authentication error. Please log in again.',
          isSuccess: false,
        );
        return;
      }

      _apiService.setToken(authProvider.token);

      print(
        '🔥 FLUTTER: Submitting facial data with ${capturedImages.length} orientations',
      );

      // Convert to the format expected by the API
      final List<Map<String, String>> imagesForApi = capturedImages.entries
          .map((entry) => {'orientation': entry.key, 'image': entry.value})
          .toList();

      final result = await _apiService.uploadFaceDataWithOrientations(
        images: imagesForApi,
      );

      print('🔥 FLUTTER: Facial data upload result: $result');

      if (result['success'] == true) {
        _showToast('Facial data registered successfully!', isSuccess: true);

        // Show success dialog and navigate back
        await _showSuccessDialog();
        if (mounted) {
          Navigator.pop(context, true); // Return true to indicate success
        }
      } else {
        final errorMessage = result['error'] ?? 'Unknown error occurred';
        _showToast(
          'Failed to register facial data: $errorMessage',
          isSuccess: false,
        );
      }
    } catch (e) {
      print('🔥 FLUTTER: Error submitting facial data: $e');
      _showToast('Error: ${e.toString()}', isSuccess: false);
    } finally {
      if (mounted) {
        setState(() {
          isProcessing = false;
        });
      }
    }
  }

  Future<void> _showSuccessDialog() async {
    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.check_circle, color: Colors.green, size: 28),
            SizedBox(width: 12),
            Text('Success!'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Your facial data has been registered successfully with the following orientations:',
            ),
            const SizedBox(height: 12),
            ...capturedImages.keys.map(
              (orientation) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: [
                    const Icon(Icons.check, color: Colors.green, size: 16),
                    const SizedBox(width: 8),
                    Text(orientationLabels[orientations.indexOf(orientation)]),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            const Text('You can now use face recognition for attendance!'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showToast(String message, {required bool isSuccess}) {
    Fluttertoast.showToast(
      msg: message,
      toastLength: Toast.LENGTH_SHORT,
      gravity: ToastGravity.BOTTOM,
      backgroundColor: isSuccess ? Colors.green : Colors.red,
      textColor: Colors.white,
    );
  }

  void _showErrorSnackBar(String message) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: Colors.red,
          duration: const Duration(seconds: 3),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundLight,
      appBar: AppBar(
        title: const Text(
          'Face Registration',
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
        ),
        backgroundColor: AppTheme.primaryColor,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          if (capturedImages.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () => _showRestartDialog(),
              tooltip: 'Start Over',
            ),
        ],
      ),
      body: isInitialized ? _buildMainContent() : _buildLoadingScreen(),
    );
  }

  Widget _buildLoadingScreen() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 20),
          Text(
            'Initializing camera...',
            style: const TextStyle(fontSize: 16, color: AppTheme.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildMainContent() {
    return Column(
      children: [
        // Progress indicator
        _buildProgressHeader(),

        // Camera preview
        Expanded(flex: 3, child: _buildCameraSection()),

        // Orientation selector and controls
        Expanded(flex: 2, child: _buildControlsSection()),
      ],
    );
  }

  Widget _buildProgressHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withOpacity(0.1),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          // Progress bar
          Row(
            children: [
              Text(
                'Progress: ${capturedImages.length}/${orientations.length}',
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 16,
                ),
              ),
              const Spacer(),
              Text(
                isComplete
                    ? 'Ready to submit!'
                    : 'Required: All 5 orientations',
                style: TextStyle(
                  fontSize: 12,
                  color: isComplete ? Colors.green : AppTheme.textSecondary,
                  fontWeight: isComplete ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: capturedImages.length / orientations.length,
            backgroundColor: Colors.grey[300],
            valueColor: AlwaysStoppedAnimation<Color>(
              isComplete ? Colors.green : AppTheme.primaryColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCameraSection() {
    return Container(
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Stack(
          children: [
            // Camera preview
            AspectRatio(
              aspectRatio: controller!.value.aspectRatio,
              child: CameraPreview(controller!),
            ),

            // Overlay with instructions
            Positioned(
              top: 16,
              left: 16,
              right: 16,
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.7),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      currentOrientationLabel,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      currentInstruction,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Capture button overlay
            Positioned(
              bottom: 20,
              left: 0,
              right: 0,
              child: Center(child: _buildCaptureButton()),
            ),

            // Loading overlay
            if (isCapturing)
              Container(
                color: Colors.black.withOpacity(0.5),
                child: const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CircularProgressIndicator(color: Colors.white),
                      SizedBox(height: 16),
                      Text(
                        'Capturing and validating...',
                        style: TextStyle(color: Colors.white, fontSize: 16),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildCaptureButton() {
    final isCaptured = capturedImages.containsKey(currentOrientation);

    return GestureDetector(
      onTap: isCapturing ? null : _captureCurrentOrientation,
      child: Container(
        width: 80,
        height: 80,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isCaptured ? Colors.green : Colors.white,
          border: Border.all(
            color: isCaptured ? Colors.green : AppTheme.primaryColor,
            width: 4,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Icon(
          isCaptured ? Icons.check : Icons.camera_alt,
          size: 32,
          color: isCaptured ? Colors.white : AppTheme.primaryColor,
        ),
      ),
    );
  }

  Widget _buildControlsSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Captured images preview
          if (capturedImages.isNotEmpty) _buildCapturedImagesPreview(),

          // Orientation selector
          Expanded(child: _buildOrientationSelector()),

          const SizedBox(height: 16),

          // Action buttons
          _buildActionButtons(),
        ],
      ),
    );
  }

  Widget _buildCapturedImagesPreview() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Captured Images:',
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 70,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: capturedImages.length,
            separatorBuilder: (context, index) => const SizedBox(width: 8),
            itemBuilder: (context, index) {
              final orientation = capturedImages.keys.elementAt(index);
              final imageBase64 = capturedImages[orientation]!;

              return CapturedImagePreview(
                imageBase64: imageBase64,
                orientation: orientation,
                onRemove: () => _removeOrientation(orientation),
                size: 60,
              );
            },
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _buildOrientationSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Select Orientation to Capture:',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: GridView.builder(
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 1.2,
            ),
            itemCount: orientations.length,
            itemBuilder: (context, index) {
              final orientation = orientations[index];
              final label = orientationLabels[index];
              final isCaptured = capturedImages.containsKey(orientation);
              final isSelected = index == currentOrientationIndex;

              return GestureDetector(
                onTap: () => _selectOrientation(index),
                onLongPress: isCaptured
                    ? () => _removeOrientation(orientation)
                    : null,
                child: AnimationConfiguration.staggeredGrid(
                  position: index,
                  duration: const Duration(milliseconds: 375),
                  columnCount: 3,
                  child: SlideAnimation(
                    verticalOffset: 50.0,
                    child: FadeInAnimation(
                      child: Container(
                        decoration: BoxDecoration(
                          color: isSelected
                              ? AppTheme.primaryColor
                              : isCaptured
                              ? Colors.green
                              : Colors.grey[100],
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: isSelected
                                ? AppTheme.primaryColor
                                : isCaptured
                                ? Colors.green
                                : Colors.grey[300]!,
                            width: 2,
                          ),
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              isCaptured
                                  ? Icons.check_circle
                                  : _getOrientationIcon(orientation),
                              size: 28,
                              color: isSelected || isCaptured
                                  ? Colors.white
                                  : AppTheme.textSecondary,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              label,
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                                color: isSelected || isCaptured
                                    ? Colors.white
                                    : AppTheme.textSecondary,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  IconData _getOrientationIcon(String orientation) {
    switch (orientation) {
      case 'front':
        return Icons.face;
      case 'left':
        return Icons.keyboard_arrow_left;
      case 'right':
        return Icons.keyboard_arrow_right;
      case 'up':
        return Icons.keyboard_arrow_up;
      case 'down':
        return Icons.keyboard_arrow_down;
      default:
        return Icons.face;
    }
  }

  Widget _buildActionButtons() {
    return Row(
      children: [
        if (capturedImages.isNotEmpty)
          Expanded(
            child: OutlinedButton(
              onPressed: isProcessing ? null : () => _showRestartDialog(),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: const Text('Start Over'),
            ),
          ),

        if (capturedImages.isNotEmpty) const SizedBox(width: 12),

        Expanded(
          flex: 2,
          child: ElevatedButton(
            onPressed: isComplete && !isProcessing ? _submitFacialData : null,
            style: ElevatedButton.styleFrom(
              backgroundColor: isComplete
                  ? Colors.green
                  : AppTheme.primaryColor,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              elevation: isComplete ? 4 : 2,
            ),
            child: isProcessing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                : Text(
                    isComplete
                        ? 'Submit Facial Data'
                        : 'Capture More (${capturedImages.length}/5)',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
          ),
        ),
      ],
    );
  }

  void _showOnboardingDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Icon(Icons.lightbulb_outline, color: Colors.amber.shade700),
            const SizedBox(width: 8),
            const Text('Enhanced Face Registration'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'This enhanced registration captures your face in multiple orientations for better recognition accuracy.',
              style: TextStyle(fontSize: 15),
            ),
            const SizedBox(height: 16),
            const Text(
              'Instructions:',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            const Text('• Capture all 5 different orientations'),
            const Text('• Follow the on-screen guidance for each pose'),
            const Text('• Ensure good lighting and clear face visibility'),
            const Text('• Hold still during each capture'),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.info_outline,
                    color: Colors.blue.shade700,
                    size: 16,
                  ),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'Tap on orientation tiles below to select which pose to capture',
                      style: TextStyle(fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryColor,
            ),
            child: const Text('Got it!', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  Future<void> _showRestartDialog() async {
    final shouldRestart = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Start Over'),
        content: const Text(
          'Are you sure you want to clear all captured images and start over?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Start Over'),
          ),
        ],
      ),
    );

    if (shouldRestart == true) {
      setState(() {
        capturedImages.clear();
        currentOrientationIndex = 0;
      });
      _showToast('Cleared all images. Start capturing again!', isSuccess: true);
    }
  }
}
