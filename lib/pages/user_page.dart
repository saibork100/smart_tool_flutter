import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../services/auth_service.dart';
import '../services/detector_service.dart';
import '../models/prediction_result.dart';
import '../models/product.dart';
import '../utils/app_theme.dart';
import '../widgets/product_result_card.dart';
import '../widgets/backend_status_banner.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:file_picker/file_picker.dart';

class UserPage extends StatefulWidget {
  const UserPage({super.key});

  @override
  State<UserPage> createState() => _UserPageState();
}

class _UserPageState extends State<UserPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final ImagePicker _picker = ImagePicker();
  final TextEditingController _searchController = TextEditingController();

  File? _selectedImage;
  List<Product> _searchResults = [];
  bool _scannerActive = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  // ── Camera / image actions ─────────────────────────────────────────────────

  Future<void> _captureFromCamera() async {
    final xFile = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 85,
      maxWidth: 640,
    );
    if (xFile == null) return;
    await _runDetection(File(xFile.path));
  }

  Future<void> _pickFromGallery() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['jpg', 'jpeg', 'png', 'bmp', 'heic', 'heif', 'webp','dng'],
    );
    if (result == null) return;
    await _runDetection(File(result.files.single.path!));
  }

  Future<void> _runDetection(File file) async {
    setState(() => _selectedImage = file);
    _tabController.animateTo(0);
    context.read<DetectorService>().detectFromFile(file);
  }

  // ── Barcode handler ────────────────────────────────────────────────────────

  void _onBarcodeDetected(BarcodeCapture capture) async {
    final barcode = capture.barcodes.firstOrNull?.rawValue;
    if (barcode == null || !_scannerActive) return;
    setState(() => _scannerActive = false);

    final product = await context.read<DetectorService>().lookupByBarcode(barcode);
    if (!mounted) return;
    if (product == null) {
      _showSnack('No product found for barcode: $barcode');
    } else {
      _showProductSheet(product);
    }
  }

  // ── Name search ────────────────────────────────────────────────────────────

  Future<void> _search(String query) async {
    if (query.trim().isEmpty) {
      setState(() => _searchResults = []);
      return;
    }
    final results = await context.read<DetectorService>().searchByName(query);
    setState(() => _searchResults = results);
  }

  // ── UI ─────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final auth = context.read<AuthService>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Smart Tool Recognition'),
        actions: [
          IconButton(
            tooltip: 'Logout',
            icon: const Icon(Icons.logout),
            onPressed: () => auth.logout(),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.accentColor,
          tabs: const [
            Tab(icon: Icon(Icons.camera_alt), text: 'Identify'),
            Tab(icon: Icon(Icons.qr_code_scanner), text: 'Barcode'),
            Tab(icon: Icon(Icons.search), text: 'Search'),
          ],
        ),
      ),
      body: Column(
        children: [
          const BackendStatusBanner(),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _IdentifyTab(
                  selectedImage: _selectedImage,
                  onCamera: _captureFromCamera,
                  onGallery: _pickFromGallery,
                ),
                _BarcodeTab(
                  active: _scannerActive,
                  onActivate: () => setState(() => _scannerActive = true),
                  onDetected: _onBarcodeDetected,
                ),
                _SearchTab(
                  controller: _searchController,
                  results: _searchResults,
                  onSearch: _search,
                  onProductTap: _showProductSheet,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _showSnack(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  void _showProductSheet(Product p) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => ProductResultCard(product: p),
    );
  }
}

// ── Sub-tabs ───────────────────────────────────────────────────────────────────

class _IdentifyTab extends StatelessWidget {
  final File? selectedImage;
  final VoidCallback onCamera;
  final VoidCallback onGallery;

  const _IdentifyTab({
    required this.selectedImage,
    required this.onCamera,
    required this.onGallery,
  });

  @override
  Widget build(BuildContext context) {
    final detector = context.watch<DetectorService>();
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Image preview
          Container(
            height: 220,
            width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.grey.shade200,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey.shade300),
            ),
            child: selectedImage != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.file(selectedImage!, fit: BoxFit.contain),
                  )
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.image_outlined, size: 64, color: Colors.grey.shade400),
                      const SizedBox(height: 8),
                      Text('Take or upload a photo of a tool',
                          style: TextStyle(color: Colors.grey.shade600)),
                    ],
                  ),
          ),
          const SizedBox(height: 16),

          // Buttons
          Row(
            children: [
             Expanded(
                child: Tooltip(
                  message: kIsWeb || Platform.isWindows
                      ? 'Camera not available on desktop — use Gallery'
                      : '',
                  child: ElevatedButton.icon(
                    onPressed: (detector.isProcessing ||
                            kIsWeb ||
                            Platform.isWindows)
                        ? null
                        : onCamera,
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Camera'),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: detector.isProcessing ? null : onGallery,
                  icon: const Icon(Icons.photo_library),
                  label: const Text('Gallery'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Result
          if (detector.isProcessing)
            const Column(
              children: [
                CircularProgressIndicator(),
                SizedBox(height: 12),
                Text('Analysing tool…'),
              ],
            )
          else if (detector.errorMessage != null)
            _ErrorCard(message: detector.errorMessage!)
          else if (detector.lastResult != null)
            _ResultView(result: detector.lastResult!),
        ],
      ),
    );
  }
}

class _ResultView extends StatelessWidget {
  final PredictionResult result;
  const _ResultView({required this.result});

  @override
  Widget build(BuildContext context) {
    if (!result.isConfident) {
      return Card(
        color: Colors.orange.shade50,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.help_outline, color: Colors.orange),
                  SizedBox(width: 8),
                  Text('Low confidence — try retaking the photo',
                      style: TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
              const SizedBox(height: 12),
              const Text('Top suggestions:'),
              ...result.topPredictions.take(3).map(
                    (p) => ListTile(
                      dense: true,
                      title: Text(p.label),
                      trailing: Text('${(p.confidence * 100).toStringAsFixed(1)}%'),
                    ),
                  ),
            ],
          ),
        ),
      );
    }

    final product = result.product;
    if (product == null) {
      return Card(
        child: ListTile(
          leading: const Icon(Icons.info_outline),
          title: Text('Detected: ${result.predictedLabel}'),
          subtitle: Text('Confidence: ${(result.confidence * 100).toStringAsFixed(1)}%\nNot found in local database.'),
        ),
      );
    }

    return ProductResultCard(product: product, confidence: result.confidence);
  }
}

