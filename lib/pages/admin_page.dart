import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:csv/csv.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';

import '../models/product.dart';
import '../models/prediction_result.dart';
import '../services/auth_service.dart';
import '../services/database_service.dart';
import '../services/detector_service.dart';
import '../utils/app_theme.dart';
import '../widgets/backend_status_banner.dart';
import '../widgets/product_form.dart';
import '../widgets/product_result_card.dart';

import '../utils/app_config.dart';

class AdminPage extends StatefulWidget {
  const AdminPage({super.key});

  @override
  State<AdminPage> createState() => _AdminPageState();
}

class _AdminPageState extends State<AdminPage> {
  int _selectedIndex = 0;

  final List<NavigationRailDestination> _destinations = const [
    NavigationRailDestination(
      icon: Icon(Icons.camera_alt_outlined),
      selectedIcon: Icon(Icons.camera_alt),
      label: Text('Identify'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.qr_code_scanner),
      selectedIcon: Icon(Icons.qr_code_scanner),
      label: Text('Scan'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.inventory_2_outlined),
      selectedIcon: Icon(Icons.inventory_2),
      label: Text('Products'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.shelves),
      selectedIcon: Icon(Icons.shelves),
      label: Text('Shelves'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.bar_chart_outlined),
      selectedIcon: Icon(Icons.bar_chart),
      label: Text('Stock'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.upload_file_outlined),
      selectedIcon: Icon(Icons.upload_file),
      label: Text('Import/Export'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.flag_outlined),
      selectedIcon: Icon(Icons.flag),
      label: Text('Reports'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.settings_outlined),
      selectedIcon: Icon(Icons.settings),
      label: Text('Settings'),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final auth = context.read<AuthService>();
    final isWide = MediaQuery.of(context).size.width > 720;

    final body = switch (_selectedIndex) {
      0 => const _AdminIdentifyTab(),
      1 => const _AdminScanTab(),
      2 => const _ProductsTab(),
      3 => const _ShelvesTab(),
      4 => const _StockTab(),
      5 => const _ImportExportTab(),
      6 => const _ReportsTab(),
      7 => const _SettingsTab(),
      _ => const SizedBox(),
    };

    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Panel'),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                const Icon(Icons.admin_panel_settings, size: 18),
                const SizedBox(width: 6),
                Text(auth.userName ?? 'Admin'),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Logout',
            icon: const Icon(Icons.logout),
            onPressed: auth.logout,
          ),
        ],
      ),
      body: Column(
        children: [
          const BackendStatusBanner(),
          Expanded(
            child: isWide
                ? Row(
                    children: [
                      NavigationRail(
                        selectedIndex: _selectedIndex,
                        onDestinationSelected: (i) =>
                            setState(() => _selectedIndex = i),
                        labelType: NavigationRailLabelType.all,
                        destinations: _destinations,
                        backgroundColor: AppTheme.primaryColor.withOpacity(0.05),
                      ),
                      const VerticalDivider(width: 1),
                      Expanded(child: body),
                    ],
                  )
                : body,
          ),
        ],
      ),
      bottomNavigationBar: isWide
          ? null
          : NavigationBar(
              selectedIndex: _selectedIndex,
              onDestinationSelected: (i) => setState(() => _selectedIndex = i),
              destinations: const [
                NavigationDestination(icon: Icon(Icons.camera_alt_outlined), label: 'Identify'),
                NavigationDestination(icon: Icon(Icons.qr_code_scanner),     label: 'Scan'),
                NavigationDestination(icon: Icon(Icons.inventory_2_outlined), label: 'Products'),
                NavigationDestination(icon: Icon(Icons.shelves),              label: 'Shelves'),
                NavigationDestination(icon: Icon(Icons.bar_chart_outlined),   label: 'Stock'),
                NavigationDestination(icon: Icon(Icons.upload_file_outlined), label: 'Import'),
                NavigationDestination(icon: Icon(Icons.flag_outlined),        label: 'Reports'),
                NavigationDestination(icon: Icon(Icons.settings_outlined),    label: 'Settings'),
              ],
            ),
    );
  }
}

// ── Admin Identify Tab ────────────────────────────────────────────────────────

class _AdminIdentifyTab extends StatefulWidget {
  const _AdminIdentifyTab();
  @override
  State<_AdminIdentifyTab> createState() => _AdminIdentifyTabState();
}

class _AdminIdentifyTabState extends State<_AdminIdentifyTab> {
  final _picker   = ImagePicker();
  File?           _image;
  bool            _rulerMode  = false;
  bool            _processing = false;
  PredictionResult? _result;
  String?         _error;

  Future<void> _pick(ImageSource source) async {
    try {
      final x = await _picker.pickImage(source: source, imageQuality: 85, maxWidth: 800);
      if (x == null) return;
      await _run(File(x.path));
    } catch (e) {
      setState(() => _error = 'Camera error: $e');
    }
  }

