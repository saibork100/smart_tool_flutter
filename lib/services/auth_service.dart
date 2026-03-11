import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:crypto/crypto.dart';
import 'dart:convert';
import 'database_service.dart';

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
    final hash = _hashPassword(password);
    final rows = await DatabaseService.instance.db.query(
      'admin_users',
      where: 'email = ? AND password_hash = ? AND is_active = 1',
      whereArgs: [email, hash],
    );
    if (rows.isEmpty) return false;

    final user = rows.first;
    await _saveSession(
      email: email,
      name: user['name'] as String? ?? email,
      isAdmin: true,
    );
    return true;
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
    final oldHash = _hashPassword(oldPassword);
    final rows = await DatabaseService.instance.db.query(
      'admin_users',
      where: 'email = ? AND password_hash = ?',
      whereArgs: [email, oldHash],
    );
    if (rows.isEmpty) return false;

    final newHash = _hashPassword(newPassword);
    await DatabaseService.instance.db.update(
      'admin_users',
      {'password_hash': newHash},
      where: 'email = ?',
      whereArgs: [email],
    );
    return true;
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
