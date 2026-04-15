import 'product.dart';

// ── Available size entry returned by /detect (parent-class strategy) ──────────
// When the model identifies a bolt diameter (e.g. M8), the API returns every
// M8 size variant in stock so the user can select the exact length they need.
class AvailableSize {
  final String sku;
  final String sizeLabel;       // "M8 × 70mm"
  final String shelfLabel;      // "A-2-B"  (empty → "—")
  final int? qtyOnShelf;
  final int? qtyInBackstore;
  final String? status;         // 'in_stock' | 'low_stock' | 'out_of_stock' | null

  const AvailableSize({
    required this.sku,
    required this.sizeLabel,
    required this.shelfLabel,
    this.qtyOnShelf,
    this.qtyInBackstore,
    this.status,
  });

  factory AvailableSize.fromMap(Map<String, dynamic> map) => AvailableSize(
        sku:              map['sku']         as String,
        sizeLabel:        map['size_label']  as String,
        shelfLabel:       map['shelf_label'] as String? ?? '—',
        qtyOnShelf:       map['qty_on_shelf']      as int?,
        qtyInBackstore:   map['qty_in_backstore']  as int?,
        status:           map['status']            as String?,
      );

  bool get inStock => status == 'in_stock' || status == 'low_stock';
}

// ── Main prediction result ────────────────────────────────────────────────────
class PredictionResult {
  final String predictedLabel;
  final double confidence;
  final List<TopPrediction> topPredictions;
  final Product? product;         // set when label maps to a single known SKU
  final bool isConfident;
  final String? measurementNote;  // "Ruler: 8.2mm × 69.5mm" — ruler mode only

  // ── YOLO11 parent-class fields ─────────────────────────────────────────────
  // When the model detects a diameter class (e.g. "bolt_M8"), these are filled.
  // The UI shows the size list instead of a single product card.
  final String? parentClass;      // "bolt_M8"
  final String? displayName;      // "Hex Bolt M8"
  final List<AvailableSize> availableSizes;  // all M8 sizes from DB

  const PredictionResult({
    required this.predictedLabel,
    required this.confidence,
    required this.topPredictions,
    this.product,
    required this.isConfident,
    this.measurementNote,
    this.parentClass,
    this.displayName,
    this.availableSizes = const [],
  });

  /// True when the new parent-class strategy is active (size list available).
  bool get hasSizeList => availableSizes.isNotEmpty;

  factory PredictionResult.fromMap(Map<String, dynamic> map, {Product? product}) {
    final tops = (map['top_predictions'] as List<dynamic>? ?? [])
        .map((e) => TopPrediction.fromMap(e as Map<String, dynamic>))
        .toList();

    final confidence = (map['confidence'] as num).toDouble();

    final sizes = (map['available_sizes'] as List<dynamic>? ?? [])
        .map((e) => AvailableSize.fromMap(e as Map<String, dynamic>))
        .toList();

    return PredictionResult(
      predictedLabel: map['predicted_label'] as String? ?? 'Unknown',
      confidence:     confidence,
      topPredictions: tops,
      product:        product,
      isConfident:    confidence >= (map['threshold'] as num? ?? 0.5),
      parentClass:    map['parent_class']  as String?,
      displayName:    map['display_name']  as String?,
      availableSizes: sizes,
    );
  }
}

class TopPrediction {
  final String label;
  final double confidence;

  const TopPrediction({required this.label, required this.confidence});

  factory TopPrediction.fromMap(Map<String, dynamic> map) => TopPrediction(
        label:      map['label']      as String,
        confidence: (map['confidence'] as num).toDouble(),
      );
}
