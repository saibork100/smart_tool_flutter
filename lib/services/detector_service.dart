import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import '../models/prediction_result.dart';
import '../models/product.dart';
import 'database_service.dart';
import '../utils/app_config.dart';

class DetectorService extends ChangeNotifier {
  static const String _baseUrl = AppConfig.backendUrl;

  static const Map<String, String> _labelToSku = {
    // 4mm
    '4mm_10mm': 'GAVHC410',
    '4mm_16mm': 'GAVHC416',
    '4mm_20mm': 'GAVHC420',
    '4mm_25mm': 'GAVHC425',
    '4mm_30mm': 'GAVHC430',
    '4mm_40mm': 'GAVHC440',
    '4mm_50mm': 'GAVHC450',
    // 5mm
    '5mm_10mm': 'GAVHC510',
    '5mm_16mm': 'GAVHC516',
    '5mm_20mm': 'GAVHC520',
    '5mm_25mm': 'GAVHC525',
    '5mm_30mm': 'GAVHC530',
    '5mm_40mm': 'GAVHC540',
    '5mm_50mm': 'GAVHC550',
    // 6mm
    '6mm_12mm': 'GAVHC612',
    '6mm_16mm': 'GAVHC616',
    '6mm_20mm': 'GAVHC620',
    '6mm_25mm': 'GAVHC625',
    '6mm_30mm': 'GAVHC630',
    '6mm_40mm': 'GAVHC640',
    '6mm_50mm': 'GAVHC650',
    '6mm_60mm': 'GAVHC660',
    '6mm_70mm': 'GAVHC670+',
    '6mm_80mm': 'GAVHC680+',
    '6mm_100mm': 'GAVHC6100+',
  };

  bool _isProcessing = false;
  PredictionResult? _lastResult;
  String? _errorMessage;

  bool get isProcessing => _isProcessing;
  PredictionResult? get lastResult => _lastResult;
  String? get errorMessage => _errorMessage;

  Future<PredictionResult?> detectFromFile(File imageFile) async {
    _setProcessing(true);
    _errorMessage = null;

    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$_baseUrl/detect'),
      );
      final bytes = await imageFile.readAsBytes();
      request.files.add(http.MultipartFile.fromBytes(
        'file',
        bytes,
        filename: 'image.jpg',
        contentType: MediaType('image', 'jpeg'),
      ));

      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw const SocketException('Request timed out'),
      );

      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode != 200) {
        throw Exception('Server error ${response.statusCode}');
      }

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final label = data['predicted_label'] as String?;

      Product? product;
      if (label != null) {
        final sku = _labelToSku[label] ?? label;
        product = await DatabaseService.instance.getProductBySku(sku);
      }

      _lastResult = PredictionResult.fromMap(data, product: product);
      notifyListeners();
      return _lastResult;
    } on SocketException {
      _errorMessage = 'Cannot reach local AI server. Is the Python backend running?';
    } catch (e) {
      _errorMessage = 'Detection failed: $e';
    } finally {
      _setProcessing(false);
    }
    return null;
  }

  Future<Product?> lookupByBarcode(String barcode) async {
    return DatabaseService.instance.getProductByBarcode(barcode);
  }

  Future<List<Product>> searchByName(String query) async {
    return DatabaseService.instance.searchProducts(query);
  }

  Future<bool> isBackendReachable() async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/health'))
          .timeout(const Duration(seconds: 3));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  void clearResult() {
    _lastResult = null;
    _errorMessage = null;
    notifyListeners();
  }

  void _setProcessing(bool value) {
    _isProcessing = value;
    notifyListeners();
  }
}