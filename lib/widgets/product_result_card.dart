import 'package:flutter/material.dart';
import '../models/product.dart';
import '../models/prediction_result.dart';
import '../utils/app_theme.dart';

/// Shown on the user page after a successful detection or barcode scan.
///
/// Two display modes:
///  1. **Size-list mode** — when [availableSizes] is non-empty (YOLO11 parent-class
///     strategy). Shows all size variants for the detected diameter; tapping one
///     expands to show shelf location and stock.
///  2. **Single-product mode** — legacy / ruler / barcode result with a known SKU.
class ProductResultCard extends StatefulWidget {
  final Product? product;
  final double? confidence;
  final List<TopPrediction> alternatives; // top-2 to top-5 predictions
  final String? measurementNote;          // e.g. "Ruler: 8.2mm × 69.5mm"

  // ── YOLO11 parent-class mode ────────────────────────────────────────────────
  final String? displayName;             // "Hex Bolt M8"
  final List<AvailableSize> availableSizes;

  const ProductResultCard({
    super.key,
    this.product,
    this.confidence,
    this.alternatives = const [],
    this.measurementNote,
    this.displayName,
    this.availableSizes = const [],
  });

  @override
  State<ProductResultCard> createState() => _ProductResultCardState();
}

class _ProductResultCardState extends State<ProductResultCard> {
  String? _expandedSku;

  @override
  Widget build(BuildContext context) {
    if (widget.availableSizes.isNotEmpty) {
      return _buildSizeListCard(context);
    }
    return _buildSingleProductCard(context);
  }

  // ── Mode 1: size list (YOLO11 parent-class) ─────────────────────────────────

