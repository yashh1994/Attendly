import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';
import '../models/user.dart';

class AuthProvider extends ChangeNotifier {
  static const String _tokenKey = 'auth_token';
  static const String _userKey = 'user_data';
  static const String _roleKey = 'user_role';

  final SharedPreferences _prefs;
  final ApiService _apiService = ApiService();

  String? _token;
  User? _user;
  bool _isLoading = false;
  String? _error;

  AuthProvider(this._prefs) {
    _loadAuthData();
  }

  // Getters
  bool get isAuthenticated => _token != null && _user != null;
  bool get isLoading => _isLoading;
  String? get error => _error;
  User? get user => _user;
  String? get token => _token;
  String? get userRole => _user?.role;

  // Load authentication data from storage
  void _loadAuthData() {
    _token = _prefs.getString(_tokenKey);
    final userData = _prefs.getString(_userKey);

    print('🔥 AUTH_PROVIDER: Loading auth data...');
    print('🔥 AUTH_PROVIDER: Token found: ${_token != null}');
    print('🔥 AUTH_PROVIDER: User data found: ${userData != null}');

    if (userData != null) {
      try {
        final userMap = jsonDecode(userData);
        _user = User.fromJson(userMap);
        print(
          '🔥 AUTH_PROVIDER: User loaded: ${_user?.email}, Role: ${_user?.role}',
        );
      } catch (e) {
        print('🔥 AUTH_PROVIDER: Error loading user data: $e');
        clearAuthData();
      }
    }

    // IMPORTANT: Set the token in ApiService when loading saved auth data
    if (_token != null) {
      _apiService.setToken(_token);
      print('🔥 FLUTTER: Token loaded and set in ApiService: $_token');
    }
  }

  // Save authentication data to storage
  Future<void> _saveAuthData() async {
    if (_token != null) {
      await _prefs.setString(_tokenKey, _token!);
    }

    if (_user != null) {
      await _prefs.setString(_userKey, jsonEncode(_user!.toJson()));
    }
  }

  // Clear authentication data
  Future<void> clearAuthData() async {
    _token = null;
    _user = null;
    _error = null;

    await _prefs.remove(_tokenKey);
    await _prefs.remove(_userKey);
    await _prefs.remove(_roleKey);

    notifyListeners();
  }

  // Set error
  void _setError(String error) {
    _error = error;
    notifyListeners();
  }

  // Clear error
  void clearError() {
    _error = null;
    notifyListeners();
  }

  // Set loading state
  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  // Register user
  Future<bool> register({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
  }) async {
    try {
      print('🔥 FLUTTER: AuthProvider.register called');
      print(
        '🔥 FLUTTER: firstName=$firstName, lastName=$lastName, email=$email',
      );

      _setLoading(true);
      clearError();

      print('🔥 FLUTTER: Calling ApiService.register...');
      final response = await _apiService.register(
        firstName: firstName,
        lastName: lastName,
        email: email,
        password: password,
      );

      print('🔥 FLUTTER: Registration response received: $response');

      _token = response['access_token'];
      _user = User.fromJson(response['user']);

      // Set token in API service immediately
      _apiService.setToken(_token);

      print('🔥 FLUTTER: User created: ${_user?.toJson()}');
      print('🔥 FLUTTER: Token: $_token');
      print('🔥 FLUTTER: Token set in ApiService');

      await _saveAuthData();
      _setLoading(false);

      print('🔥 FLUTTER: Registration successful');
      return true;
    } catch (e) {
      print('🔥 FLUTTER: Registration error: $e');
      _setError(e.toString());
      _setLoading(false);
      return false;
    }
  }

  // Set user role after registration
  Future<bool> setUserRole(String role) async {
    try {
      print('🔥 FLUTTER: AuthProvider.setUserRole called with role: $role');
      print('🔥 FLUTTER: Current token: $_token');
      print('🔥 FLUTTER: Current user: ${_user?.toJson()}');

      _setLoading(true);
      clearError();

      if (_user == null) {
        print('🔥 FLUTTER: ERROR - User data not found');
        _setError('User data not found');
        _setLoading(false);
        return false;
      }

      if (_token == null) {
        print('🔥 FLUTTER: ERROR - No token available');
        _setError('No authentication token');
        _setLoading(false);
        return false;
      }

      // Ensure token is set in API service
      _apiService.setToken(_token);
      print('🔥 FLUTTER: Token set in ApiService before role update');

      print('🔥 FLUTTER: Calling ApiService.updateUserRole...');
      final response = await _apiService.updateUserRole(role);
      print('🔥 FLUTTER: Role update response: $response');

      _user = User.fromJson(response['user']);

      await _saveAuthData();
      _setLoading(false);

      return true;
    } catch (e) {
      print('🔥 FLUTTER: ERROR in setUserRole: $e');
      print('🔥 FLUTTER: ERROR type: ${e.runtimeType}');
      _setError(e.toString());
      _setLoading(false);
      return false;
    }
  }

  // Login user
  Future<bool> login({required String email, required String password}) async {
    try {
      _setLoading(true);
      clearError();

      final response = await _apiService.login(
        email: email,
        password: password,
      );

      _token = response['access_token'];
      _user = User.fromJson(response['user']);

      // IMPORTANT: Set the token in ApiService so it's included in all future requests
      _apiService.setToken(_token);
      print('🔥 FLUTTER: Token set in ApiService after login: $_token');

      await _saveAuthData();
      _setLoading(false);

      return true;
    } catch (e) {
      _setError(e.toString());
      _setLoading(false);
      return false;
    }
  }

  // Logout user
  Future<void> logout() async {
    try {
      if (_token != null) {
        await _apiService.logout();
      }
    } catch (e) {
      // Continue with local logout even if API call fails
    } finally {
      await clearAuthData();
    }
  }

  // Upload face data (for students)
  Future<bool> uploadFaceData(List<String> images) async {
    try {
      _setLoading(true);
      clearError();

      // Use the new student-specific facial data upload API
      final response = await _apiService.studentUploadFacialData(
        images: images,
        replaceExisting: true,
      );

      _setLoading(false);
      return response['success'] ?? false;
    } catch (e) {
      _setError(e.toString());
      _setLoading(false);
      return false;
    }
  }

  // Check if user has uploaded face data
  Future<bool> hasFaceData() async {
    try {
      final response = await _apiService.getFaceData();
      return response['has_face_data'] ?? false;
    } catch (e) {
      return false;
    }
  }
}