  Future<void> _pickFile() async {
    final r = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['jpg','jpeg','png','bmp','webp'],
    );
    if (r == null) return;
    await _run(File(r.files.single.path!));
  }

  Future<void> _run(File file) async {
    setState(() { _image = file; _processing = true; _error = null; _result = null; });
    final svc = context.read<DetectorService>();
    PredictionResult? res;
    if (_rulerMode) {
      res = await svc.measureFromFile(file);
    } else {
      res = await svc.detectFromFile(file);
    }
    setState(() { _processing = false; _result = res; _error = svc.errorMessage; });
  }

  void _reset() => setState(() { _image = null; _result = null; _error = null; });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Mode toggle ──────────────────────────────────────────────────
          Row(
            children: [
              const Text('Mode:', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(width: 12),
              ChoiceChip(
                label: const Text('AI'),
                selected: !_rulerMode,
                onSelected: (_) => setState(() { _rulerMode = false; _reset(); }),
              ),
              const SizedBox(width: 8),
              ChoiceChip(
                label: const Text('Ruler'),
                selected: _rulerMode,
                avatar: const Icon(Icons.straighten, size: 16),
                onSelected: (_) => setState(() { _rulerMode = true; _reset(); }),
              ),
              if (_rulerMode) ...[
                const SizedBox(width: 8),
                Text('Place ruler horizontally in frame',
                    style: TextStyle(fontSize: 11, color: Colors.blue.shade700)),
              ],
            ],
          ),
          const SizedBox(height: 12),

          // ── Image preview ────────────────────────────────────────────────
          Container(
            height: 200,
            width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey.shade300),
            ),
            child: _image != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.file(_image!, fit: BoxFit.contain,
                        width: double.infinity, height: double.infinity),
                  )
                : Center(child: Icon(Icons.camera_alt_outlined,
                    size: 48, color: Colors.grey.shade400)),
          ),
          const SizedBox(height: 12),

          // ── Action buttons ───────────────────────────────────────────────
          Row(
            children: [
              if (!kIsWeb && !Platform.isWindows)
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _processing ? null : () => _pick(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt, size: 16),
                    label: const Text('Camera'),
                  ),
                ),
              if (!kIsWeb && !Platform.isWindows) const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _processing ? null : _pickFile,
                  icon: const Icon(Icons.photo_library, size: 16),
                  label: const Text('Gallery'),
                ),
              ),
              if (_result != null) ...[
                const SizedBox(width: 8),
                IconButton(
                  onPressed: _reset,
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Clear',
                ),
              ],
            ],
          ),
          const SizedBox(height: 16),

          // ── Processing ───────────────────────────────────────────────────
          if (_processing)
            const Center(child: CircularProgressIndicator()),

          // ── Error ────────────────────────────────────────────────────────
          if (_error != null)
            _AdminResultBanner(
              icon: Icons.error_outline,
              color: AppTheme.errorColor,
              label: _error!,
            ),

          // ── Result ───────────────────────────────────────────────────────
          if (_result != null) ...[
            _AdminConfidenceBanner(result: _result!),
            const SizedBox(height: 12),
            // YOLO11 parent-class result: full size list
            if (_result!.hasSizeList)
              ProductResultCard(
                displayName:    _result!.displayName,
                availableSizes: _result!.availableSizes,
                confidence:     _result!.confidence,
              )
            // Legacy single-product result
            else if (_result!.product != null)
              ProductResultCard(
                product:         _result!.product!,
                confidence:      _result!.measurementNote != null ? null : _result!.confidence,
                measurementNote: _result!.measurementNote,
              )
            else
              _AdminResultBanner(
                icon: Icons.info_outline,
                color: Colors.orange,
                label: 'Detected "${_result!.predictedLabel}" — not found in database.',
              ),
          ],
        ],
      ),
    );
  }
}

// ── Admin confidence banner ───────────────────────────────────────────────────

class _AdminConfidenceBanner extends StatelessWidget {
  final PredictionResult result;
  const _AdminConfidenceBanner({required this.result});

  @override
  Widget build(BuildContext context) {
    final isRuler = result.measurementNote != null;
    final pct     = (result.confidence * 100).toStringAsFixed(0);

    final (label, color, icon) = isRuler
        ? ('Ruler measurement — physically grounded', Colors.blue.shade700, Icons.straighten)
        : result.confidence >= 0.70
            ? ('High confidence ($pct%) — result likely correct', AppTheme.successColor, Icons.check_circle_outline)
            : result.confidence >= 0.40
                ? ('Medium confidence ($pct%) — verify result', Colors.orange, Icons.warning_amber_outlined)
                : ('Low confidence ($pct%) — result probably wrong', AppTheme.errorColor, Icons.cancel_outlined);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.10),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Expanded(child: Text(label,
              style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 12))),
        ],
      ),
    );
  }
}

class _AdminResultBanner extends StatelessWidget {
  final IconData icon;
  final Color    color;
  final String   label;
  const _AdminResultBanner({required this.icon, required this.color, required this.label});

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    decoration: BoxDecoration(
      color: color.withOpacity(0.08),
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: color.withOpacity(0.3)),
    ),
    child: Row(children: [
      Icon(icon, color: color, size: 18),
      const SizedBox(width: 8),
      Expanded(child: Text(label, style: TextStyle(color: color, fontSize: 12))),
    ]),
  );
}

// ── Admin Scan Tab ────────────────────────────────────────────────────────────

class _AdminScanTab extends StatefulWidget {
  const _AdminScanTab();
  @override
  State<_AdminScanTab> createState() => _AdminScanTabState();
}

class _AdminScanTabState extends State<_AdminScanTab> {
  bool     _scannerActive = false;
  Product? _found;
  String?  _notFound;
  final _manualCtrl = TextEditingController();

  Future<void> _lookup(String barcode) async {
    final p = await DatabaseService.instance.getProductByBarcode(barcode)
           ?? await DatabaseService.instance.getProductBySku(barcode);
    if (!mounted) return;
    setState(() {
      _found    = p;
      _notFound = p == null ? 'No product found for: $barcode' : null;
      _scannerActive = false;
    });
  }

  void _onDetected(BarcodeCapture cap) {
    final raw = cap.barcodes.firstOrNull?.rawValue;
    if (raw == null || !_scannerActive) return;
    setState(() => _scannerActive = false);
    _lookup(raw);
  }

  @override
  void dispose() { _manualCtrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Manual entry ─────────────────────────────────────────────────
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _manualCtrl,
                  decoration: const InputDecoration(
                    hintText: 'Enter SKU or barcode manually…',
                    prefixIcon: Icon(Icons.edit_outlined),
                    isDense: true,
                  ),
                  onSubmitted: (v) { if (v.isNotEmpty) _lookup(v.trim()); },
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: () {
                  final v = _manualCtrl.text.trim();
                  if (v.isNotEmpty) _lookup(v);
                },
                child: const Text('Lookup'),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // ── Camera scanner ───────────────────────────────────────────────
          if (!kIsWeb && !Platform.isWindows) ...[
            if (!_scannerActive)
              ElevatedButton.icon(
                onPressed: () => setState(() {
                  _scannerActive = true;
                  _found = null;
                  _notFound = null;
                }),
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Start Barcode Scanner'),
              )
            else
              Column(
                children: [
                  SizedBox(
                    height: 240,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: MobileScanner(onDetect: _onDetected),
                    ),
                  ),
                  TextButton(
                    onPressed: () => setState(() => _scannerActive = false),
                    child: const Text('Cancel'),
                  ),
                ],
              ),
            const SizedBox(height: 16),
          ],

