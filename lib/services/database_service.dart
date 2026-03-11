import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:http/http.dart' as http;
import '../models/product.dart';
import '../utils/app_config.dart';

class DatabaseService {
  DatabaseService._();
  static final DatabaseService instance = DatabaseService._();

  Database? _db;

  static const String _baseUrl = AppConfig.backendUrl;

  // ── Local SQLite (admin session only) ─────────────────────────────────────

  Future<void> init() async {
    final dbPath = await getDatabasesPath();
    print('DATABASE PATH: $dbPath');
    final path = join(dbPath, 'smart_tool.db');

    _db = await openDatabase(
      path,
      version: 2,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  Database get db {
    assert(_db != null, 'DatabaseService.init() must be called before use');
    return _db!;
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE admin_users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        email         TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name          TEXT,
        role          TEXT DEFAULT 'admin',
        is_active     INTEGER DEFAULT 1,
        created_at    TEXT DEFAULT (datetime('now'))
      )
    ''');
    await db.insert('admin_users', {
      'email': 'trikimahoud86@gmail.com',
      'password_hash': '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
      'name': 'Admin',
      'role': 'admin',
      'is_active': 1,
    });
  }

  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    if (oldVersion < 2) {
      final existing = await db.query('admin_users',
          where: 'email = ?', whereArgs: ['trikimahoud86@gmail.com']);
      if (existing.isEmpty) {
        await db.insert('admin_users', {
          'email': 'trikimahoud86@gmail.com',
          'password_hash': '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
          'name': 'Admin',
          'role': 'admin',
          'is_active': 1,
        });
      }
    }
  }

  // ── Products (from API) ────────────────────────────────────────────────────

  Future<List<Product>> getAllProducts() async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/products'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as List;
        return data.map((m) => Product.fromMap(Map<String, dynamic>.from(m))).toList();
      }
    } catch (e) {
      print('getAllProducts error: $e');
    }
    return [];
  }

  Future<Product?> getProductBySku(String sku) async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/products/$sku'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        return Product.fromMap(Map<String, dynamic>.from(jsonDecode(response.body)));
      }
    } catch (e) {
      print('getProductBySku error: $e');
    }
    return null;
  }

  Future<Product?> getProductByBarcode(String barcode) async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/products/barcode/$barcode'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        return Product.fromMap(Map<String, dynamic>.from(jsonDecode(response.body)));
      }
    } catch (e) {
      print('getProductByBarcode error: $e');
    }
    return null;
  }

  Future<List<Product>> searchProducts(String query) async {
    try {
      final uri = Uri.parse('$_baseUrl/products').replace(
          queryParameters: {'search': query});
      final response = await http
          .get(uri)
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as List;
        return data.map((m) => Product.fromMap(Map<String, dynamic>.from(m))).toList();
      }
    } catch (e) {
      print('searchProducts error: $e');
    }
    return [];
  }

  Future<void> upsertProduct(Product p) async {
    try {
      await http.post(
        Uri.parse('$_baseUrl/products'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'sku': p.sku,
          'barcode': p.barcode,
          'name': p.name,
          'brand': p.brand,
          'category': p.category,
          'type': p.type,
          'description': p.description,
          'shelf_id': p.shelfId,
        }),
      ).timeout(const Duration(seconds: 10));
    } catch (e) {
      print('upsertProduct error: $e');
    }
  }

  Future<void> deleteProduct(String sku) async {
    try {
      await http
          .delete(Uri.parse('$_baseUrl/products/$sku'))
          .timeout(const Duration(seconds: 10));
    } catch (e) {
      print('deleteProduct error: $e');
    }
  }

  // ── Stock (from API) ───────────────────────────────────────────────────────

  Future<void> updateStock(String sku, int onShelf, int inBackstore) async {
    try {
      await http.put(
        Uri.parse('$_baseUrl/stock/$sku'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'quantity_on_shelf': onShelf,
          'quantity_in_backstore': inBackstore,
        }),
      ).timeout(const Duration(seconds: 10));
    } catch (e) {
      print('updateStock error: $e');
    }
  }

  // ── Shelves (from API) ─────────────────────────────────────────────────────

  Future<List<Map<String, dynamic>>> getShelves() async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/shelves'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as List;
        return data.map((m) => Map<String, dynamic>.from(m)).toList();
      }
    } catch (e) {
      print('getShelves error: $e');
    }
    return [];
  }

  Future<void> upsertShelf(Map<String, dynamic> shelf) async {
    try {
      await http.post(
        Uri.parse('$_baseUrl/shelves'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(shelf),
      ).timeout(const Duration(seconds: 10));
    } catch (e) {
      print('upsertShelf error: $e');
    }
  }

  Future<void> deleteShelf(String shelfId) async {
    try {
      await http
          .delete(Uri.parse('$_baseUrl/shelves/$shelfId'))
          .timeout(const Duration(seconds: 10));
    } catch (e) {
      print('deleteShelf error: $e');
    }
  }
}
