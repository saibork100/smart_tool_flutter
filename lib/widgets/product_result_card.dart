import 'package:flutter/material.dart';
import '../models/product.dart';
import '../utils/app_theme.dart';

/// Shown on the user page after a successful detection or barcode scan.
class ProductResultCard extends StatelessWidget {
  final Product product;
  final double? confidence;

  const ProductResultCard({super.key, required this.product, this.confidence});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Handle bar
          Center(
            child: Container(
              width: 40, height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Product name & brand
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                radius: 28,
                backgroundColor: AppTheme.primaryColor,
                child: Text(
                  product.brand.isNotEmpty ? product.brand[0].toUpperCase() : '?',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      product.name,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    Text(product.brand, style: TextStyle(color: Colors.grey.shade600)),
                    if (confidence != null)
                      Text(
                        'Confidence: ${(confidence! * 100).toStringAsFixed(1)}%',
                        style: const TextStyle(
                          color: AppTheme.successColor,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          const Divider(),

          // Shelf location
          _InfoRow(
            icon: Icons.location_on_outlined,
            label: 'Shelf Location',
            value: product.shelfLabel,
            valueStyle: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: AppTheme.primaryColor,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 12),

          // Stock
          _InfoRow(
            icon: Icons.inventory_outlined,
            label: 'Stock on Shelf',
            value: '${product.quantityOnShelf ?? "—"}',
          ),
          const SizedBox(height: 4),
          _InfoRow(
            icon: Icons.warehouse_outlined,
            label: 'Backstore',
            value: '${product.quantityInBackstore ?? "—"}',
          ),
          const SizedBox(height: 12),

          // Status badge
          _StatusBadge(status: product.stockStatus),
          const SizedBox(height: 12),

          // Extra details
          if (product.description != null && product.description!.isNotEmpty) ...[
            const Divider(),
            Text(
              product.description!,
              style: TextStyle(color: Colors.grey.shade700),
            ),
          ],

          const SizedBox(height: 8),
          _InfoRow(
            icon: Icons.category_outlined,
            label: 'Category',
            value: product.category,
          ),
          _InfoRow(
            icon: Icons.qr_code,
            label: 'SKU',
            value: product.sku,
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final TextStyle? valueStyle;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
    this.valueStyle,
  });

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            Icon(icon, size: 18, color: Colors.grey.shade600),
            const SizedBox(width: 8),
            Text('$label: ', style: TextStyle(color: Colors.grey.shade600)),
            Text(value, style: valueStyle),
          ],
        ),
      );
}

class _StatusBadge extends StatelessWidget {
  final String? status;
  const _StatusBadge({this.status});

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (status) {
      'in_stock'     => ('In Stock', AppTheme.successColor),
      'low_stock'    => ('Low Stock', Colors.orange),
      'out_of_stock' => ('Out of Stock', AppTheme.errorColor),
      _              => ('Unknown', Colors.grey),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, size: 10, color: color),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(color: color, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