          // ── Result ───────────────────────────────────────────────────────
          if (_notFound != null)
            _AdminResultBanner(icon: Icons.search_off,
                color: Colors.orange, label: _notFound!),

          if (_found != null) ...[
            _AdminResultBanner(
              icon: Icons.check_circle_outline,
              color: AppTheme.successColor,
              label: 'Product found — SKU: ${_found!.sku}',
            ),
            const SizedBox(height: 12),
            ProductResultCard(product: _found!),
          ],
        ],
      ),
    );
  }
}

// ── Products Tab ─────────────────────────────────────────────────────────────

class _ProductsTab extends StatefulWidget {
  const _ProductsTab();

  @override
  State<_ProductsTab> createState() => _ProductsTabState();
}

class _ProductsTabState extends State<_ProductsTab> {
  late Future<List<Product>> _productsFuture;
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    setState(() {
      _productsFuture = DatabaseService.instance.getAllProducts();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchController,
                  decoration: const InputDecoration(
                    hintText: 'Search products…',
                    prefixIcon: Icon(Icons.search),
                    isDense: true,
                  ),
                  onChanged: (_) => setState(() {
                    _productsFuture = DatabaseService.instance
                        .searchProducts(_searchController.text);
                  }),
                ),
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                onPressed: () => _openProductForm(context, null),
                icon: const Icon(Icons.add),
                label: const Text('Add Product'),
              ),
            ],
          ),
        ),
        Expanded(
          child: FutureBuilder<List<Product>>(
            future: _productsFuture,
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              final products = snap.data ?? [];
              if (products.isEmpty) {
                return const Center(child: Text('No products found. Add one!'));
              }
              return ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                itemCount: products.length,
                itemBuilder: (_, i) => _ProductTile(
                  product: products[i],
                  onEdit: () => _openProductForm(context, products[i]),
                  onDelete: () => _deleteProduct(products[i]),
                  onAssignShelf: () => _quickAssignShelf(context, products[i]),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Future<void> _openProductForm(BuildContext context, Product? product) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (_) => ProductFormDialog(product: product),
    );
    if (result == true) _reload();
  }

  Future<void> _quickAssignShelf(BuildContext context, Product product) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (_) => _QuickAssignShelfDialog(product: product),
    );
    if (result == true) _reload();
  }

  Future<void> _deleteProduct(Product p) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Delete Product'),
        content: Text('Delete "${p.name}"? This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppTheme.errorColor),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await DatabaseService.instance.deleteProduct(p.sku);
      _reload();
    }
  }
}

class _ProductTile extends StatelessWidget {
  final Product product;
  final VoidCallback onEdit;
  final VoidCallback onDelete;
  final VoidCallback onAssignShelf;

  const _ProductTile({
    required this.product,
    required this.onEdit,
    required this.onDelete,
    required this.onAssignShelf,
  });

  @override
  Widget build(BuildContext context) {
    final hasShelf = product.shelfId != null;
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: AppTheme.primaryColor,
          child: Text(product.brand.isNotEmpty ? product.brand[0].toUpperCase() : '?',
              style: const TextStyle(color: Colors.white)),
        ),
        title: Text(
          product.name,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'SKU: ${product.sku} · ${product.brand}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                _StockChip(status: product.stockStatus),
                const SizedBox(width: 8),
                Icon(Icons.shelves, size: 13, color: hasShelf ? AppTheme.primaryColor : Colors.grey),
                const SizedBox(width: 2),
                Flexible(
                  child: Text(
                    hasShelf ? product.shelfLabel : 'No shelf',
                    style: TextStyle(
                      fontSize: 12,
                      color: hasShelf ? AppTheme.primaryColor : Colors.grey,
                      fontWeight: hasShelf ? FontWeight.w500 : FontWeight.normal,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ],
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: Icon(
                Icons.shelves,
                color: hasShelf ? AppTheme.primaryColor : Colors.grey,
              ),
              tooltip: hasShelf ? 'Reassign shelf' : 'Assign to shelf',
              onPressed: onAssignShelf,
              visualDensity: VisualDensity.compact,
              padding: EdgeInsets.zero,
            ),
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              onPressed: onEdit,
              visualDensity: VisualDensity.compact,
              padding: EdgeInsets.zero,
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline, color: AppTheme.errorColor),
              onPressed: onDelete,
              visualDensity: VisualDensity.compact,
              padding: EdgeInsets.zero,
            ),
          ],
        ),
      ),
    );
  }
}

class _StockChip extends StatelessWidget {
  final String? status;
  const _StockChip({this.status});

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (status) {
      'in_stock'     => ('In Stock', AppTheme.successColor),
      'low_stock'    => ('Low', Colors.orange),
      'out_of_stock' => ('Out', AppTheme.errorColor),
      _              => ('Unknown', Colors.grey),
    };
    return Chip(
      label: Text(label, style: TextStyle(color: color, fontSize: 11)),
      backgroundColor: color.withOpacity(0.1),
      side: BorderSide(color: color),
      padding: EdgeInsets.zero,
    );
  }
}

// ── Quick Assign Shelf Dialog ─────────────────────────────────────────────────

class _QuickAssignShelfDialog extends StatefulWidget {
  final Product product;
  const _QuickAssignShelfDialog({required this.product});

  @override
  State<_QuickAssignShelfDialog> createState() => _QuickAssignShelfDialogState();
}

