// Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/detector_service.dart';
import '../utils/app_theme.dart';

class ReportDialog extends StatefulWidget {
  final File imageFile;
  final String detectedClass;

  const ReportDialog({
    super.key,
    required this.imageFile,
    required this.detectedClass,
  });

  @override
  State<ReportDialog> createState() => _ReportDialogState();
}

class _ReportDialogState extends State<ReportDialog> {
  List<String> _classes = [];
  String? _selectedClass;
  bool _loading = true;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _loadClasses();
  }

  Future<void> _loadClasses() async {
    final classes =
        await context.read<DetectorService>().getModelClasses();
    if (mounted) {
      setState(() {
        _classes  = classes;
        _loading  = false;
        // Pre-select a different class than the wrong one
        _selectedClass = classes.firstWhere(
          (c) => c != widget.detectedClass,
          orElse: () => classes.isNotEmpty ? classes.first : '',
        );
      });
    }
  }

  Future<void> _submit() async {
    if (_selectedClass == null || _selectedClass!.isEmpty) return;
    setState(() => _submitting = true);

    final ok = await context.read<DetectorService>().reportDetection(
          imageFile:    widget.imageFile,
          wrongClass:   widget.detectedClass,
          correctClass: _selectedClass!,
        );

    if (!mounted) return;
    Navigator.of(context).pop();
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(ok
          ? 'Report submitted — thank you!'
          : 'Failed to submit report. Check connection.'),
      backgroundColor: ok ? Colors.green : Colors.red,
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.flag_outlined, color: Colors.orange),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'Report Wrong Detection',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Photo thumbnail
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.file(
                widget.imageFile,
                height: 140,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
            ),
            const SizedBox(height: 16),

            // AI detected (read-only)
            Text('AI detected:', style: TextStyle(color: Colors.grey[600], fontSize: 12)),
            const SizedBox(height: 4),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: Text(
                widget.detectedClass,
                style: TextStyle(
                    color: Colors.red.shade700, fontWeight: FontWeight.w500),
              ),
            ),
            const SizedBox(height: 12),

            // Correct class dropdown
            Text('Correct class:', style: TextStyle(color: Colors.grey[600], fontSize: 12)),
            const SizedBox(height: 4),
            if (_loading)
              const Center(child: CircularProgressIndicator())
            else
              Container(
                decoration: BoxDecoration(
                  border: Border.all(color: AppTheme.primaryColor.withOpacity(0.4)),
                  borderRadius: BorderRadius.circular(8),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _selectedClass,
                    isExpanded: true,
                    menuMaxHeight: 300,
                    items: _classes
                        .map((c) => DropdownMenuItem(value: c, child: Text(c, style: const TextStyle(fontSize: 13))))
                        .toList(),
                    onChanged: (v) => setState(() => _selectedClass = v),
                  ),
                ),
              ),
            const SizedBox(height: 20),

            // Buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _submitting ? null : () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: (_submitting || _selectedClass == null) ? null : _submit,
                    icon: _submitting
                        ? const SizedBox(
                            width: 16, height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.send, size: 16),
                    label: Text(_submitting ? 'Sending…' : 'Submit'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryColor,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
