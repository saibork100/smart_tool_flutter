// Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
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
      version: 3,
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
    await _createProductsCache(db);
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
    if (oldVersion < 3) {
      await _createProductsCache(db);
    }
  }

  Future<void> _createProductsCache(Database db) async {
    await db.execute('''
      CREATE TABLE IF NOT EXISTS products_cache (
        sku                   TEXT PRIMARY KEY,
        barcode               TEXT,
        name                  TEXT NOT NULL,
        brand                 TEXT NOT NULL,
        category              TEXT NOT NULL,
        type                  TEXT NOT NULL,
        description           TEXT,
        image_paths           TEXT,
        confidence_threshold  REAL DEFAULT 0.5,
        shelf_id              TEXT,
        aisle                 TEXT,
        bay                   TEXT,
        zone                  TEXT,
        quantity_on_shelf     INTEGER,
        quantity_in_backstore INTEGER,
        status                TEXT,
        cached_at             TEXT DEFAULT (datetime('now'))
      )
    ''');
  }

  // ── Product cache helpers ──────────────────────────────────────────────────

  Future<void> _cacheProducts(List<Product> products) async {
    final batch = db.batch();
    for (final p in products) {
      batch.insert('products_cache', {
        'sku': p.sku,
        'barcode': p.barcode,
        'name': p.name,
        'brand': p.brand,
        'category': p.category,
        'type': p.type,
        'description': p.description,
        'image_paths': p.imagePaths,
        'confidence_threshold': p.confidenceThreshold,
        'shelf_id': p.shelfId,
        'aisle': p.aisle,
        'bay': p.bay,
        'zone': p.zone,
        'quantity_on_shelf': p.quantityOnShelf,
        'quantity_in_backstore': p.quantityInBackstore,
        'status': p.stockStatus,
        'cached_at': DateTime.now().toIso8601String(),
      }, conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await batch.commit(noResult: true);
  }

  Product _productFromCacheRow(Map<String, dynamic> row) =>
      Product.fromMap({...row, 'status': row['status']});

  Future<List<Product>> _getCachedProducts() async {
    final rows = await db.query('products_cache', orderBy: 'name ASC');
    return rows.map(_productFromCacheRow).toList();
  }

  Future<Product?> _getCachedBySku(String sku) async {
    final rows = await db.query('products_cache',
        where: 'sku = ?', whereArgs: [sku], limit: 1);
    return rows.isEmpty ? null : _productFromCacheRow(rows.first);
  }

  Future<Product?> _getCachedByBarcode(String barcode) async {
    final rows = await db.query('products_cache',
        where: 'barcode = ?', whereArgs: [barcode], limit: 1);
    return rows.isEmpty ? null : _productFromCacheRow(rows.first);
  }

  Future<List<Product>> _searchCached(String query) async {
    final q = '%${query.toLowerCase()}%';
    final rows = await db.rawQuery('''
      SELECT * FROM products_cache
      WHERE lower(name) LIKE ? OR lower(sku) LIKE ? OR lower(brand) LIKE ?
      ORDER BY name ASC
    ''', [q, q, q]);
    return rows.map(_productFromCacheRow).toList();
  }

  // ── Products (API-first, SQLite fallback) ────────────────────────────────

  Future<List<Product>> getAllProducts() async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/products'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final products = (jsonDecode(response.body) as List)
            .map((m) => Product.fromMap(Map<String, dynamic>.from(m)))
            .toList();
        await _cacheProducts(products);
        return products;
      }
    } catch (_) {}
    return _getCachedProducts();
  }

  Future<Product?> getProductBySku(String sku) async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/products/$sku'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final p = Product.fromMap(Map<String, dynamic>.from(jsonDecode(response.body)));
        await _cacheProducts([p]);
        return p;
      }
    } catch (_) {}
    return _getCachedBySku(sku);
  }

  Future<Product?> getProductByBarcode(String barcode) async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/products/barcode/$barcode'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final p = Product.fromMap(Map<String, dynamic>.from(jsonDecode(response.body)));
        await _cacheProducts([p]);
        return p;
      }
    } catch (_) {}
    return _getCachedByBarcode(barcode);
  }

  Future<List<Product>> searchProducts(String query) async {
    try {
      final uri = Uri.parse('$_baseUrl/products')
          .replace(queryParameters: {'search': query});
      final response = await http.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final products = (jsonDecode(response.body) as List)
            .map((m) => Product.fromMap(Map<String, dynamic>.from(m)))
            .toList();
        await _cacheProducts(products);
        return products;
      }
    } catch (_) {}
    return _searchCached(query);
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
