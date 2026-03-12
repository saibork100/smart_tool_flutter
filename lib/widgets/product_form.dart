import 'package:flutter/material.dart';
import '../models/product.dart';
import '../services/database_service.dart';

class ProductFormDialog extends StatefulWidget {
  final Product? product; // null = create new

  const ProductFormDialog({super.key, this.product});

  @override
  State<ProductFormDialog> createState() => _ProductFormDialogState();
}

class _ProductFormDialogState extends State<ProductFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _sku, _name, _brand, _category, _barcode, _description;
  String _type = 'tool';
  bool _saving = false;

  // Shelf assignment
  String? _selectedShelfId;
  List<Map<String, dynamic>> _shelves = [];
  bool _loadingShelves = true;

  bool get isEditing => widget.product != null;

  @override
  void initState() {
    super.initState();
    final p = widget.product;
    _sku         = TextEditingController(text: p?.sku ?? '');
    _name        = TextEditingController(text: p?.name ?? '');
    _brand       = TextEditingController(text: p?.brand ?? '');
    _category    = TextEditingController(text: p?.category ?? '');
    _barcode     = TextEditingController(text: p?.barcode ?? '');
    _description = TextEditingController(text: p?.description ?? '');
    _type        = p?.type ?? 'tool';
    _selectedShelfId = p?.shelfId;
    _loadShelves();
  }

  Future<void> _loadShelves() async {
    final shelves = await DatabaseService.instance.getShelves();
    if (mounted) {
      setState(() {
        _shelves = shelves;
        _loadingShelves = false;
        // Validate that the current shelf_id still exists; clear if not
        if (_selectedShelfId != null &&
            !shelves.any((s) => s['shelf_id'] == _selectedShelfId)) {
          _selectedShelfId = null;
        }
      });
    }
  }

  @override
  void dispose() {
    for (final c in [_sku, _name, _brand, _category, _barcode, _description]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);

    final product = Product(
      sku: _sku.text.trim(),
      name: _name.text.trim(),
      brand: _brand.text.trim(),
      category: _category.text.trim(),
      type: _type,
      barcode: _barcode.text.trim().isEmpty ? null : _barcode.text.trim(),
      description: _description.text.trim().isEmpty ? null : _description.text.trim(),
      shelfId: _selectedShelfId,
    );

    await DatabaseService.instance.upsertProduct(product);
    if (mounted) Navigator.pop(context, true);
  }

  /// Builds the shelf label for a shelf map: e.g. "A-3-B"
  String _shelfLabel(Map<String, dynamic> shelf) {
    final parts = [
      shelf['aisle'] as String?,
      shelf['bay'] as String?,
      shelf['zone'] as String?,
    ].where((s) => s != null && s.isNotEmpty).join('-');
    return parts.isEmpty ? shelf['shelf_id'] as String : parts;
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 500, maxHeight: 650),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isEditing ? 'Edit Product' : 'Add Product',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 20),
                Expanded(
                  child: SingleChildScrollView(
                    child: Column(
                      children: [
                        _field(_sku, 'SKU *', enabled: !isEditing, validator: _required),
                        _field(_name, 'Product Name *', validator: _required),
                        _field(_brand, 'Brand *', validator: _required),
                        _field(_category, 'Category *', validator: _required),
                        _field(_barcode, 'Barcode'),
                        _buildShelfDropdown(),
                        _field(_description, 'Description', maxLines: 3),
                        const SizedBox(height: 8),
                        DropdownButtonFormField<String>(
                          value: _type,
                          decoration: const InputDecoration(labelText: 'Type'),
                          items: ['tool', 'accessory', 'service']
                              .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                              .toList(),
                          onChanged: (v) => setState(() => _type = v!),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: const Text('Cancel'),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      onPressed: _saving ? null : _save,
                      child: _saving
                          ? const SizedBox(height: 18, width: 18,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : Text(isEditing ? 'Save Changes' : 'Add Product'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildShelfDropdown() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: _loadingShelves
          ? const InputDecorator(
              decoration: InputDecoration(labelText: 'Shelf Location'),
              child: SizedBox(
                height: 20,
                child: Center(
                  child: SizedBox(
                    height: 16,
                    width: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              ),
            )
          : DropdownButtonFormField<String?>(
              value: _selectedShelfId,
              decoration: InputDecoration(
                labelText: 'Shelf Location',
                suffixIcon: _selectedShelfId != null
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 18),
                        tooltip: 'Remove shelf assignment',
                        onPressed: () => setState(() => _selectedShelfId = null),
                      )
                    : null,
              ),
              hint: const Text('Unassigned'),
              items: [
                const DropdownMenuItem<String?>(
                  value: null,
                  child: Text('— Unassigned —', style: TextStyle(color: Colors.grey)),
                ),
                ..._shelves.map((shelf) {
                  final id = shelf['shelf_id'] as String;
                  final label = _shelfLabel(shelf);
                  final notes = shelf['notes'] as String?;
                  return DropdownMenuItem<String?>(
                    value: id,
                    child: Row(
                      children: [
                        const Icon(Icons.shelves, size: 16),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(label, style: const TextStyle(fontWeight: FontWeight.w500)),
                              if (notes != null && notes.isNotEmpty)
                                Text(notes,
                                    style: TextStyle(
                                        fontSize: 11,
                                        color: Colors.grey.shade600),
                                    overflow: TextOverflow.ellipsis),
                            ],
                          ),
                        ),
                        Text(id,
                            style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
                      ],
                    ),
                  );
                }),
              ],
              onChanged: (v) => setState(() => _selectedShelfId = v),
              isExpanded: true,
            ),
    );
  }

  Widget _field(
    TextEditingController ctrl,
    String label, {
    bool enabled = true,
    int maxLines = 1,
    String? Function(String?)? validator,
  }) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextFormField(
          controller: ctrl,
          enabled: enabled,
          maxLines: maxLines,
          decoration: InputDecoration(labelText: label),
          validator: validator,
        ),
      );

  String? _required(String? v) =>
      (v == null || v.trim().isEmpty) ? 'This field is required' : null;
}
