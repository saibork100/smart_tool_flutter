class Product {
  final String sku;
  final String? barcode;
  final String name;
  final String brand;
  final String category;
  final String type;           // tool | accessory | service
  final String? description;
  final String? imagePaths;
  final double confidenceThreshold;
  final String? shelfId;
  // Joined fields from shelves table
  final String? aisle;
  final String? bay;
  final String? zone;
  // Joined from stock table
  final int? quantityOnShelf;
  final int? quantityInBackstore;
  final String? stockStatus;   // in_stock | low_stock | out_of_stock

  const Product({
    required this.sku,
    this.barcode,
    required this.name,
    required this.brand,
    required this.category,
    required this.type,
    this.description,
    this.imagePaths,
    this.confidenceThreshold = 0.5,
    this.shelfId,
    this.aisle,
    this.bay,
    this.zone,
    this.quantityOnShelf,
    this.quantityInBackstore,
    this.stockStatus,
  });

  /// Human-readable shelf location string e.g. "A-3-B"
  String get shelfLabel {
    if (aisle == null && bay == null) return 'Unknown';
    return [aisle, bay, zone].where((s) => s != null && s.isNotEmpty).join('-');
  }

  /// True when stock is available
  bool get inStock => stockStatus == 'in_stock' || stockStatus == 'low_stock';

  factory Product.fromMap(Map<String, dynamic> map) {
    return Product(
      sku: map['sku'] as String,
      barcode: map['barcode'] as String?,
      name: map['name'] as String,
      brand: map['brand'] as String,
      category: map['category'] as String,
      type: map['type'] as String,
      description: map['description'] as String?,
      imagePaths: map['image_paths'] as String?,
      confidenceThreshold: (map['confidence_threshold'] as num?)?.toDouble() ?? 0.5,
      shelfId: map['shelf_id'] as String?,
      aisle: map['aisle'] as String?,
      bay: map['bay'] as String?,
      zone: map['zone'] as String?,
      quantityOnShelf: map['quantity_on_shelf'] as int?,
      quantityInBackstore: map['quantity_in_backstore'] as int?,
      stockStatus: map['status'] as String?,
    );
  }

  Map<String, dynamic> toMap() => {
        'sku': sku,
        'barcode': barcode,
        'name': name,
        'brand': brand,
        'category': category,
        'type': type,
        'description': description,
        'image_paths': imagePaths,
        'confidence_threshold': confidenceThreshold,
        'shelf_id': shelfId,
      };

  Product copyWith({
    String? name,
    String? brand,
    String? category,
    String? description,
    String? shelfId,
    int? quantityOnShelf,
  }) =>
      Product(
        sku: sku,
        barcode: barcode,
        name: name ?? this.name,
        brand: brand ?? this.brand,
        category: category ?? this.category,
        type: type,
        description: description ?? this.description,
        imagePaths: imagePaths,
        confidenceThreshold: confidenceThreshold,
        shelfId: shelfId ?? this.shelfId,
        aisle: aisle,
        bay: bay,
        zone: zone,
        quantityOnShelf: quantityOnShelf ?? this.quantityOnShelf,
        quantityInBackstore: quantityInBackstore,
        stockStatus: stockStatus,
      );
}
