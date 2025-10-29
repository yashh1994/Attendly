import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';

class CapturedImagePreview extends StatelessWidget {
  final String imageBase64;
  final String orientation;
  final VoidCallback? onRemove;
  final double size;

  const CapturedImagePreview({
    super.key,
    required this.imageBase64,
    required this.orientation,
    this.onRemove,
    this.size = 60,
  });

  @override
  Widget build(BuildContext context) {
    // Extract base64 data without data URL prefix
    String base64Data = imageBase64;
    if (imageBase64.contains(',')) {
      base64Data = imageBase64.split(',')[1];
    }

    Uint8List imageBytes;
    try {
      imageBytes = base64Decode(base64Data);
    } catch (e) {
      return _buildErrorWidget();
    }

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.green, width: 2),
      ),
      child: Stack(
        children: [
          // Image
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: Image.memory(
              imageBytes,
              width: size,
              height: size,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) => _buildErrorWidget(),
            ),
          ),

          // Orientation label
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 2),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.7),
                borderRadius: const BorderRadius.only(
                  bottomLeft: Radius.circular(6),
                  bottomRight: Radius.circular(6),
                ),
              ),
              child: Text(
                _getOrientationLabel(orientation),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 8,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ),

          // Remove button
          if (onRemove != null)
            Positioned(
              top: -4,
              right: -4,
              child: GestureDetector(
                onTap: onRemove,
                child: Container(
                  width: 20,
                  height: 20,
                  decoration: const BoxDecoration(
                    color: Colors.red,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.close, color: Colors.white, size: 12),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildErrorWidget() {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: Colors.grey[300],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.red, width: 2),
      ),
      child: const Icon(Icons.error, color: Colors.red, size: 24),
    );
  }

  String _getOrientationLabel(String orientation) {
    switch (orientation) {
      case 'front':
        return 'Front';
      case 'left':
        return 'Left';
      case 'right':
        return 'Right';
      case 'up':
        return 'Up';
      case 'down':
        return 'Down';
      default:
        return orientation.toUpperCase();
    }
  }
}