class _QuickAssignShelfDialogState extends State<_QuickAssignShelfDialog> {
  List<Map<String, dynamic>> _shelves = [];
  String? _selectedShelfId;
  bool _loading = true;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _selectedShelfId = widget.product.shelfId;
    _loadShelves();
  }

  Future<void> _loadShelves() async {
    final shelves = await DatabaseService.instance.getShelves();
    if (mounted) {
      setState(() {
        _shelves = shelves;
        _loading = false;
        if (_selectedShelfId != null &&
            !shelves.any((s) => s['shelf_id'] == _selectedShelfId)) {
          _selectedShelfId = null;
        }
      });
    }
  }

  String _shelfLabel(Map<String, dynamic> shelf) {
    final parts = [
      shelf['aisle'] as String?,
      shelf['bay'] as String?,
      shelf['zone'] as String?,
    ].where((s) => s != null && s.isNotEmpty).join('-');
    return parts.isEmpty ? shelf['shelf_id'] as String : parts;
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final p = widget.product;
    final updated = Product(
      sku: p.sku,
      barcode: p.barcode,
      name: p.name,
      brand: p.brand,
      category: p.category,
      type: p.type,
      description: p.description,
      imagePaths: p.imagePaths,
      confidenceThreshold: p.confidenceThreshold,
      shelfId: _selectedShelfId, // may be null to unassign
    );
    await DatabaseService.instance.upsertProduct(updated);
    if (mounted) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Assign Shelf — ${widget.product.name}'),
      content: SizedBox(
        width: 360,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : DropdownButtonFormField<String?>(
                value: _selectedShelfId,
                hint: const Text('Select a shelf…'),
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Shelf Location',
                  prefixIcon: Icon(Icons.shelves),
                ),
                items: [
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('— Unassigned —',
                        style: TextStyle(color: Colors.grey)),
                  ),
                  ..._shelves.map((shelf) {
                    final id = shelf['shelf_id'] as String;
                    final label = _shelfLabel(shelf);
                    final notes = shelf['notes'] as String?;
                    return DropdownMenuItem<String?>(
                      value: id,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(label,
                              style:
                                  const TextStyle(fontWeight: FontWeight.w500)),
                          if (notes != null && notes.isNotEmpty)
                            Text(notes,
                                style: TextStyle(
                                    fontSize: 11, color: Colors.grey.shade600),
                                overflow: TextOverflow.ellipsis),
                        ],
                      ),
                    );
                  }),
                ],
                onChanged: (v) => setState(() => _selectedShelfId = v),
              ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _saving ? null : _save,
          child: _saving
              ? const SizedBox(
                  height: 18,
                  width: 18,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white))
              : const Text('Assign'),
        ),
      ],
    );
  }
}

// ── Shelves Tab ───────────────────────────────────────────────────────────────

class _ShelvesTab extends StatefulWidget {
  const _ShelvesTab();

  @override
  State<_ShelvesTab> createState() => _ShelvesTabState();
}

class _ShelvesTabState extends State<_ShelvesTab> {
  late Future<List<Map<String, dynamic>>> _shelvesFuture;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    setState(() {
      _shelvesFuture = DatabaseService.instance.getShelves();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              ElevatedButton.icon(
                onPressed: () => _openShelfForm(context, null),
                icon: const Icon(Icons.add),
                label: const Text('Add Shelf'),
              ),
            ],
          ),
        ),
        Expanded(
          child: FutureBuilder<List<Map<String, dynamic>>>(
            future: _shelvesFuture,
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              final shelves = snap.data ?? [];
              if (shelves.isEmpty) {
                return const Center(child: Text('No shelves configured yet.'));
              }
              return ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                itemCount: shelves.length,
                itemBuilder: (_, i) {
                  final s = shelves[i];
                  return Card(
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    child: ListTile(
                      leading: const CircleAvatar(
                        backgroundColor: AppTheme.primaryColor,
                        child: Icon(Icons.shelves, color: Colors.white),
                      ),
                      title: Text(
                        'Aisle ${s['aisle']} · Bay ${s['bay']}${s['zone'] != null ? ' · Zone ${s['zone']}' : ''}',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      subtitle: Text('ID: ${s['shelf_id']}  ${s['notes'] ?? ''}'),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.edit_outlined),
                            onPressed: () => _openShelfForm(context, s),
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete_outline,
                                color: AppTheme.errorColor),
                            onPressed: () => _deleteShelf(context, s),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              );
            },
          ),
        ),
      ],
    );
  }

  Future<void> _openShelfForm(
      BuildContext context, Map<String, dynamic>? shelf) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (_) => _ShelfFormDialog(shelf: shelf),
    );
    if (result == true) _reload();
  }

  Future<void> _deleteShelf(
      BuildContext context, Map<String, dynamic> shelf) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Delete Shelf'),
        content: Text(
            'Delete shelf "${shelf['shelf_id']}"? Products assigned to it will be unlinked.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppTheme.errorColor),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await DatabaseService.instance.deleteShelf(shelf['shelf_id']);
      _reload();
    }
  }
}

// ── Shelf Form Dialog ─────────────────────────────────────────────────────────

class _ShelfFormDialog extends StatefulWidget {
  final Map<String, dynamic>? shelf;
  const _ShelfFormDialog({this.shelf});

  @override
  State<_ShelfFormDialog> createState() => _ShelfFormDialogState();
}

class _ShelfFormDialogState extends State<_ShelfFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _aisleCtrl;
  late final TextEditingController _bayCtrl;
  late final TextEditingController _zoneCtrl;
  late final TextEditingController _notesCtrl;
  bool _saving = false;

  bool get _isEdit => widget.shelf != null;

  @override
  void initState() {
    super.initState();
    _aisleCtrl = TextEditingController(text: widget.shelf?['aisle'] ?? '');
    _bayCtrl   = TextEditingController(text: widget.shelf?['bay'] ?? '');
    _zoneCtrl  = TextEditingController(text: widget.shelf?['zone'] ?? '');
    _notesCtrl = TextEditingController(text: widget.shelf?['notes'] ?? '');
  }

  @override
  void dispose() {
    _aisleCtrl.dispose();
    _bayCtrl.dispose();
    _zoneCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }

  String get _generatedId {
    final a = _aisleCtrl.text.trim().toUpperCase();
    final b = _bayCtrl.text.trim().toUpperCase();
    final z = _zoneCtrl.text.trim().toUpperCase();
    if (a.isEmpty || b.isEmpty) return '';
    return z.isNotEmpty ? '$a-$b-$z' : '$a-$b';
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);

    final shelfId = _isEdit
        ? widget.shelf!['shelf_id'] as String
        : _generatedId;

    try {
      if (_isEdit) {
        await DatabaseService.instance.upsertShelf({
          'shelf_id': shelfId,
          'aisle': _aisleCtrl.text.trim(),
          'bay': _bayCtrl.text.trim(),
          'zone': _zoneCtrl.text.trim().isEmpty ? null : _zoneCtrl.text.trim(),
          'notes': _notesCtrl.text.trim().isEmpty ? null : _notesCtrl.text.trim(),
      });
      }
      if (mounted) Navigator.pop(context, true);  
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEdit ? 'Edit Shelf' : 'Add Shelf'),
      content: SizedBox(
        width: 400,
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Shelf ID preview
              if (!_isEdit)
                ListenableBuilder(
                  listenable: Listenable.merge([_aisleCtrl, _bayCtrl, _zoneCtrl]),
                  builder: (_, __) => Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryColor.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      'Shelf ID: ${_generatedId.isEmpty ? '—' : _generatedId}',
                      style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          color: AppTheme.primaryColor),
                    ),
                  ),
                ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _aisleCtrl,
                      decoration: const InputDecoration(
                          labelText: 'Aisle *', hintText: 'A'),
                      textCapitalization: TextCapitalization.characters,
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _bayCtrl,
                      decoration: const InputDecoration(
                          labelText: 'Bay *', hintText: '1'),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _zoneCtrl,
                decoration: const InputDecoration(
                    labelText: 'Zone (optional)', hintText: 'Top / Middle / Bottom'),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _notesCtrl,
                decoration: const InputDecoration(
                    labelText: 'Notes (optional)',
                    hintText: 'e.g. Near entrance'),
                maxLines: 2,
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel')),
        ElevatedButton(
          onPressed: _saving ? null : _save,
          child: _saving
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : Text(_isEdit ? 'Save' : 'Add'),
        ),
      ],
    );
  }
}

