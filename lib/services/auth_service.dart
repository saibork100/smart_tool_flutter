// Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../utils/app_config.dart';

class AuthService extends ChangeNotifier {
  bool _isLoggedIn = false;
  bool _isAdmin = false;
  String? _userEmail;
  String? _userName;

  bool get isLoggedIn => _isLoggedIn;
  bool get isAdmin => _isAdmin;
  String? get userEmail => _userEmail;
  String? get userName => _userName;

  AuthService() {
    _restoreSession();
  }

  // ── Public methods ──────────────────────────────────────────────────────────

  Future<bool> loginAdmin({
    required String email,
    required String password,
  }) async {
    try {
      final hash = _hashPassword(password);
      final response = await http.post(
        Uri.parse('${AppConfig.backendUrl}/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password_hash': hash}),
      );
      if (response.statusCode != 200) return false;
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      await _saveSession(
        email: email,
        name: data['name'] as String? ?? email,
        isAdmin: true,
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Staff login — no password required (magic-link style like existing system).
  Future<void> loginAsStaff({required String name}) async {
    await _saveSession(email: '', name: name, isAdmin: false);
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    _isLoggedIn = false;
    _isAdmin = false;
    _userEmail = null;
    _userName = null;
    notifyListeners();
  }

  Future<bool> changePassword({
    required String email,
    required String oldPassword,
    required String newPassword,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.backendUrl}/auth/change-password'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email,
          'old_password_hash': _hashPassword(oldPassword),
          'new_password_hash': _hashPassword(newPassword),
        }),
      );
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Private helpers ─────────────────────────────────────────────────────────

  String _hashPassword(String password) {
    final bytes = utf8.encode(password);
    return sha256.convert(bytes).toString();
  }

  Future<void> _saveSession({
    required String email,
    required String name,
    required bool isAdmin,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('user_email', email);
    await prefs.setString('user_name', name);
    await prefs.setBool('is_admin', isAdmin);

    _userEmail = email;
    _userName = name;
    _isAdmin = isAdmin;
    _isLoggedIn = true;
    notifyListeners();
  }

  Future<void> _restoreSession() async {
    final prefs = await SharedPreferences.getInstance();
    final email = prefs.getString('user_email');
    if (email == null) return;

    _userEmail = email;
    _userName = prefs.getString('user_name');
    _isAdmin = prefs.getBool('is_admin') ?? false;
    _isLoggedIn = true;
    notifyListeners();
  }
}
