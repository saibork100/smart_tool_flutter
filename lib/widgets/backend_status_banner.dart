import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/detector_service.dart';
import '../utils/app_theme.dart';
import '../utils/app_config.dart';

/// Shows a small banner if the local Python backend is unreachable.
class BackendStatusBanner extends StatefulWidget {
  const BackendStatusBanner({super.key});

  @override
  State<BackendStatusBanner> createState() => _BackendStatusBannerState();
}

class _BackendStatusBannerState extends State<BackendStatusBanner> {
  bool? _reachable;

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    final ok = await context.read<DetectorService>().isBackendReachable();
    if (mounted) setState(() => _reachable = ok);
  }

  @override
  Widget build(BuildContext context) {
    if (_reachable == null || _reachable == true) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      color: Colors.red.shade900,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          const Icon(Icons.warning_amber, color: Colors.black, size: 18),
          const SizedBox(width: 8),
          const Expanded(
            child: Text(
              'AI backend offline — barcode & name search still work.',
              style: TextStyle(fontSize: 13),
            ),
          ),
          TextButton(
            onPressed: _check,
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }
}
