import 'product.dart';

class PredictionResult {
  final String predictedLabel;
  final double confidence;
  final List<TopPrediction> topPredictions;
  final Product? product;       // null when below confidence threshold
  final bool isConfident;

  const PredictionResult({
    required this.predictedLabel,
    required this.confidence,
    required this.topPredictions,
    this.product,
    required this.isConfident,
  });

  factory PredictionResult.fromMap(Map<String, dynamic> map, {Product? product}) {
    final tops = (map['top_predictions'] as List<dynamic>? ?? [])
        .map((e) => TopPrediction.fromMap(e as Map<String, dynamic>))
        .toList();

    final confidence = (map['confidence'] as num).toDouble();

    return PredictionResult(
      predictedLabel: map['predicted_label'] as String? ?? 'Unknown',
      confidence: confidence,
      topPredictions: tops,
      product: product,
      isConfident: confidence >= (map['threshold'] as num? ?? 0.5),
    );
  }
}

class TopPrediction {
  final String label;
  final double confidence;

  const TopPrediction({required this.label, required this.confidence});

  factory TopPrediction.fromMap(Map<String, dynamic> map) => TopPrediction(
        label: map['label'] as String,
        confidence: (map['confidence'] as num).toDouble(),
      );
}