// ── Stock Tab ─────────────────────────────────────────────────────────────────

class _StockTab extends StatefulWidget {
  const _StockTab();

  @override
  State<_StockTab> createState() => _StockTabState();
}

class _StockTabState extends State<_StockTab> {
  late Future<List<Product>> _productsFuture;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    setState(() {
      _productsFuture = DatabaseService.instance.getAllProducts();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Product>>(
      future: _productsFuture,
      builder: (context, snap) {
        if (snap.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        final products = snap.data ?? [];
        return ListView.builder(
          padding: const EdgeInsets.all(12),
          itemCount: products.length,
          itemBuilder: (_, i) {
            final p = products[i];
            return Card(
              margin: const EdgeInsets.symmetric(vertical: 4),
              child: ListTile(
                title: Text(p.name),
                subtitle: Text('On shelf: ${p.quantityOnShelf ?? 0}  ·  Backstore: ${p.quantityInBackstore ?? 0}'),
                trailing: IconButton(
                  icon: const Icon(Icons.edit_outlined),
                  onPressed: () => _editStock(context, p),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _editStock(BuildContext context, Product p) async {
    final onShelfCtrl    = TextEditingController(text: '${p.quantityOnShelf ?? 0}');
    final backstoreCtrl  = TextEditingController(text: '${p.quantityInBackstore ?? 0}');

    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text('Update stock: ${p.name}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: onShelfCtrl,   decoration: const InputDecoration(labelText: 'On Shelf'),    keyboardType: TextInputType.number),
            const SizedBox(height: 12),
            TextField(controller: backstoreCtrl, decoration: const InputDecoration(labelText: 'Backstore'),   keyboardType: TextInputType.number),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              await DatabaseService.instance.updateStock(
                p.sku,
                int.tryParse(onShelfCtrl.text) ?? 0,
                int.tryParse(backstoreCtrl.text) ?? 0,
              );
              if (context.mounted) Navigator.pop(context, true);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (saved == true) _reload();
  }
}

// ── Import/Export Tab ─────────────────────────────────────────────────────────

class _ImportExportTab extends StatelessWidget {
  const _ImportExportTab();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Import / Export', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 24),
          _ActionCard(
            icon: Icons.upload_file,
            title: 'Import Products from CSV',
            subtitle: 'Matches your existing products_rows.csv format',
            onTap: () => _importCsv(context),
          ),
          const SizedBox(height: 12),
          _ActionCard(
            icon: Icons.download,
            title: 'Export Products to CSV',
            subtitle: 'Downloads current catalog as CSV',
            onTap: () => _exportCsv(context),
          ),
        ],
      ),
    );
  }

  Future<void> _importCsv(BuildContext context) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['csv'],
    );
    if (result == null) return;

    final file = File(result.files.single.path!);
    final content = await file.readAsString();
    final rows = const CsvToListConverter(eol: '\n').convert(content);
    if (rows.isEmpty) return;

    final headers = rows.first.map((e) => e.toString()).toList();
    int imported = 0;
    for (final row in rows.skip(1)) {
      final map = {for (var i = 0; i < headers.length; i++) headers[i]: row[i]};
      try {
        final product = Product(
          sku: map['sku'].toString(),
          name: map['name'].toString(),
          brand: map['brand'].toString(),
          category: map['category'].toString(),
          type: map['type']?.toString() ?? 'tool',
          barcode: map['barcode']?.toString(),
          description: map['description']?.toString(),
        );
        await DatabaseService.instance.upsertProduct(product);
        imported++;
      } catch (_) {}
    }

    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Imported $imported products')),
      );
    }
  }

  Future<void> _exportCsv(BuildContext context) async {
    final products = await DatabaseService.instance.getAllProducts();
    final rows = [
      ['sku', 'barcode', 'name', 'brand', 'category', 'type', 'shelf_id', 'quantity_on_shelf'],
      for (final p in products)
        [p.sku, p.barcode ?? '', p.name, p.brand, p.category, p.type, p.shelfId ?? '', p.quantityOnShelf ?? 0],
    ];
    final csv = const ListToCsvConverter().convert(rows);

    final path = await FilePicker.platform.saveFile(
      dialogTitle: 'Save products CSV',
      fileName: 'products_export.csv',
    );
    if (path == null) return;
    await File(path).writeAsString(csv);

    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Exported successfully')),
      );
    }
  }
}

class _ActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _ActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          leading: CircleAvatar(
            backgroundColor: AppTheme.primaryColor,
            child: Icon(icon, color: Colors.white),
          ),
          title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(subtitle),
          trailing: const Icon(Icons.chevron_right),
          onTap: onTap,
        ),
      );
}

