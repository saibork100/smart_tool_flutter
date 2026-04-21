// Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
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
    // M4
    '4mm_10mm': 'GAVHC410',   '4mm_16mm': 'GAVHC416',   '4mm_20mm': 'GAVHC420',
    '4mm_25mm': 'GAVHC425',   '4mm_30mm': 'GAVHC430',   '4mm_40mm': 'GAVHC440',
    '4mm_50mm': 'GAVHC450',
    // M5
    '5mm_10mm': 'GAVHC510',   '5mm_16mm': 'GAVHC516',   '5mm_20mm': 'GAVHC520',
    '5mm_25mm': 'GAVHC525',   '5mm_30mm': 'GAVHC530',   '5mm_40mm': 'GAVHC540',
    '5mm_50mm': 'GAVHC550',
    // M6
    '6mm_12mm': 'GAVHC612',   '6mm_16mm': 'GAVHC616',   '6mm_20mm': 'GAVHC620',
    '6mm_25mm': 'GAVHC625',   '6mm_30mm': 'GAVHC630',   '6mm_40mm': 'GAVHC640',
    '6mm_50mm': 'GAVHC650',   '6mm_60mm': 'GAVHC660',   '6mm_70mm': 'GAVHC670',
    '6mm_80mm': 'GAVHC680',   '6mm_100mm': 'GAVHC6100', '6mm_120mm': 'GAVHC6120',
    // M8
    '8mm_16mm': 'GAVHC816',   '8mm_20mm': 'GAVHC820',   '8mm_25mm': 'GAVHC825',
    '8mm_30mm': 'GAVHC830',   '8mm_40mm': 'GAVHC840',   '8mm_50mm': 'GAVHC850',
    '8mm_60mm': 'GAVHC860',   '8mm_70mm': 'GAVHC870',   '8mm_80mm': 'GAVHC880',
    '8mm_100mm': 'GAVHC8100', '8mm_120mm': 'GAVHC8120', '8mm_150mm': 'GAVHC8150',
    // M10
    '10mm_16mm': 'GAVHC1016',   '10mm_20mm': 'GAVHC1020',   '10mm_25mm': 'GAVHC1025',
    '10mm_30mm': 'GAVHC1030',   '10mm_40mm': 'GAVHC1040',   '10mm_45mm': 'GAVHC1045',
    '10mm_50mm': 'GAVHC1050',   '10mm_60mm': 'GAVHC1060',   '10mm_70mm': 'GAVHC1070',
    '10mm_80mm': 'GAVHC1080',   '10mm_90mm': 'GAVHC1090',   '10mm_100mm': 'GAVHC10100',
    '10mm_120mm': 'GAVHC10120', '10mm_140mm': 'GAVHC10140', '10mm_150mm': 'GAVHC10150',
    '10mm_160mm': 'GAVHC10160',
    // M12
    '12mm_20mm': 'GAVHC1220',   '12mm_25mm': 'GAVHC1225',   '12mm_30mm': 'GAVHC1230',
    '12mm_40mm': 'GAVHC1240',   '12mm_45mm': 'GAVHC1245',   '12mm_50mm': 'GAVHC1250',
    '12mm_60mm': 'GAVHC1260',   '12mm_70mm': 'GAVHC1270',   '12mm_80mm': 'GAVHC1280',
    '12mm_90mm': 'GAVHC1290',   '12mm_100mm': 'GAVHC12100', '12mm_120mm': 'GAVHC12120',
    '12mm_140mm': 'GAVHC12140', '12mm_150mm': 'GAVHC12150', '12mm_160mm': 'GAVHC12160',
    '12mm_180mm': 'GAVHC12180',
    // M14
    '14mm_25mm': 'GAVHC1425',   '14mm_30mm': 'GAVHC1430',   '14mm_35mm': 'GAVHC1435',
    '14mm_40mm': 'GAVHC1440',   '14mm_45mm': 'GAVHC1445',   '14mm_50mm': 'GAVHC1450',
    '14mm_60mm': 'GAVHC1460',   '14mm_70mm': 'GAVHC1470',   '14mm_80mm': 'GAVHC1480',
    '14mm_90mm': 'GAVHC1490+',  '14mm_100mm': 'GAVHC14100', '14mm_120mm': 'GAVHC14120',
    '14mm_140mm': 'GAVHC14140', '14mm_150mm': 'GAVHC14150', '14mm_160mm': 'GAVHC14160',
    '14mm_180mm': 'GAVHC14180', '14mm_200mm': 'GAVHC14200', '14mm_220mm': 'GAVHC14220',
    // M16
    '16mm_25mm': 'GAVHC1625',   '16mm_30mm': 'GAVHC1630',   '16mm_35mm': 'GAVHC1635',
    '16mm_40mm': 'GAVHC1640',   '16mm_45mm': 'GAVHC1645',   '16mm_50mm': 'GAVHC1650',
    '16mm_55mm': 'GAVHC1655',   '16mm_60mm': 'GAVHC1660',   '16mm_70mm': 'GAVHC1670',
    '16mm_80mm': 'GAVHC1680',   '16mm_90mm': 'GAVHC1690',   '16mm_100mm': 'GAVHC16100',
    '16mm_120mm': 'GAVHC16120', '16mm_130mm': 'GAVHC16130', '16mm_140mm': 'GAVHC16140',
    '16mm_150mm': 'GAVHC16150', '16mm_160mm': 'GAVHC16160', '16mm_180mm': 'GAVHC16180',
    '16mm_200mm': 'GAVHC16200', '16mm_220mm': 'GAVHC16220', '16mm_240mm': 'GAVHC16240',
    '16mm_260mm': 'GAVHC16260',
    // M18
    '18mm_40mm': 'GAVHC1840',   '18mm_50mm': 'GAVHC1850',   '18mm_60mm': 'GAVHC1860',
    '18mm_70mm': 'GAVHC1870',   '18mm_80mm': 'GAVHC1880',   '18mm_90mm': 'GAVHC1890',
    '18mm_100mm': 'GAVHC18100', '18mm_120mm': 'GAVHC18120', '18mm_140mm': 'GAVHC18140',
    '18mm_160mm': 'GAVHC18160', '18mm_180mm': 'GAVHC18180', '18mm_200mm': 'GAVHC18200',
    // M20
    '20mm_40mm': 'GAVHC2040',   '20mm_50mm': 'GAVHC2050',   '20mm_60mm': 'GAVHC2060',
    '20mm_70mm': 'GAVHC2070',   '20mm_80mm': 'GAVHC2080',   '20mm_90mm': 'GAVHC2090',
    '20mm_100mm': 'GAVHC20100', '20mm_110mm': 'GAVHC20110+','20mm_120mm': 'GAVHC20120',
    '20mm_130mm': 'GAVHC20130', '20mm_140mm': 'GAVHC20140', '20mm_150mm': 'GAVHC20150',
    '20mm_160mm': 'GAVHC20160', '20mm_180mm': 'GAVHC20180', '20mm_200mm': 'GAVHC20200',
    '20mm_220mm': 'GAVHC20220', '20mm_240mm': 'GAVHC20240',
    // M22
    '22mm_50mm': 'GAVHC2250',   '22mm_60mm': 'GAVHC2260',   '22mm_70mm': 'GAVHC2270',
    '22mm_80mm': 'GAVHC2280',   '22mm_90mm': 'GAVHC2290',   '22mm_100mm': 'GAVHC22100',
    '22mm_120mm': 'GAVHC22120', '22mm_140mm': 'GAVHC22140', '22mm_160mm': 'GAVHC22160',
    '22mm_180mm': 'GAVHC22180',
    // M24
    '24mm_50mm': 'GAVHC2450',   '24mm_60mm': 'GAVHC2460',   '24mm_70mm': 'GAVHC2470',
    '24mm_80mm': 'GAVHC2480',   '24mm_90mm': 'GAVHC2490',   '24mm_100mm': 'GAVHC24100',
    '24mm_120mm': 'GAVHC24120', '24mm_140mm': 'GAVHC24140', '24mm_160mm': 'GAVHC24160',
    '24mm_180mm': 'GAVHC24180', '24mm_200mm': 'GAVHC24200', '24mm_220mm': 'GAVHC24220',
    '24mm_260mm': 'GAVHC24260',
    // M27
    '27mm_60mm': 'GAVHC2760',   '27mm_70mm': 'GAVHC2770',   '27mm_80mm': 'GAVHC2780',
    '27mm_100mm': 'GAVHC27100', '27mm_120mm': 'GAVHC27120', '27mm_130mm': 'GAVHC27130',
    '27mm_140mm': 'GAVHC27140', '27mm_160mm': 'GAVHC27160', '27mm_220mm': 'GAVHC27220',
    '27mm_280mm': 'GAVHC27280',
    // M30
    '30mm_60mm': 'GAVHC3060',   '30mm_70mm': 'GAVHC3070',   '30mm_80mm': 'GAVHC3080',
    '30mm_90mm': 'GAVHC3090',   '30mm_100mm': 'GAVHC30100', '30mm_120mm': 'GAVHC30120',
    '30mm_130mm': 'GAVHC30130', '30mm_140mm': 'GAVHC30140', '30mm_150mm': 'GAVHC30150',
    '30mm_160mm': 'GAVHC30160', '30mm_180mm': 'GAVHC30180', '30mm_200mm': 'GAVHC30200',
    // M33
    '33mm_100mm': 'GAVHC33100', '33mm_120mm': 'GAVHC33120', '33mm_140mm': 'GAVHC33140',
    '33mm_180mm': 'GAVHC33180', '33mm_200mm': 'GAVHC33200', '33mm_220mm': 'GAVHC33220',
    '33mm_250mm': 'GAVHC33250',
    // M36
    '36mm_120mm': 'GAVHC36120', '36mm_160mm': 'GAVHC36160',
    // M39
    '39mm_160mm': 'GAVHC39160',
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

      final data  = jsonDecode(response.body) as Map<String, dynamic>;
      final label = data['predicted_label'] as String?;

      // ── Parent-class strategy (YOLO11): available_sizes is populated ─────────
      // When the model returns a diameter class, the API pre-fetches all size
      // variants from the DB. The Flutter card shows a scrollable size list.
      // Fallback: old model returns a specific size label → look up single product.
      Product? product;
      final hasSizes = (data['available_sizes'] as List<dynamic>? ?? []).isNotEmpty;
      if (!hasSizes && label != null) {
        // Legacy path: old model output like "8mm_70mm" → look up specific product
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

  Future<PredictionResult?> measureFromFile(File imageFile) async {
    _setProcessing(true);
    _errorMessage = null;

    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$_baseUrl/measure'),
      );
      final bytes = await imageFile.readAsBytes();
      request.files.add(http.MultipartFile.fromBytes(
        'file',
        bytes,
        filename: 'image.jpg',
        contentType: MediaType('image', 'jpeg'),
      ));

      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 15),
        onTimeout: () => throw const SocketException('Request timed out'),
      );
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 422) {
        // Ruler not detected — tell the user clearly
        final body = jsonDecode(response.body);
        _errorMessage = body['detail'] ?? 'Ruler not detected in image.';
        notifyListeners();
        return null;
      }
      if (response.statusCode != 200) {
        throw Exception('Server error ${response.statusCode}');
      }

      final data   = jsonDecode(response.body) as Map<String, dynamic>;
      final label  = data['nearest_label'] as String?;
      final conf   = data['confidence'] as String? ?? 'low';
      final lenMm  = (data['measured_length_mm']   as num?)?.toDouble() ?? 0.0;
      final diaMm  = (data['measured_diameter_mm'] as num?)?.toDouble() ?? 0.0;

      // Build a PredictionResult compatible with the existing UI
      Product? product;
      final productMap = data['product'] as Map<String, dynamic>?;
      if (productMap != null) {
        product = Product.fromMap(productMap);
      }

      // Confidence string → numeric for PredictionResult
      final confValue = conf == 'high' ? 0.90 : conf == 'medium' ? 0.65 : 0.40;

      _lastResult = PredictionResult(
        predictedLabel: label ?? 'Unknown',
        confidence:     confValue,
        topPredictions: [],
        product:        product,
        isConfident:    true,
        measurementNote: 'Ruler: ${diaMm.toStringAsFixed(1)}mm × ${lenMm.toStringAsFixed(1)}mm',
      );
      notifyListeners();
      return _lastResult;
    } on SocketException {
      _errorMessage = 'Cannot reach local AI server. Is the Python backend running?';
    } catch (e) {
      _errorMessage = 'Measurement failed: $e';
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

  Future<List<String>> getModelClasses() async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/model/classes'))
          .timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return (data['classes'] as List).cast<String>();
      }
    } catch (_) {}
    return [];
  }

  Future<bool> reportDetection({
    required File imageFile,
    required String wrongClass,
    required String correctClass,
    String reportedBy = '',
  }) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$_baseUrl/report'),
      );
      final bytes = await imageFile.readAsBytes();
      request.files.add(http.MultipartFile.fromBytes(
        'file',
        bytes,
        filename: 'report.jpg',
        contentType: MediaType('image', 'jpeg'),
      ));
      request.fields['wrong_class']   = wrongClass;
      request.fields['correct_class'] = correctClass;
      request.fields['reported_by']   = reportedBy;

      final streamed = await request.send().timeout(const Duration(seconds: 15));
      return streamed.statusCode == 200;
    } catch (_) {
      return false;
    }
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