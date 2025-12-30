import 'package:flutter_dotenv/flutter_dotenv.dart';

class AppConfig {
  static String get backendBaseUrl {
    final raw = dotenv.env['BACKEND_BASE_URL'];
    if (raw != null) {
      final trimmed = raw.trim();
      if (trimmed.isNotEmpty) return trimmed;
    }
    return 'http://localhost:3000';
  }
}
