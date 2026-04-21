// Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
import 'package:flutter/material.dart';

class AppTheme {
  static const Color primaryColor = Color(0xFF1E3A5F);   // Dark navy
  static const Color accentColor  = Color(0xFFF5A623);   // Tool orange
  static const Color successColor = Color(0xFF27AE60);
  static const Color errorColor   = Color(0xFFE74C3C);
  static const Color surfaceColor = Color(0xFFF8F9FA);

  static ThemeData get lightTheme => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: primaryColor,
          secondary: accentColor,
          surface: surfaceColor,
        ),
        textTheme: const TextTheme(
          displayLarge:  TextStyle(fontSize: 48),
          displayMedium: TextStyle(fontSize: 40),
          displaySmall:  TextStyle(fontSize: 34),
          headlineLarge: TextStyle(fontSize: 26),
          headlineMedium:TextStyle(fontSize: 22),
          headlineSmall: TextStyle(fontSize: 18),
          titleLarge:    TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          titleMedium:   TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
          titleSmall:    TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
          bodyLarge:     TextStyle(fontSize: 13),
          bodyMedium:    TextStyle(fontSize: 12),
          bodySmall:     TextStyle(fontSize: 11),
          labelLarge:    TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
          labelMedium:   TextStyle(fontSize: 11),
          labelSmall:    TextStyle(fontSize: 10),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: primaryColor,
          foregroundColor: Colors.white,
          elevation: 0,
          titleTextStyle: TextStyle(
            color: Colors.white,
            fontSize: 17,
            fontWeight: FontWeight.w600,
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: primaryColor,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
            ),
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 24),
          ),
        ),
        cardTheme: CardThemeData(
          elevation: 2,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          filled: true,
          fillColor: Colors.white,
        ),
      );

  static ThemeData get darkTheme => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: primaryColor,
          brightness: Brightness.dark,
          secondary: accentColor,
        ),
      );
}
