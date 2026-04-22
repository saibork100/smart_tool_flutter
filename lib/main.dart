// Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:flutter/foundation.dart';

import 'package:shared_preferences/shared_preferences.dart';
import 'services/auth_service.dart';
import 'services/database_service.dart';
import 'services/detector_service.dart';
import 'pages/login_page.dart';
import 'pages/user_page.dart';
import 'pages/admin_page.dart';
import 'utils/app_theme.dart';
import 'utils/app_config.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Use FFI for SQLite on desktop platforms
  if (!kIsWeb &&
      (defaultTargetPlatform == TargetPlatform.windows ||
          defaultTargetPlatform == TargetPlatform.linux ||
          defaultTargetPlatform == TargetPlatform.macOS)) {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  }

  // Load saved backend URL
  final prefs = await SharedPreferences.getInstance();
  final savedUrl = prefs.getString('backend_url');
  if (savedUrl != null && savedUrl.isNotEmpty) {
    AppConfig.backendUrl = savedUrl;
  }

  // Initialise local database
  await DatabaseService.instance.init();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthService()),
        ChangeNotifierProvider(create: (_) => DetectorService()),
      ],
      child: const SmartToolApp(),
    ),
  );
}

class SmartToolApp extends StatelessWidget {
  const SmartToolApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Tool Recognition',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      home: const AuthGate(),
      routes: {
        '/login': (_) => const LoginPage(),
        '/user': (_) => const UserPage(),
        '/admin': (_) => const AdminPage(),
      },
    );
  }
}

/// Decides which page to show based on auth state.
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();

    if (!auth.isLoggedIn) return const LoginPage();
    if (auth.isAdmin) return const AdminPage();
    return const UserPage();
  }
}