class _ErrorCard extends StatelessWidget {
  final String message;
  const _ErrorCard({required this.message});

  @override
  Widget build(BuildContext context) => Card(
        color: Colors.red.shade50,
        child: ListTile(
          leading: const Icon(Icons.error_outline, color: AppTheme.errorColor),
          title: Text(message, style: const TextStyle(color: AppTheme.errorColor)),
        ),
      );
}

class _BarcodeTab extends StatelessWidget {
  final bool active;
  final VoidCallback onActivate;
  final Function(BarcodeCapture) onDetected;

  const _BarcodeTab({
    required this.active,
    required this.onActivate,
    required this.onDetected,
  });

  @override
  Widget build(BuildContext context) {
    if (!active) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.qr_code_scanner, size: 80, color: AppTheme.primaryColor),
            const SizedBox(height: 16),
            const Text('Scan a barcode to find a product'),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: onActivate,
              icon: const Icon(Icons.play_arrow),
              label: const Text('Start Scanner'),
            ),
          ],
        ),
      );
    }
    return MobileScanner(onDetect: onDetected);
  }
}

class _SearchTab extends StatelessWidget {
  final TextEditingController controller;
  final List<Product> results;
  final Function(String) onSearch;
  final Function(Product) onProductTap;

  const _SearchTab({
    required this.controller,
    required this.results,
    required this.onSearch,
    required this.onProductTap,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(
            controller: controller,
            decoration: const InputDecoration(
              hintText: 'Search by name, brand, category…',
              prefixIcon: Icon(Icons.search),
            ),
            onChanged: onSearch,
          ),
        ),
        Expanded(
          child: results.isEmpty
              ? Center(
                  child: Text(
                    controller.text.isEmpty ? 'Type to search products' : 'No results found',
                    style: TextStyle(color: Colors.grey.shade600),
                  ),
                )
              : ListView.builder(
                  itemCount: results.length,
                  itemBuilder: (_, i) {
                    final p = results[i];
                    return ListTile(
                      leading: CircleAvatar(
                        backgroundColor: AppTheme.primaryColor,
                        child: Text(p.brand.isNotEmpty ? p.brand[0].toUpperCase() : '?',
                            style: const TextStyle(color: Colors.white)),
                      ),
                      title: Text(p.name),
                      subtitle: Text('${p.brand} · ${p.shelfLabel}'),
                      trailing: _StockBadge(status: p.stockStatus),
                      onTap: () => onProductTap(p),
                    );
                  },
                ),
        ),
      ],
    );
  }
}

class _StockBadge extends StatelessWidget {
  final String? status;
  const _StockBadge({this.status});

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (status) {
      'in_stock'     => ('In Stock', AppTheme.successColor),
      'low_stock'    => ('Low', Colors.orange),
      'out_of_stock' => ('Out', AppTheme.errorColor),
      _              => ('?', Colors.grey),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold)),
    );
  }
}