// ── Settings Tab ──────────────────────────────────────────────────────────────

class _SettingsTab extends StatefulWidget {
  const _SettingsTab();
  @override
  State<_SettingsTab> createState() => _SettingsTabState();
}

class _SettingsTabState extends State<_SettingsTab> {
  static const String _baseUrl = AppConfig.backendUrl;

  // ── Train state ──
  Map<String, dynamic>? _trainStatus;
  bool _polling = false;
  Timer? _timer;
  int _epochs = 50;

  // ── Dataset classes ──
  List<Map<String, dynamic>> _classes = [];
  bool _loadingClasses = false;

  // ── Selected product for photo upload ──
  Product? _selectedProduct;
  List<String> _selectedPhotoPaths = [];
  bool _uploading = false;

  @override
  void initState() {
    super.initState();
    _loadClasses();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  // ── Load dataset classes ──────────────────────────────────────────────────

  Future<void> _loadClasses() async {
    setState(() => _loadingClasses = true);
    try {
      final response = await http.get(Uri.parse('$_baseUrl/dataset/classes'));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as List;
        setState(() => _classes = data.cast<Map<String, dynamic>>());
      }
    } catch (_) {}
    setState(() => _loadingClasses = false);
  }

  // ── Pick product ──────────────────────────────────────────────────────────

  Future<void> _pickProduct() async {
    final result = await showDialog<Product>(
      context: context,
      builder: (_) => const _ProductPickerDialog(),
    );
    if (result != null) {
      setState(() {
        _selectedProduct = result;
        _selectedPhotoPaths = [];
      });
    }
  }

  // ── Pick photos ───────────────────────────────────────────────────────────