  Widget _buildSizeListCard(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _handleBar(),
          const SizedBox(height: 16),

          // Header: detected type + confidence
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.primaryColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.bolt, color: AppTheme.primaryColor, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.displayName ?? 'Fastener detected',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    if (widget.confidence != null)
                      Text(
                        'Confidence: ${(widget.confidence! * 100).toStringAsFixed(1)}%',
                        style: TextStyle(
                          color: _confidenceColor(widget.confidence!),
                          fontWeight: FontWeight.w500,
                          fontSize: 13,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Instruction
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.blue.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.blue.shade200),
            ),
            child: Row(
              children: [
                Icon(Icons.touch_app, size: 14, color: Colors.blue.shade700),
                const SizedBox(width: 6),
                Text(
                  'Tap the length that matches your bolt',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.blue.shade700,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          const Divider(),

          // Size list
          LimitedBox(
            maxHeight: 340,
            child: ListView.separated(
              shrinkWrap: true,
              itemCount: widget.availableSizes.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, i) {
                final size = widget.availableSizes[i];
                final expanded = _expandedSku == size.sku;
                return _SizeTile(
                  size: size,
                  expanded: expanded,
                  onTap: () => setState(
                    () => _expandedSku = expanded ? null : size.sku,
                  ),
                );
              },
            ),
          ),

          const SizedBox(height: 16),
        ],
      ),
    );
  }

  // ── Mode 2: single product (legacy / ruler / barcode) ──────────────────────

  Widget _buildSingleProductCard(BuildContext context) {
    final product = widget.product;
    if (product == null) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _handleBar(),
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
                    if (widget.measurementNote != null)
                      Container(
                        margin: const EdgeInsets.only(top: 4),
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: Colors.blue.shade50,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: Colors.blue.shade200),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.straighten, size: 12, color: Colors.blue.shade700),
                            const SizedBox(width: 4),
                            Text(
                              widget.measurementNote!,
                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.blue.shade700,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      )
                    else if (widget.confidence != null)
                      Text(
                        'Confidence: ${(widget.confidence! * 100).toStringAsFixed(1)}%',
                        style: TextStyle(
                          color: _confidenceColor(widget.confidence!),
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

          _StatusBadge(status: product.stockStatus),
          const SizedBox(height: 12),

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

          // ── Top-5 alternatives ─────────────────────────────────────────────
          if (widget.alternatives.isNotEmpty) ...[
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(Icons.list_alt, size: 16, color: Colors.grey.shade600),
                const SizedBox(width: 6),
                Text(
                  'Other possible matches',
                  style: TextStyle(
                    color: Colors.grey.shade600,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ...widget.alternatives.map((alt) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(
                children: [
                  const SizedBox(width: 4),
                  Icon(Icons.chevron_right, size: 16, color: Colors.grey.shade400),
                  const SizedBox(width: 4),
                  Text(
                    _formatLabel(alt.label),
                    style: const TextStyle(fontSize: 13),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      '${(alt.confidence * 100).toStringAsFixed(1)}%',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey.shade700,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            )),
          ],

          const SizedBox(height: 24),
        ],
      ),
    );
  }

  // ── Shared helpers ──────────────────────────────────────────────────────────

  Widget _handleBar() => Center(
        child: Container(
          width: 40,
          height: 4,
          decoration: BoxDecoration(
            color: Colors.grey.shade300,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
      );

  Color _confidenceColor(double conf) {
    if (conf >= 0.70) return AppTheme.successColor;
    if (conf >= 0.40) return Colors.orange;
    return AppTheme.errorColor;
  }

  /// Format a raw model label for display in the alternatives list.
  /// Handles both old size format ("8mm_30mm" → "M8 × 30mm") and
  /// new type class_id format ("vis__th__zinc__48__din933" → "Vis Th Zinc 4.8 DIN933").
  static String _formatLabel(String label) {
    // Old size format: "8mm_30mm"
    final sizeMatch = RegExp(r'^(\d+)mm_(\d+mm)$').firstMatch(label);
    if (sizeMatch != null) {
      return 'M${sizeMatch.group(1)} × ${sizeMatch.group(2)}';
    }
    // New type class_id: double-underscore separators
    if (label.contains('__')) {
      return label
          .split('__')
          .map((p) {
            // Numeric grade: 48 → 4.8, 88 → 8.8, 109 → 10.9, 129 → 12.9
            final gradeMap = {'48': '4.8', '88': '8.8', '109': '10.9', '129': '12.9'};
            if (gradeMap.containsKey(p)) return gradeMap[p]!;
            if (p.startsWith('din') || p.startsWith('iso')) return p.toUpperCase();
            return p[0].toUpperCase() + p.substring(1);
          })
          .join(' ');
    }
    return label;
  }
}

// ── Size tile (used in size-list mode) ────────────────────────────────────────

class _SizeTile extends StatelessWidget {
  final AvailableSize size;
  final bool expanded;
  final VoidCallback onTap;

  const _SizeTile({
    required this.size,
    required this.expanded,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final (statusColor, statusLabel) = _stockInfo();

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 10),
            child: Row(
              children: [
                // Size label
                Expanded(
                  child: Text(
                    size.sizeLabel,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                    ),
                  ),
                ),
                // Stock badge
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: statusColor.withOpacity(0.5)),
                  ),
                  child: Text(
                    statusLabel,
                    style: TextStyle(
                      fontSize: 11,
                      color: statusColor,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                Icon(
                  expanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                  size: 18,
                  color: Colors.grey.shade500,
                ),
              ],
            ),
          ),
        ),
        // Expanded shelf detail
        if (expanded)
          Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.primaryColor.withOpacity(0.06),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.primaryColor.withOpacity(0.25)),
            ),
            child: Column(
              children: [
                _DetailRow(
                  icon: Icons.location_on_outlined,
                  label: 'Shelf',
                  value: size.shelfLabel,
                  valueStyle: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.primaryColor,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 6),
                _DetailRow(
                  icon: Icons.inventory_outlined,
                  label: 'On shelf',
                  value: '${size.qtyOnShelf ?? "—"}',
                ),
                _DetailRow(
                  icon: Icons.warehouse_outlined,
                  label: 'Backstore',
                  value: '${size.qtyInBackstore ?? "—"}',
                ),
                _DetailRow(
                  icon: Icons.qr_code,
                  label: 'SKU',
                  value: size.sku,
                ),
              ],
            ),
          ),
      ],
    );
  }

  (Color, String) _stockInfo() {
    return switch (size.status) {
      'in_stock'     => (AppTheme.successColor, 'In Stock'),
      'low_stock'    => (Colors.orange,          'Low Stock'),
      'out_of_stock' => (AppTheme.errorColor,    'Out of Stock'),
      _              => (Colors.grey,             size.qtyOnShelf != null
                            ? '${size.qtyOnShelf} pcs'
                            : 'Unknown'),
    };
  }
}

class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final TextStyle? valueStyle;

  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
    this.valueStyle,
  });

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          children: [
            Icon(icon, size: 15, color: Colors.grey.shade600),
            const SizedBox(width: 6),
            Text('$label: ', style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
            Text(value, style: valueStyle ?? const TextStyle(fontSize: 12)),
          ],
        ),
      );
}

// ── Shared widgets used by single-product mode ────────────────────────────────

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