  Future<void> _pickPhotos() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.image,
    );
    if (result != null) {
      setState(() {
        _selectedPhotoPaths = result.files.map((f) => f.path!).toList();
      });
    }
  }

  // ── Upload photos ─────────────────────────────────────────────────────────

  Future<void> _uploadPhotos() async {
    if (_selectedProduct == null || _selectedPhotoPaths.isEmpty) return;
    setState(() => _uploading = true);

    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$_baseUrl/dataset/add-photos?sku=${_selectedProduct!.sku}'),
      );

      for (final path in _selectedPhotoPaths) {
        final bytes = await File(path).readAsBytes();
        request.files.add(http.MultipartFile.fromBytes(
          'files',
          bytes,
          filename: path.split('\\').last,
          contentType: MediaType('image', 'jpeg'),
        ));
      }

      final response = await http.Response.fromStream(await request.send());
      final data = jsonDecode(response.body);

      if (response.statusCode == 200 && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✅ ${data['saved']} photos added to ${data['label']}'),
            backgroundColor: AppTheme.successColor,
          ),
        );
        setState(() {
          _selectedProduct = null;
          _selectedPhotoPaths = [];
        });
        _loadClasses(); // refresh counts
      } else {
        throw Exception(data['detail'] ?? 'Upload failed');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: AppTheme.errorColor),
        );
      }
    }
    setState(() => _uploading = false);
  }

  // ── Training ──────────────────────────────────────────────────────────────

  Future<void> _startTraining() async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/train?epochs=$_epochs'),
      );
      if (response.statusCode == 200) {
        _startPolling();
      } else {
        final data = jsonDecode(response.body);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(data['detail'] ?? 'Failed to start')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  void _startPolling() {
    setState(() => _polling = true);
    _timer = Timer.periodic(const Duration(seconds: 3), (_) async {
      await _fetchTrainStatus();
    });
    // Keep screen awake during training
    WakelockPlus.enable();
  }

  Future<void> _fetchTrainStatus() async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/train/status'))
          .timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        setState(() => _trainStatus = data);
        if (data['status'] == 'done' || data['status'] == 'error') {
          _timer?.cancel();
          setState(() => _polling = false);
          WakelockPlus.disable(); // release screen lock when done
        }
      }
    } catch (e) {
      // Connection dropped — keep polling, don't stop
      print('Polling error (retrying): $e');
    }
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Settings', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 24),

          // ── Add Training Photos ──────────────────────────────────────────
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(children: [
                    Icon(Icons.add_photo_alternate, color: AppTheme.primaryColor),
                    SizedBox(width: 8),
                    Text('Add Training Photos',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  ]),
                  const SizedBox(height: 4),
                  const Text('Select a product then add photos to improve its AI recognition.',
                      style: TextStyle(color: Colors.grey)),
                  const SizedBox(height: 16),

                  // Step 1 — pick product
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: CircleAvatar(
                      backgroundColor: AppTheme.primaryColor,
                      child: const Text('1', style: TextStyle(color: Colors.white)),
                    ),
                    title: Text(
                      _selectedProduct == null
                          ? 'Select a product'
                          : _selectedProduct!.name,
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: _selectedProduct == null ? Colors.grey : null,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    subtitle: _selectedProduct != null
                        ? Text('SKU: ${_selectedProduct!.sku}')
                        : null,
                    trailing: ElevatedButton(
                      onPressed: _pickProduct,
                      child: const Text('Browse'),
                    ),
                  ),

                  const Divider(),

                  // Step 2 — pick photos
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: CircleAvatar(
                      backgroundColor: _selectedProduct == null
                          ? Colors.grey
                          : AppTheme.primaryColor,
                      child: const Text('2', style: TextStyle(color: Colors.white)),
                    ),
                    title: Text(
                      _selectedPhotoPaths.isEmpty
                          ? 'Select photos'
                          : '${_selectedPhotoPaths.length} photo(s) selected',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: _selectedPhotoPaths.isEmpty ? Colors.grey : null,
                      ),
                    ),
                    trailing: ElevatedButton(
                      onPressed: _selectedProduct == null ? null : _pickPhotos,
                      child: const Text('Browse'),
                    ),
                  ),

                  const SizedBox(height: 12),

                  // Upload button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: (_selectedProduct == null ||
                              _selectedPhotoPaths.isEmpty ||
                              _uploading)
                          ? null
                          : _uploadPhotos,
                      icon: _uploading
                          ? const SizedBox(
                              width: 16, height: 16,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white))
                          : const Icon(Icons.cloud_upload),
                      label: Text(_uploading ? 'Uploading...' : 'Upload Photos'),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 12),

          // ── Dataset Overview ─────────────────────────────────────────────
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Row(children: [
                        Icon(Icons.dataset, color: AppTheme.primaryColor),
                        SizedBox(width: 8),
                        Text('Dataset Overview',
                            style: TextStyle(
                                fontWeight: FontWeight.bold, fontSize: 16)),
                      ]),
                      IconButton(
                        icon: const Icon(Icons.refresh),
                        onPressed: _loadClasses,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  if (_loadingClasses)
                    const Center(child: CircularProgressIndicator())
                  else if (_classes.isEmpty)
                    const Text('No classes found.',
                        style: TextStyle(color: Colors.grey))
                  else
                    ..._classes.map((c) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                            children: [
                              const Icon(Icons.folder_outlined, size: 18),
                              const SizedBox(width: 8),
                              Expanded(child: Text(c['class_name'] as String)),
                              Text(
                                '${c['photo_count']} photos',
                                style: TextStyle(
                                  color: (c['photo_count'] as int) < 20
                                      ? Colors.orange
                                      : AppTheme.successColor,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        )),
                ],
              ),
            ),
          ),

          const SizedBox(height: 12),

          // ── Train Model ──────────────────────────────────────────────────
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(children: [
                    Icon(Icons.model_training, color: AppTheme.primaryColor),
                    SizedBox(width: 8),
                    Text('Train AI Model',
                        style: TextStyle(
                            fontWeight: FontWeight.bold, fontSize: 16)),
                  ]),
                  const SizedBox(height: 4),
                  const Text('Retrain the classifier with the latest photos.',
                      style: TextStyle(color: Colors.grey)),
                  const SizedBox(height: 12),

                  Row(
                    children: [
                      const Text('Epochs:'),
                      Expanded(
                        child: Slider(
                          value: _epochs.toDouble(),
                          min: 10, max: 100, divisions: 9,
                          label: '$_epochs',
                          onChanged: _polling
                              ? null
                              : (v) => setState(() => _epochs = v.toInt()),
                        ),
                      ),
                      Text('$_epochs',
                          style: const TextStyle(fontWeight: FontWeight.bold)),
                    ],
                  ),

                  if (_trainStatus != null) ...[
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: LinearProgressIndicator(
                            value: (_trainStatus!['progress'] as int) / 100.0,
                            color: _trainStatus!['status'] == 'error'
                                ? AppTheme.errorColor
                                : _trainStatus!['status'] == 'done'
                                    ? AppTheme.successColor
                                    : AppTheme.primaryColor,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text('${_trainStatus!['progress']}%'),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _trainStatus!['message'] as String? ?? '',
                      style: TextStyle(
                        fontSize: 13,
                        color: _trainStatus!['status'] == 'error'
                            ? AppTheme.errorColor
                            : _trainStatus!['status'] == 'done'
                                ? AppTheme.successColor
                                : Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 8),
                  ],

                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _polling ? null : _startTraining,
                      icon: _polling
                          ? const SizedBox(
                              width: 16, height: 16,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white))
                          : const Icon(Icons.play_arrow),
                      label: Text(_polling
                          ? 'Training in progress...'
                          : 'Start Training'),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 12),

          // ── Other settings ───────────────────────────────────────────────
          Card(
            child: ListTile(
              leading: const Icon(Icons.lock_outline, color: AppTheme.primaryColor),
              title: const Text('Change Password'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => _changePassword(context),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _changePassword(BuildContext context) async {
    final auth = context.read<AuthService>();
    final oldCtrl = TextEditingController();
    final newCtrl = TextEditingController();
    final confirmCtrl = TextEditingController();
    String? error;

    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Change Password'),
          content: SizedBox(
            width: 360,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: oldCtrl,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Current password'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: newCtrl,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'New password'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: confirmCtrl,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Confirm new password'),
                ),
                if (error != null) ...[
                  const SizedBox(height: 8),
                  Text(error!, style: const TextStyle(color: AppTheme.errorColor)),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                if (newCtrl.text != confirmCtrl.text) {
                  setDialogState(() => error = 'Passwords do not match.');
                  return;
                }
                if (newCtrl.text.length < 6) {
                  setDialogState(() => error = 'Password must be at least 6 characters.');
                  return;
                }
                final ok = await auth.changePassword(
                  email: auth.userEmail ?? '',
                  oldPassword: oldCtrl.text,
                  newPassword: newCtrl.text,
                );
                if (ok) {
                  if (ctx.mounted) Navigator.pop(ctx);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Password changed successfully.')),
                    );
                  }
                } else {
                  setDialogState(() => error = 'Current password is incorrect.');
                }
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Reports Tab ───────────────────────────────────────────────────────────────

class _ReportsTab extends StatefulWidget {
  const _ReportsTab();
  @override
  State<_ReportsTab> createState() => _ReportsTabState();
}

class _ReportsTabState extends State<_ReportsTab> {
  static const _base = AppConfig.backendUrl;

  List<Map<String, dynamic>> _reports = [];
  bool _loading = false;
  // local override map: id → 'confirmed'|'rejected' (before batch submit)
  final Map<int, String> _localStatus = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await http.get(Uri.parse('$_base/admin/reports?status=pending'));
      if (r.statusCode == 200) {
        final list = jsonDecode(r.body) as List;
        setState(() => _reports = list.cast<Map<String, dynamic>>());
      }
    } catch (_) {}
    setState(() => _loading = false);
  }

  Future<void> _confirm(int id) async {
    await http.post(Uri.parse('$_base/admin/reports/$id/confirm'));
    setState(() => _localStatus[id] = 'confirmed');
  }

  Future<void> _reject(int id) async {
    await http.post(Uri.parse('$_base/admin/reports/$id/reject'));
    setState(() => _localStatus[id] = 'rejected');
  }

  Future<void> _submitBatch() async {
    final confirmed = _reports
        .where((r) => _localStatus[r['id']] == 'confirmed')
        .length;
    if (confirmed == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No confirmed reports to submit.')),
      );
      return;
    }
    final r = await http.post(Uri.parse('$_base/admin/submit-batch'));
    if (!mounted) return;
    final msg = r.statusCode == 200
        ? (jsonDecode(r.body)['message'] as String)
        : 'Submit failed (${r.statusCode})';
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(msg)));
    _localStatus.clear();
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final pendingCount = _reports
        .where((r) => !_localStatus.containsKey(r['id']))
        .length;
    final confirmedCount = _reports
        .where((r) => _localStatus[r['id']] == 'confirmed')
        .length;

    return Column(
      children: [
        // ── Header bar ────────────────────────────────────────────────────────
        Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('AI Detection Reports',
                        style: Theme.of(context).textTheme.titleLarge),
                    Text('$pendingCount pending · $confirmedCount confirmed',
                        style: const TextStyle(color: Colors.grey, fontSize: 12)),
                  ],
                ),
              ),
              IconButton(
                tooltip: 'Refresh',
                icon: const Icon(Icons.refresh),
                onPressed: _load,
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: confirmedCount > 0 ? _submitBatch : null,
                icon: const Icon(Icons.upload, size: 16),
                label: Text('Submit ($confirmedCount)'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryColor,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
        const Divider(height: 1),

        // ── List ──────────────────────────────────────────────────────────────
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _reports.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.check_circle_outline,
                              size: 64, color: Colors.grey),
                          SizedBox(height: 12),
                          Text('No pending reports',
                              style: TextStyle(color: Colors.grey)),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: _reports.length,
                      itemBuilder: (_, i) {
                        final r      = _reports[i];
                        final id     = r['id'] as int;
                        final status = _localStatus[id];
                        return _ReportCard(
                          report:       r,
                          localStatus:  status,
                          baseUrl:      _base,
                          onConfirm:    status == null ? () => _confirm(id) : null,
                          onReject:     status == null ? () => _reject(id)  : null,
                        );
                      },
                    ),
        ),
      ],
    );
  }
}

class _ReportCard extends StatelessWidget {
  final Map<String, dynamic> report;
  final String?     localStatus;
  final String      baseUrl;
  final VoidCallback? onConfirm;
  final VoidCallback? onReject;

  const _ReportCard({
    required this.report,
    required this.localStatus,
    required this.baseUrl,
    this.onConfirm,
    this.onReject,
  });

  @override
  Widget build(BuildContext context) {
    final imageUrl = '$baseUrl${report['image_url']}';
    final wrong    = report['wrong_class']   as String;
    final correct  = report['correct_class'] as String;
    final by       = report['reported_by']   as String? ?? 'staff';
    final decided  = localStatus != null;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: localStatus == 'confirmed'
              ? Colors.green
              : localStatus == 'rejected'
                  ? Colors.red
                  : Colors.transparent,
          width: 2,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Thumbnail
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.network(
                imageUrl,
                width: 80,
                height: 80,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  width: 80, height: 80,
                  color: Colors.grey.shade200,
                  child: const Icon(Icons.broken_image, color: Colors.grey),
                ),
              ),
            ),
            const SizedBox(width: 12),

            // Labels
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _LabelRow(label: 'Wrong', value: wrong,
                      color: Colors.red.shade700),
                  const SizedBox(height: 4),
                  _LabelRow(label: 'Correct', value: correct,
                      color: Colors.green.shade700),
                  const SizedBox(height: 4),
                  Text('by $by',
                      style: const TextStyle(color: Colors.grey, fontSize: 11)),
                  if (decided) ...[
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: localStatus == 'confirmed'
                            ? Colors.green.shade100
                            : Colors.red.shade100,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        localStatus == 'confirmed' ? '✓ Confirmed' : '✗ Rejected',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: localStatus == 'confirmed'
                              ? Colors.green.shade700
                              : Colors.red.shade700,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),

            // Action buttons (hidden after decision)
            if (!decided)
              Column(
                children: [
                  IconButton(
                    tooltip: 'Confirm — correct image',
                    icon: const Icon(Icons.check_circle_outline,
                        color: Colors.green),
                    onPressed: onConfirm,
                  ),
                  IconButton(
                    tooltip: 'Reject — delete image',
                    icon: const Icon(Icons.cancel_outlined,
                        color: Colors.red),
                    onPressed: onReject,
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _LabelRow extends StatelessWidget {
  final String label;
  final String value;
  final Color  color;
  const _LabelRow({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 50,
            child: Text('$label:',
                style: const TextStyle(
                    fontSize: 11, color: Colors.grey,
                    fontWeight: FontWeight.bold)),
          ),
          Expanded(
            child: Text(value,
                style: TextStyle(fontSize: 12, color: color,
                    fontWeight: FontWeight.w500),
                maxLines: 2,
                overflow: TextOverflow.ellipsis),
          ),
        ],
      );
}

// ── Product Picker Dialog ─────────────────────────────────────────────────────

class _ProductPickerDialog extends StatefulWidget {
  const _ProductPickerDialog();

  @override
  State<_ProductPickerDialog> createState() => _ProductPickerDialogState();
}

class _ProductPickerDialogState extends State<_ProductPickerDialog> {
  final _searchCtrl = TextEditingController();
  List<Product> _results = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _search('');
  }
  Future<void> _search(String query) async {
    setState(() => _loading = true);
    List<Product> products;
    if (query.isEmpty) {
      products = await DatabaseService.instance.getAllProducts();
    } else {
      products = await DatabaseService.instance.searchProducts(query);
    }
    setState(() {
      _results = products; // show all products
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Select Product'),
      content: SizedBox(
        width: 500,
        height: 400,
        child: Column(
          children: [
            TextField(
              controller: _searchCtrl,
              decoration: const InputDecoration(
                hintText: 'Search products…',
                prefixIcon: Icon(Icons.search),
                isDense: true,
              ),
              onChanged: _search,
            ),
            const SizedBox(height: 8),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _results.isEmpty
                      ? const Center(
                          child: Text('No trainable products found.'))
                      : ListView.builder(
                          itemCount: _results.length,
                          itemBuilder: (_, i) {
                            final p = _results[i];
                            return ListTile(
                              title: Text(p.name,
                                  style: const TextStyle(fontSize: 13),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis),
                              subtitle: Text('SKU: ${p.sku}'),
                              onTap: () => Navigator.pop(context, p),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
      ],
    );
  }
}