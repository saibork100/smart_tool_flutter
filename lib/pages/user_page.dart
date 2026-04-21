// Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
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
import '../widgets/report_dialog.dart';
import '../widgets/backend_status_banner.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:file_picker/file_picker.dart';

// ── Screw size photo instructions ─────────────────────────────────────────────

class _ScrewPhotoInstructions {
  final String label;
  final String title;
  final String distance;
  final String angle;
  final String tip;
  final double screwWidthRatio;  // silhouette width as fraction of frame
  final double screwLengthRatio; // silhouette length as fraction of frame

  const _ScrewPhotoInstructions({
    required this.label,
    required this.title,
    required this.distance,
    required this.angle,
    required this.tip,
    required this.screwWidthRatio,
    required this.screwLengthRatio,
  });
}

const Map<String, _ScrewPhotoInstructions> _screwInstructions = {
  // 4mm screws
  '4mm_10mm': _ScrewPhotoInstructions(label:'4mm_10mm', title:'4mm × 10mm Screw', distance:'5–8 cm', angle:'Flat, horizontal', tip:'Very small — bring camera close', screwWidthRatio:0.08, screwLengthRatio:0.22),
  '4mm_16mm': _ScrewPhotoInstructions(label:'4mm_16mm', title:'4mm × 16mm Screw', distance:'5–8 cm', angle:'Flat, horizontal', tip:'Keep ruler nearby for scale', screwWidthRatio:0.08, screwLengthRatio:0.30),
  '4mm_20mm': _ScrewPhotoInstructions(label:'4mm_20mm', title:'4mm × 20mm Screw', distance:'6–10 cm', angle:'Flat, horizontal', tip:'Ensure full length is visible', screwWidthRatio:0.08, screwLengthRatio:0.36),
  '4mm_25mm': _ScrewPhotoInstructions(label:'4mm_25mm', title:'4mm × 25mm Screw', distance:'8–12 cm', angle:'Flat, horizontal', tip:'Place on white background', screwWidthRatio:0.08, screwLengthRatio:0.42),
  '4mm_30mm': _ScrewPhotoInstructions(label:'4mm_30mm', title:'4mm × 30mm Screw', distance:'8–12 cm', angle:'Flat, horizontal', tip:'Thread pattern must be visible', screwWidthRatio:0.08, screwLengthRatio:0.50),
  '4mm_40mm': _ScrewPhotoInstructions(label:'4mm_40mm', title:'4mm × 40mm Screw', distance:'10–15 cm', angle:'Flat, horizontal', tip:'Place on contrasting surface', screwWidthRatio:0.08, screwLengthRatio:0.60),
  '4mm_50mm': _ScrewPhotoInstructions(label:'4mm_50mm', title:'4mm × 50mm Screw', distance:'12–18 cm', angle:'Flat, horizontal', tip:'Full screw must fit in frame', screwWidthRatio:0.08, screwLengthRatio:0.70),
  // 5mm screws
  '5mm_10mm': _ScrewPhotoInstructions(label:'5mm_10mm', title:'5mm × 10mm Screw', distance:'5–8 cm', angle:'Flat, horizontal', tip:'Wider head — show head clearly', screwWidthRatio:0.10, screwLengthRatio:0.22),
  '5mm_16mm': _ScrewPhotoInstructions(label:'5mm_16mm', title:'5mm × 16mm Screw', distance:'5–8 cm', angle:'Flat, horizontal', tip:'Keep screw centred in frame', screwWidthRatio:0.10, screwLengthRatio:0.30),
  '5mm_20mm': _ScrewPhotoInstructions(label:'5mm_20mm', title:'5mm × 20mm Screw', distance:'6–10 cm', angle:'Flat, horizontal', tip:'Good lighting helps accuracy', screwWidthRatio:0.10, screwLengthRatio:0.36),
  '5mm_25mm': _ScrewPhotoInstructions(label:'5mm_25mm', title:'5mm × 25mm Screw', distance:'8–12 cm', angle:'Flat, horizontal', tip:'White or grey background best', screwWidthRatio:0.10, screwLengthRatio:0.42),
  '5mm_30mm': _ScrewPhotoInstructions(label:'5mm_30mm', title:'5mm × 30mm Screw', distance:'8–12 cm', angle:'Flat, horizontal', tip:'Avoid shadows on screw', screwWidthRatio:0.10, screwLengthRatio:0.50),
  '5mm_40mm': _ScrewPhotoInstructions(label:'5mm_40mm', title:'5mm × 40mm Screw', distance:'10–15 cm', angle:'Flat, horizontal', tip:'Thread must be in focus', screwWidthRatio:0.10, screwLengthRatio:0.60),
  '5mm_50mm': _ScrewPhotoInstructions(label:'5mm_50mm', title:'5mm × 50mm Screw', distance:'12–18 cm', angle:'Flat, horizontal', tip:'Full length must be visible', screwWidthRatio:0.10, screwLengthRatio:0.70),
  // 6mm screws
  '6mm_12mm': _ScrewPhotoInstructions(label:'6mm_12mm', title:'6mm × 12mm Screw', distance:'5–8 cm', angle:'Flat, horizontal', tip:'Show head and thread together', screwWidthRatio:0.12, screwLengthRatio:0.25),
  '6mm_16mm': _ScrewPhotoInstructions(label:'6mm_16mm', title:'6mm × 16mm Screw', distance:'5–8 cm', angle:'Flat, horizontal', tip:'Wider screw — closer camera', screwWidthRatio:0.12, screwLengthRatio:0.30),
  '6mm_20mm': _ScrewPhotoInstructions(label:'6mm_20mm', title:'6mm × 20mm Screw', distance:'6–10 cm', angle:'Flat, horizontal', tip:'Natural light preferred', screwWidthRatio:0.12, screwLengthRatio:0.36),
  '6mm_25mm': _ScrewPhotoInstructions(label:'6mm_25mm', title:'6mm × 25mm Screw', distance:'8–12 cm', angle:'Flat, horizontal', tip:'Avoid reflective surfaces', screwWidthRatio:0.12, screwLengthRatio:0.42),
  '6mm_30mm': _ScrewPhotoInstructions(label:'6mm_30mm', title:'6mm × 30mm Screw', distance:'8–12 cm', angle:'Flat, horizontal', tip:'Keep screw straight in frame', screwWidthRatio:0.12, screwLengthRatio:0.50),
  '6mm_40mm': _ScrewPhotoInstructions(label:'6mm_40mm', title:'6mm × 40mm Screw', distance:'10–15 cm', angle:'Flat, horizontal', tip:'Ensure sharp focus on thread', screwWidthRatio:0.12, screwLengthRatio:0.60),
  '6mm_50mm': _ScrewPhotoInstructions(label:'6mm_50mm', title:'6mm × 50mm Screw', distance:'12–18 cm', angle:'Flat, horizontal', tip:'Step back slightly for longer screws', screwWidthRatio:0.12, screwLengthRatio:0.70),
  '6mm_60mm': _ScrewPhotoInstructions(label:'6mm_60mm', title:'6mm × 60mm Screw', distance:'15–20 cm', angle:'Flat, horizontal', tip:'Landscape orientation works better', screwWidthRatio:0.12, screwLengthRatio:0.78),
  '6mm_70mm': _ScrewPhotoInstructions(label:'6mm_70mm', title:'6mm × 70mm Screw', distance:'18–22 cm', angle:'Flat, horizontal', tip:'Long screw — ensure full length fits', screwWidthRatio:0.12, screwLengthRatio:0.85),
  '6mm_80mm': _ScrewPhotoInstructions(label:'6mm_80mm', title:'6mm × 80mm Screw', distance:'20–25 cm', angle:'Flat, horizontal', tip:'Step back to capture full length', screwWidthRatio:0.12, screwLengthRatio:0.88),
  '6mm_100mm': _ScrewPhotoInstructions(label:'6mm_100mm', title:'6mm × 100mm Screw', distance:'25–30 cm', angle:'Flat, horizontal', tip:'Longest screw — use landscape mode', screwWidthRatio:0.12, screwLengthRatio:0.92),
  // M8 — diameter 8mm → widthRatio ~0.15 (vs M6:0.12, proportional to real size)
  '8mm_16mm':  _ScrewPhotoInstructions(label:'8mm_16mm',  title:'M8 × 16mm',  distance:'5–8 cm',   angle:'Flat, horizontal', tip:'Short bolt — bring camera close',          screwWidthRatio:0.15, screwLengthRatio:0.28),
  '8mm_20mm':  _ScrewPhotoInstructions(label:'8mm_20mm',  title:'M8 × 20mm',  distance:'6–10 cm',  angle:'Flat, horizontal', tip:'Keep screw centred in frame',             screwWidthRatio:0.15, screwLengthRatio:0.34),
  '8mm_25mm':  _ScrewPhotoInstructions(label:'8mm_25mm',  title:'M8 × 25mm',  distance:'8–12 cm',  angle:'Flat, horizontal', tip:'Good lighting helps accuracy',            screwWidthRatio:0.15, screwLengthRatio:0.40),
  '8mm_30mm':  _ScrewPhotoInstructions(label:'8mm_30mm',  title:'M8 × 30mm',  distance:'8–12 cm',  angle:'Flat, horizontal', tip:'White or grey background best',           screwWidthRatio:0.15, screwLengthRatio:0.48),
  '8mm_40mm':  _ScrewPhotoInstructions(label:'8mm_40mm',  title:'M8 × 40mm',  distance:'10–15 cm', angle:'Flat, horizontal', tip:'Avoid shadows on screw',                 screwWidthRatio:0.15, screwLengthRatio:0.58),
  '8mm_50mm':  _ScrewPhotoInstructions(label:'8mm_50mm',  title:'M8 × 50mm',  distance:'12–18 cm', angle:'Flat, horizontal', tip:'Thread must be in focus',                screwWidthRatio:0.15, screwLengthRatio:0.66),
  '8mm_60mm':  _ScrewPhotoInstructions(label:'8mm_60mm',  title:'M8 × 60mm',  distance:'15–20 cm', angle:'Flat, horizontal', tip:'Landscape orientation works better',     screwWidthRatio:0.15, screwLengthRatio:0.74),
  '8mm_70mm':  _ScrewPhotoInstructions(label:'8mm_70mm',  title:'M8 × 70mm',  distance:'18–22 cm', angle:'Flat, horizontal', tip:'Long screw — ensure full length fits',   screwWidthRatio:0.15, screwLengthRatio:0.80),
  '8mm_80mm':  _ScrewPhotoInstructions(label:'8mm_80mm',  title:'M8 × 80mm',  distance:'20–25 cm', angle:'Flat, horizontal', tip:'Step back to capture full length',       screwWidthRatio:0.15, screwLengthRatio:0.85),
  '8mm_100mm': _ScrewPhotoInstructions(label:'8mm_100mm', title:'M8 × 100mm', distance:'25–30 cm', angle:'Flat, horizontal', tip:'Use landscape mode for long screws',     screwWidthRatio:0.15, screwLengthRatio:0.90),
  '8mm_120mm': _ScrewPhotoInstructions(label:'8mm_120mm', title:'M8 × 120mm', distance:'28–35 cm', angle:'Flat, horizontal', tip:'Use landscape mode, step well back',     screwWidthRatio:0.15, screwLengthRatio:0.93),
  '8mm_150mm': _ScrewPhotoInstructions(label:'8mm_150mm', title:'M8 × 150mm', distance:'35–40 cm', angle:'Flat, horizontal', tip:'Very long — landscape mode required',    screwWidthRatio:0.15, screwLengthRatio:0.96),
  // M10 — diameter 10mm → widthRatio ~0.19
  '10mm_16mm':  _ScrewPhotoInstructions(label:'10mm_16mm',  title:'M10 × 16mm',  distance:'5–8 cm',   angle:'Flat, horizontal', tip:'Short bolt — bring camera close',         screwWidthRatio:0.19, screwLengthRatio:0.26),
  '10mm_20mm':  _ScrewPhotoInstructions(label:'10mm_20mm',  title:'M10 × 20mm',  distance:'6–10 cm',  angle:'Flat, horizontal', tip:'Wider head — show it clearly',            screwWidthRatio:0.19, screwLengthRatio:0.33),
  '10mm_25mm':  _ScrewPhotoInstructions(label:'10mm_25mm',  title:'M10 × 25mm',  distance:'8–12 cm',  angle:'Flat, horizontal', tip:'Good lighting helps accuracy',            screwWidthRatio:0.19, screwLengthRatio:0.40),
  '10mm_30mm':  _ScrewPhotoInstructions(label:'10mm_30mm',  title:'M10 × 30mm',  distance:'8–12 cm',  angle:'Flat, horizontal', tip:'White or grey background best',           screwWidthRatio:0.19, screwLengthRatio:0.48),
  '10mm_40mm':  _ScrewPhotoInstructions(label:'10mm_40mm',  title:'M10 × 40mm',  distance:'10–15 cm', angle:'Flat, horizontal', tip:'Avoid shadows on screw',                 screwWidthRatio:0.19, screwLengthRatio:0.56),
  '10mm_50mm':  _ScrewPhotoInstructions(label:'10mm_50mm',  title:'M10 × 50mm',  distance:'12–18 cm', angle:'Flat, horizontal', tip:'Thread must be in focus',                screwWidthRatio:0.19, screwLengthRatio:0.64),
  '10mm_60mm':  _ScrewPhotoInstructions(label:'10mm_60mm',  title:'M10 × 60mm',  distance:'15–20 cm', angle:'Flat, horizontal', tip:'Landscape orientation works better',     screwWidthRatio:0.19, screwLengthRatio:0.71),
  '10mm_70mm':  _ScrewPhotoInstructions(label:'10mm_70mm',  title:'M10 × 70mm',  distance:'18–22 cm', angle:'Flat, horizontal', tip:'Long screw — ensure full length fits',   screwWidthRatio:0.19, screwLengthRatio:0.78),
  '10mm_80mm':  _ScrewPhotoInstructions(label:'10mm_80mm',  title:'M10 × 80mm',  distance:'20–25 cm', angle:'Flat, horizontal', tip:'Step back to capture full length',       screwWidthRatio:0.19, screwLengthRatio:0.84),
  '10mm_100mm': _ScrewPhotoInstructions(label:'10mm_100mm', title:'M10 × 100mm', distance:'25–30 cm', angle:'Flat, horizontal', tip:'Use landscape mode',                     screwWidthRatio:0.19, screwLengthRatio:0.90),
  '10mm_120mm': _ScrewPhotoInstructions(label:'10mm_120mm', title:'M10 × 120mm', distance:'28–35 cm', angle:'Flat, horizontal', tip:'Use landscape mode, step well back',     screwWidthRatio:0.19, screwLengthRatio:0.93),
  '10mm_150mm': _ScrewPhotoInstructions(label:'10mm_150mm', title:'M10 × 150mm', distance:'35–40 cm', angle:'Flat, horizontal', tip:'Very long — landscape mode required',    screwWidthRatio:0.19, screwLengthRatio:0.96),
  // M12 — diameter 12mm → widthRatio ~0.22
  '12mm_20mm':  _ScrewPhotoInstructions(label:'12mm_20mm',  title:'M12 × 20mm',  distance:'6–10 cm',  angle:'Flat, horizontal', tip:'Short thick bolt — camera close',         screwWidthRatio:0.22, screwLengthRatio:0.32),
  '12mm_25mm':  _ScrewPhotoInstructions(label:'12mm_25mm',  title:'M12 × 25mm',  distance:'8–12 cm',  angle:'Flat, horizontal', tip:'Show full hex head',                      screwWidthRatio:0.22, screwLengthRatio:0.38),
  '12mm_30mm':  _ScrewPhotoInstructions(label:'12mm_30mm',  title:'M12 × 30mm',  distance:'8–12 cm',  angle:'Flat, horizontal', tip:'White or grey background best',           screwWidthRatio:0.22, screwLengthRatio:0.44),
  '12mm_40mm':  _ScrewPhotoInstructions(label:'12mm_40mm',  title:'M12 × 40mm',  distance:'10–15 cm', angle:'Flat, horizontal', tip:'Avoid shadows on screw',                 screwWidthRatio:0.22, screwLengthRatio:0.54),
  '12mm_50mm':  _ScrewPhotoInstructions(label:'12mm_50mm',  title:'M12 × 50mm',  distance:'12–18 cm', angle:'Flat, horizontal', tip:'Thread must be in focus',                screwWidthRatio:0.22, screwLengthRatio:0.62),
  '12mm_60mm':  _ScrewPhotoInstructions(label:'12mm_60mm',  title:'M12 × 60mm',  distance:'15–20 cm', angle:'Flat, horizontal', tip:'Landscape orientation works better',     screwWidthRatio:0.22, screwLengthRatio:0.70),
  '12mm_80mm':  _ScrewPhotoInstructions(label:'12mm_80mm',  title:'M12 × 80mm',  distance:'20–25 cm', angle:'Flat, horizontal', tip:'Step back to capture full length',       screwWidthRatio:0.22, screwLengthRatio:0.82),
  '12mm_100mm': _ScrewPhotoInstructions(label:'12mm_100mm', title:'M12 × 100mm', distance:'25–30 cm', angle:'Flat, horizontal', tip:'Use landscape mode',                     screwWidthRatio:0.22, screwLengthRatio:0.88),
  '12mm_120mm': _ScrewPhotoInstructions(label:'12mm_120mm', title:'M12 × 120mm', distance:'28–35 cm', angle:'Flat, horizontal', tip:'Use landscape mode, step well back',     screwWidthRatio:0.22, screwLengthRatio:0.92),
  // M14 — diameter 14mm → widthRatio ~0.26
  '14mm_25mm':  _ScrewPhotoInstructions(label:'14mm_25mm',  title:'M14 × 25mm',  distance:'8–12 cm',  angle:'Flat, horizontal', tip:'Show full hex head',                      screwWidthRatio:0.26, screwLengthRatio:0.36),
  '14mm_30mm':  _ScrewPhotoInstructions(label:'14mm_30mm',  title:'M14 × 30mm',  distance:'8–12 cm',  angle:'Flat, horizontal', tip:'White or grey background best',           screwWidthRatio:0.26, screwLengthRatio:0.42),
  '14mm_35mm':  _ScrewPhotoInstructions(label:'14mm_35mm',  title:'M14 × 35mm',  distance:'10–14 cm', angle:'Flat, horizontal', tip:'Show full hex head clearly',              screwWidthRatio:0.26, screwLengthRatio:0.48),
  '14mm_40mm':  _ScrewPhotoInstructions(label:'14mm_40mm',  title:'M14 × 40mm',  distance:'10–15 cm', angle:'Flat, horizontal', tip:'Avoid shadows on screw',                 screwWidthRatio:0.26, screwLengthRatio:0.54),
  '14mm_50mm':  _ScrewPhotoInstructions(label:'14mm_50mm',  title:'M14 × 50mm',  distance:'12–18 cm', angle:'Flat, horizontal', tip:'Thread must be in focus',                screwWidthRatio:0.26, screwLengthRatio:0.62),
  '14mm_60mm':  _ScrewPhotoInstructions(label:'14mm_60mm',  title:'M14 × 60mm',  distance:'15–20 cm', angle:'Flat, horizontal', tip:'Landscape orientation works better',     screwWidthRatio:0.26, screwLengthRatio:0.70),
  '14mm_80mm':  _ScrewPhotoInstructions(label:'14mm_80mm',  title:'M14 × 80mm',  distance:'20–25 cm', angle:'Flat, horizontal', tip:'Step back to capture full length',       screwWidthRatio:0.26, screwLengthRatio:0.80),
  '14mm_100mm': _ScrewPhotoInstructions(label:'14mm_100mm', title:'M14 × 100mm', distance:'25–30 cm', angle:'Flat, horizontal', tip:'Use landscape mode',                     screwWidthRatio:0.26, screwLengthRatio:0.87),
  // M16 — diameter 16mm → widthRatio ~0.30
  '16mm_30mm':  _ScrewPhotoInstructions(label:'16mm_30mm',  title:'M16 × 30mm',  distance:'8–12 cm',  angle:'Flat, horizontal', tip:'Large head — show it clearly',            screwWidthRatio:0.30, screwLengthRatio:0.40),
  '16mm_40mm':  _ScrewPhotoInstructions(label:'16mm_40mm',  title:'M16 × 40mm',  distance:'10–15 cm', angle:'Flat, horizontal', tip:'Large head — show it clearly',            screwWidthRatio:0.30, screwLengthRatio:0.48),
  '16mm_50mm':  _ScrewPhotoInstructions(label:'16mm_50mm',  title:'M16 × 50mm',  distance:'12–18 cm', angle:'Flat, horizontal', tip:'Thread must be in focus',                screwWidthRatio:0.30, screwLengthRatio:0.57),
  '16mm_60mm':  _ScrewPhotoInstructions(label:'16mm_60mm',  title:'M16 × 60mm',  distance:'15–20 cm', angle:'Flat, horizontal', tip:'Landscape orientation works better',     screwWidthRatio:0.30, screwLengthRatio:0.65),
  '16mm_80mm':  _ScrewPhotoInstructions(label:'16mm_80mm',  title:'M16 × 80mm',  distance:'20–25 cm', angle:'Flat, horizontal', tip:'Step back to capture full length',       screwWidthRatio:0.30, screwLengthRatio:0.76),
  '16mm_100mm': _ScrewPhotoInstructions(label:'16mm_100mm', title:'M16 × 100mm', distance:'25–30 cm', angle:'Flat, horizontal', tip:'Use landscape mode',                     screwWidthRatio:0.30, screwLengthRatio:0.84),
  '16mm_120mm': _ScrewPhotoInstructions(label:'16mm_120mm', title:'M16 × 120mm', distance:'28–35 cm', angle:'Flat, horizontal', tip:'Use landscape mode, step well back',     screwWidthRatio:0.30, screwLengthRatio:0.90),
  // M20 — diameter 20mm → widthRatio ~0.37
  '20mm_50mm':  _ScrewPhotoInstructions(label:'20mm_50mm',  title:'M20 × 50mm',  distance:'15–20 cm', angle:'Flat, horizontal', tip:'Very wide head — camera 20 cm back',     screwWidthRatio:0.37, screwLengthRatio:0.55),
  '20mm_60mm':  _ScrewPhotoInstructions(label:'20mm_60mm',  title:'M20 × 60mm',  distance:'18–22 cm', angle:'Flat, horizontal', tip:'Landscape orientation works better',     screwWidthRatio:0.37, screwLengthRatio:0.63),
  '20mm_80mm':  _ScrewPhotoInstructions(label:'20mm_80mm',  title:'M20 × 80mm',  distance:'22–28 cm', angle:'Flat, horizontal', tip:'Step back to capture full length',       screwWidthRatio:0.37, screwLengthRatio:0.74),
  '20mm_100mm': _ScrewPhotoInstructions(label:'20mm_100mm', title:'M20 × 100mm', distance:'28–35 cm', angle:'Flat, horizontal', tip:'Use landscape mode',                     screwWidthRatio:0.37, screwLengthRatio:0.83),
  '20mm_120mm': _ScrewPhotoInstructions(label:'20mm_120mm', title:'M20 × 120mm', distance:'32–40 cm', angle:'Flat, horizontal', tip:'Use landscape mode, step well back',     screwWidthRatio:0.37, screwLengthRatio:0.90),
  // M24 — diameter 24mm → widthRatio ~0.44
  '24mm_60mm':  _ScrewPhotoInstructions(label:'24mm_60mm',  title:'M24 × 60mm',  distance:'20–25 cm', angle:'Flat, horizontal', tip:'Very wide — keep full head in frame',    screwWidthRatio:0.44, screwLengthRatio:0.60),
  '24mm_80mm':  _ScrewPhotoInstructions(label:'24mm_80mm',  title:'M24 × 80mm',  distance:'25–30 cm', angle:'Flat, horizontal', tip:'Use landscape mode',                     screwWidthRatio:0.44, screwLengthRatio:0.72),
  '24mm_100mm': _ScrewPhotoInstructions(label:'24mm_100mm', title:'M24 × 100mm', distance:'28–35 cm', angle:'Flat, horizontal', tip:'Use landscape mode, step well back',     screwWidthRatio:0.44, screwLengthRatio:0.82),
  // M27 — diameter 27mm → widthRatio ~0.50 (very wide, takes up half the frame)
  '27mm_60mm':  _ScrewPhotoInstructions(label:'27mm_60mm',  title:'M27 × 60mm',  distance:'22–28 cm', angle:'Flat, horizontal', tip:'Very wide bolt — step well back',        screwWidthRatio:0.50, screwLengthRatio:0.58),
  '27mm_80mm':  _ScrewPhotoInstructions(label:'27mm_80mm',  title:'M27 × 80mm',  distance:'25–32 cm', angle:'Flat, horizontal', tip:'Use landscape mode',                     screwWidthRatio:0.50, screwLengthRatio:0.68),
  '27mm_100mm': _ScrewPhotoInstructions(label:'27mm_100mm', title:'M27 × 100mm', distance:'28–35 cm', angle:'Flat, horizontal', tip:'Use landscape mode, step well back',     screwWidthRatio:0.50, screwLengthRatio:0.77),
  '27mm_130mm': _ScrewPhotoInstructions(label:'27mm_130mm', title:'M27 × 130mm', distance:'32–40 cm', angle:'Flat, horizontal', tip:'Very long — use landscape, step back 40cm', screwWidthRatio:0.50, screwLengthRatio:0.86),
  '27mm_280mm': _ScrewPhotoInstructions(label:'27mm_280mm', title:'M27 × 280mm', distance:'60–80 cm', angle:'Flat, horizontal', tip:'Extremely long — use landscape, step far back', screwWidthRatio:0.50, screwLengthRatio:0.97),
  // M30 — diameter 30mm → widthRatio ~0.55
  '30mm_80mm':  _ScrewPhotoInstructions(label:'30mm_80mm',  title:'M30 × 80mm',  distance:'28–35 cm', angle:'Flat, horizontal', tip:'Very wide bolt — step well back',        screwWidthRatio:0.55, screwLengthRatio:0.66),
  '30mm_100mm': _ScrewPhotoInstructions(label:'30mm_100mm', title:'M30 × 100mm', distance:'32–40 cm', angle:'Flat, horizontal', tip:'Use landscape mode',                     screwWidthRatio:0.55, screwLengthRatio:0.76),
  // M33 — diameter 33mm → widthRatio ~0.60
  '33mm_100mm': _ScrewPhotoInstructions(label:'33mm_100mm', title:'M33 × 100mm', distance:'32–40 cm', angle:'Flat, horizontal', tip:'Very wide bolt — step well back',        screwWidthRatio:0.60, screwLengthRatio:0.74),
  '33mm_250mm': _ScrewPhotoInstructions(label:'33mm_250mm', title:'M33 × 250mm', distance:'60–80 cm', angle:'Flat, horizontal', tip:'Extremely long — use landscape, step far back', screwWidthRatio:0.60, screwLengthRatio:0.96),
};

_ScrewPhotoInstructions _defaultInstructions = const _ScrewPhotoInstructions(
  label: '', title: 'Screw', distance: '8–15 cm', angle: 'Flat, horizontal',
  tip: 'Place screw on white background, ensure full length visible',
  screwWidthRatio: 0.10, screwLengthRatio: 0.50,
);

// ── Screw Silhouette Painter ───────────────────────────────────────────────────

class _ScrewSilhouettePainter extends CustomPainter {
  final double widthRatio;
  final double lengthRatio;
  final Color color;

  const _ScrewSilhouettePainter({
    required this.widthRatio,
    required this.lengthRatio,
    required this.color,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final fillPaint = Paint()
      ..color = color.withOpacity(0.08)
      ..style = PaintingStyle.fill;

    final cx = size.width / 2;
    final cy = size.height / 2;
    final screwW = size.width * widthRatio;
    final screwL = size.width * lengthRatio;

    final headW = screwW * 2.2;
    final headH = screwW * 1.2;
    final shankL = screwL - headH;

    // Head (left side)
    final headRect = Rect.fromCenter(
      center: Offset(cx - shankL / 2, cy),
      width: headW,
      height: headH * 2,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(headRect, Radius.circular(headH * 0.4)),
      fillPaint,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(headRect, Radius.circular(headH * 0.4)),
      paint,
    );

    // Slot on head
    canvas.drawLine(
      Offset(cx - shankL / 2 - headW * 0.25, cy),
      Offset(cx - shankL / 2 + headW * 0.25, cy),
      paint,
    );

    // Shank (body)
    final shankRect = Rect.fromCenter(
      center: Offset(cx + headH * 0.3, cy),
      width: shankL,
      height: screwW * 1.2,
    );
    canvas.drawRect(shankRect, fillPaint);
    canvas.drawRect(shankRect, paint);

    // Thread lines on shank
    final threadCount = (shankL / (screwW * 0.8)).floor().clamp(3, 12);
    for (int i = 1; i < threadCount; i++) {
      final x = shankRect.left + (shankL * i / threadCount);
      canvas.drawLine(
        Offset(x, shankRect.top),
        Offset(x, shankRect.bottom),
        Paint()..color = color.withOpacity(0.4)..strokeWidth = 1,
      );
    }

    // Tip (right side triangle)
    final tipPath = Path()
      ..moveTo(shankRect.right, shankRect.top)
      ..lineTo(shankRect.right, shankRect.bottom)
      ..lineTo(shankRect.right + screwW * 1.2, cy)
      ..close();
    canvas.drawPath(tipPath, fillPaint);
    canvas.drawPath(tipPath, paint);

    // Dashed guide box
    final boxPaint = Paint()
      ..color = color.withOpacity(0.5)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    final boxRect = Rect.fromCenter(
      center: Offset(cx, cy),
      width: screwL + headW + screwW * 3,
      height: headH * 3.5,
    );
    _drawDashedRect(canvas, boxRect, boxPaint);

    // Corner markers
    const markerSize = 12.0;
    final markerPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round;

    for (final corner in [
      boxRect.topLeft, boxRect.topRight,
      boxRect.bottomLeft, boxRect.bottomRight,
    ]) {
      final isRight = corner.dx > cx;
      final isBottom = corner.dy > cy;
      canvas.drawLine(corner, corner + Offset(isRight ? -markerSize : markerSize, 0), markerPaint);
      canvas.drawLine(corner, corner + Offset(0, isBottom ? -markerSize : markerSize), markerPaint);
    }
  }

  void _drawDashedRect(Canvas canvas, Rect rect, Paint paint) {
    const dash = 6.0;
    const gap = 4.0;
    for (double x = rect.left; x < rect.right; x += dash + gap) {
      canvas.drawLine(Offset(x, rect.top), Offset((x + dash).clamp(0, rect.right), rect.top), paint);
      canvas.drawLine(Offset(x, rect.bottom), Offset((x + dash).clamp(0, rect.right), rect.bottom), paint);
    }
    for (double y = rect.top; y < rect.bottom; y += dash + gap) {
      canvas.drawLine(Offset(rect.left, y), Offset(rect.left, (y + dash).clamp(0, rect.bottom)), paint);
      canvas.drawLine(Offset(rect.right, y), Offset(rect.right, (y + dash).clamp(0, rect.bottom)), paint);
    }
  }

  @override
  bool shouldRepaint(_ScrewSilhouettePainter old) =>
      old.widthRatio != widthRatio || old.lengthRatio != lengthRatio;
}

// ── Photo Guide Widget ────────────────────────────────────────────────────────

class _PhotoGuideWidget extends StatelessWidget {
  final _ScrewPhotoInstructions instructions;
  final VoidCallback onTakePhoto;
  final VoidCallback? onPickGallery;
  final bool isRetake;

  const _PhotoGuideWidget({
    required this.instructions,
    required this.onTakePhoto,
    this.onPickGallery,
    this.isRetake = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.grey.shade900,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Title bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: isRetake ? Colors.orange.shade800 : AppTheme.primaryColor,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
            ),
            child: Row(
              children: [
                Icon(isRetake ? Icons.refresh : Icons.camera_alt,
                    color: Colors.white, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    isRetake
                        ? 'Retake — Follow these instructions'
                        : 'Photo Guide: ${instructions.title}',
                    style: const TextStyle(
                        color: Colors.white, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
          ),

          // Silhouette preview
          Container(
            height: 140,
            width: double.infinity,
            color: Colors.grey.shade800,
            child: CustomPaint(
              painter: _ScrewSilhouettePainter(
                widthRatio: instructions.screwWidthRatio,
                lengthRatio: instructions.screwLengthRatio,
                color: isRetake ? Colors.orange : AppTheme.accentColor,
              ),
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.only(top: 100),
                  child: Text(
                    'Align your screw inside the frame',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.7),
                      fontSize: 11,
                    ),
                  ),
                ),
              ),
            ),
          ),

          // Instructions
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: [
                _InstructionRow(Icons.straighten, 'Distance', instructions.distance),
                const SizedBox(height: 6),
                _InstructionRow(Icons.rotate_right, 'Angle', instructions.angle),
                const SizedBox(height: 6),
                _InstructionRow(Icons.lightbulb_outline, 'Tip', instructions.tip),
              ],
            ),
          ),

          // Buttons
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            child: Row(
              children: [
                if (onPickGallery != null) ...[
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: onPickGallery,
                      icon: const Icon(Icons.photo_library, size: 16),
                      label: const Text('Gallery'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white54,
                        side: const BorderSide(color: Colors.white24),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                ],
                Expanded(
                  flex: 2,
                  child: ElevatedButton.icon(
                    onPressed: onTakePhoto,
                    icon: Icon(isRetake ? Icons.refresh : Icons.camera_alt,
                        size: 16),
                    label: Text(isRetake ? 'Retake Photo' : 'Take Photo'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          isRetake ? Colors.orange : AppTheme.primaryColor,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InstructionRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _InstructionRow(this.icon, this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 16, color: AppTheme.accentColor),
        const SizedBox(width: 8),
        Text('$label: ', style: const TextStyle(
            color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold)),
        Expanded(
          child: Text(value,
              style: const TextStyle(color: Colors.white, fontSize: 12)),
        ),
      ],
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Converts "14mm_35mm" → "M14 × 35mm" for any diameter/length combination.
String _formatScrewLabel(String label) {
  final parts = label.split('_');
  if (parts.length == 2) {
    final d = parts[0].replaceAll('mm', '');
    final l = parts[1];
    return 'M$d × $l';
  }
  return label;
}

// ── Low Confidence Picker ─────────────────────────────────────────────────────

class _LowConfidencePicker extends StatelessWidget {
  final PredictionResult result;
  final File? imageFile;
  final VoidCallback onRetakeAnyway;
  final Function(String label) onSelectLabel;

  const _LowConfidencePicker({
    required this.result,
    this.imageFile,
    required this.onRetakeAnyway,
    required this.onSelectLabel,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.orange.shade50,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade100,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.help_outline, color: Colors.orange),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Low Confidence Detection',
                          style: TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 15)),
                      Text('Which screw is this?',
                          style: TextStyle(color: Colors.grey, fontSize: 12)),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Text('Select the correct screw to get better photo instructions:',
                style: TextStyle(fontSize: 12, color: Colors.black54)),
            const SizedBox(height: 10),

            // Top predictions as selectable tiles
            ...result.topPredictions.take(5).map((p) {
              final instr = _screwInstructions[p.label] ?? _defaultInstructions;
              final pct = (p.confidence * 100).toStringAsFixed(1);
              final displayName = _formatScrewLabel(p.label);
              return GestureDetector(
                onTap: () => onSelectLabel(p.label),
                child: Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.orange.shade200),
                  ),
                  child: Row(
                    children: [
                      // Mini silhouette
                      SizedBox(
                        width: 60,
                        height: 30,
                        child: CustomPaint(
                          painter: _ScrewSilhouettePainter(
                            widthRatio: instr.screwWidthRatio * 1.5,
                            lengthRatio: instr.screwLengthRatio * 0.8,
                            color: Colors.orange,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(displayName,
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold, fontSize: 13)),
                            Text('AI confidence: $pct%',
                                style: TextStyle(
                                    color: Colors.grey.shade600, fontSize: 11)),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.orange,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Text('Select',
                            style: TextStyle(
                                color: Colors.white,
                                fontSize: 11,
                                fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ),
              );
            }),

            const SizedBox(height: 4),
            TextButton.icon(
              onPressed: onRetakeAnyway,
              icon: const Icon(Icons.refresh, size: 16),
              label: const Text('None of these — retake photo'),
              style: TextButton.styleFrom(foregroundColor: Colors.orange),
            ),
            if (imageFile != null)
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: () => showDialog(
                    context: context,
                    builder: (_) => ReportDialog(
                      imageFile: imageFile!,
                      detectedClass: result.topPredictions.isNotEmpty
                          ? result.topPredictions.first.label
                          : '',
                    ),
                  ),
                  icon: const Icon(Icons.flag_outlined,
                      size: 15, color: Colors.orange),
                  label: const Text('Wrong result?',
                      style: TextStyle(color: Colors.orange, fontSize: 13)),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

// ── Main Page ─────────────────────────────────────────────────────────────────

class UserPage extends StatefulWidget {
  const UserPage({super.key});

  @override
  State<UserPage> createState() => _UserPageState();
}

class _UserPageState extends State<UserPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final ImagePicker _picker = ImagePicker();
  final TextEditingController _searchController = TextEditingController();

  File? _selectedImage;
  List<Product> _searchResults = [];
  bool _scannerActive = false;
  bool _rulerMode = false;   // when true, sends to /measure instead of /detect

  // Two-shot flow state
  String? _selectedLabel;  // label picked after low confidence
  bool _isRetakeMode = false;

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

  // ── Camera / image actions ──────────────────────────────────────────────────

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
      allowedExtensions: ['jpg','jpeg','png','bmp','heic','heif','webp','dng'],
    );
    if (result == null) return;
    await _runDetection(File(result.files.single.path!));
  }

  Future<void> _runDetection(File file) async {
    setState(() {
      _selectedImage = file;
      _isRetakeMode = false;
    });
    _tabController.animateTo(0);
    if (_rulerMode) {
      await context.read<DetectorService>().measureFromFile(file);
    } else {
      await context.read<DetectorService>().detectFromFile(file);
    }

    // After detection, check if low confidence
    final result = context.read<DetectorService>().lastResult;
    if (result != null && !result.isConfident) {
      // Enter two-shot mode — show picker
      setState(() {});
    }
  }

  // Called when user picks a label from low confidence picker
  void _onLabelSelected(String label) {
    setState(() {
      _selectedLabel = label;
      _isRetakeMode = true;
    });
  }

  // Called when user retakes without selecting
  void _onRetakeAnyway() {
    setState(() {
      _selectedLabel = null;
      _isRetakeMode = false;
      _selectedImage = null;
    });
    context.read<DetectorService>().clearResult();
  }

  // Called after retake with instructions
  Future<void> _retakeWithGuide() async {
    final xFile = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 90,
      maxWidth: 800,
    );
    if (xFile == null) return;
    await _runDetection(File(xFile.path));
    setState(() {
      _selectedLabel = null;
      _isRetakeMode = false;
    });
  }

  Future<void> _retakeFromGallery() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['jpg','jpeg','png','bmp','heic','heif','webp','dng'],
    );
    if (result == null) return;
    await _runDetection(File(result.files.single.path!));
    setState(() {
      _selectedLabel = null;
      _isRetakeMode = false;
    });
  }

  // ── Barcode handler ─────────────────────────────────────────────────────────

  void _onBarcodeDetected(BarcodeCapture capture) async {
    final barcode = capture.barcodes.firstOrNull?.rawValue;
    if (barcode == null || !_scannerActive) return;
    setState(() => _scannerActive = false);
    final product =
        await context.read<DetectorService>().lookupByBarcode(barcode);
    if (!mounted) return;
    if (product == null) {
      _showSnack('No product found for barcode: $barcode');
    } else {
      _showProductSheet(product);
    }
  }

  // ── Name search ─────────────────────────────────────────────────────────────

  Future<void> _search(String query) async {
    if (query.trim().isEmpty) {
      setState(() => _searchResults = []);
      return;
    }
    final results =
        await context.read<DetectorService>().searchByName(query);
    setState(() => _searchResults = results);
  }

  // ── Build ───────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final auth = context.read<AuthService>();
    final detector = context.watch<DetectorService>();

    // Determine what to show in identify tab
    final showLowConfPicker = !detector.isProcessing &&
        detector.lastResult != null &&
        !detector.lastResult!.isConfident &&
        !_isRetakeMode;

    final showRetakeGuide = _isRetakeMode && _selectedLabel != null;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Smart Tool Recognition'),
        actions: [
          // Ruler mode toggle
          Tooltip(
            message: _rulerMode ? 'Ruler mode ON — tap to switch to AI mode' : 'AI mode — tap to switch to Ruler mode',
            child: GestureDetector(
              onTap: () {
                setState(() => _rulerMode = !_rulerMode);
                context.read<DetectorService>().clearResult();
                setState(() {
                  _selectedImage = null;
                  _selectedLabel = null;
                  _isRetakeMode = false;
                });
              },
              child: Container(
                margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: _rulerMode ? Colors.blue.shade700 : Colors.white24,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      _rulerMode ? Icons.straighten : Icons.psychology,
                      color: Colors.white,
                      size: 16,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      _rulerMode ? 'Ruler' : 'AI',
                      style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ),
          ),
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
                  detector: detector,
                  showLowConfPicker: showLowConfPicker,
                  showRetakeGuide: showRetakeGuide,
                  selectedLabel: _selectedLabel,
                  onCamera: _captureFromCamera,
                  onGallery: _pickFromGallery,
                  onLabelSelected: _onLabelSelected,
                  onRetakeAnyway: _onRetakeAnyway,
                  onRetakeWithGuide: _retakeWithGuide,
                  onRetakeFromGallery: _retakeFromGallery,
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

  void _showSnack(String msg) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(msg)));

  void _showProductSheet(Product p) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => ProductResultCard(product: p),
    );
  }
}

// ── Identify Tab ──────────────────────────────────────────────────────────────

class _IdentifyTab extends StatelessWidget {
  final File? selectedImage;
  final DetectorService detector;
  final bool showLowConfPicker;
  final bool showRetakeGuide;
  final String? selectedLabel;
  final VoidCallback onCamera;
  final VoidCallback onGallery;
  final Function(String) onLabelSelected;
  final VoidCallback onRetakeAnyway;
  final VoidCallback onRetakeWithGuide;
  final VoidCallback onRetakeFromGallery;

  const _IdentifyTab({
    required this.selectedImage,
    required this.detector,
    required this.showLowConfPicker,
    required this.showRetakeGuide,
    required this.selectedLabel,
    required this.onCamera,
    required this.onGallery,
    required this.onLabelSelected,
    required this.onRetakeAnyway,
    required this.onRetakeWithGuide,
    required this.onRetakeFromGallery,
  });

  @override
  Widget build(BuildContext context) {
    final instructions = selectedLabel != null
        ? (_screwInstructions[selectedLabel!] ?? _defaultInstructions)
        : _defaultInstructions;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // ── Image preview ──────────────────────────────────────────────
          Container(
            height: 200,
            width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.grey.shade200,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey.shade300),
            ),
            child: selectedImage != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.file(selectedImage!, fit: BoxFit.contain,
                        width: double.infinity, height: double.infinity),
                  )
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.camera_alt_outlined,
                          size: 48, color: Colors.grey.shade400),
                      const SizedBox(height: 8),
                      Text(
                        'Take a photo or pick from gallery',
                        style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
          ),
          const SizedBox(height: 16),

          // ── Camera / Gallery buttons (shown when not in retake mode) ───
          if (!showRetakeGuide) ...[
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
            const SizedBox(height: 16),
          ],

          // ── Processing ─────────────────────────────────────────────────
          if (detector.isProcessing)
            const Column(
              children: [
                CircularProgressIndicator(),
                SizedBox(height: 12),
                Text('Analysing screw…'),
              ],
            )

          // ── Error ──────────────────────────────────────────────────────
          else if (detector.errorMessage != null)
            _ErrorCard(message: detector.errorMessage!)

          // ── Retake guide (after user picks label) ──────────────────────
          else if (showRetakeGuide)
            _PhotoGuideWidget(
              instructions: instructions,
              onTakePhoto: onRetakeWithGuide,
              onPickGallery: kIsWeb || Platform.isWindows
                  ? onRetakeFromGallery
                  : null,
              isRetake: true,
            )

          // ── Low confidence picker ──────────────────────────────────────
          else if (showLowConfPicker) ...[
            _LowConfidencePicker(
              result: detector.lastResult!,
              imageFile: selectedImage,
              onRetakeAnyway: onRetakeAnyway,
              onSelectLabel: onLabelSelected,
            ),
          ]

          // ── High confidence result ─────────────────────────────────────
          else if (detector.lastResult != null)
            _ResultView(result: detector.lastResult!, imageFile: selectedImage),
        ],
      ),
    );
  }
}

// ── Result View ───────────────────────────────────────────────────────────────

class _ResultView extends StatelessWidget {
  final PredictionResult result;
  final File? imageFile;
  const _ResultView({required this.result, this.imageFile});

  void _openReport(BuildContext context) {
    if (imageFile == null) return;
    final label = result.predictedLabel.isNotEmpty
        ? result.predictedLabel
        : (result.displayName ?? 'unknown');
    showDialog(
      context: context,
      builder: (_) => ReportDialog(
        imageFile:     imageFile!,
        detectedClass: label,
      ),
    );
  }

  Widget _reportButton(BuildContext context) => Align(
        alignment: Alignment.centerRight,
        child: TextButton.icon(
          onPressed: imageFile != null ? () => _openReport(context) : null,
          icon: const Icon(Icons.flag_outlined, size: 16, color: Colors.orange),
          label: const Text('Wrong result?',
              style: TextStyle(color: Colors.orange, fontSize: 12)),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final product = result.product;
    final isRuler = result.measurementNote != null;

    // ── YOLO11 parent-class result: size list available ─────────────────────
    if (result.hasSizeList) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ProductResultCard(
            displayName:    result.displayName,
            availableSizes: result.availableSizes,
            confidence:     result.confidence,
          ),
          _reportButton(context),
        ],
      );
    }

    // ── No product matched (low confidence or DB miss) ───────────────────────
    if (product == null) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Card(
            child: ListTile(
              leading: Icon(isRuler ? Icons.straighten : Icons.info_outline),
              title: Text(isRuler
                  ? 'Measured: ${result.predictedLabel.replaceAll('mm_', 'mm × ')}'
                  : 'Detected: ${result.predictedLabel}'),
              subtitle: Text(isRuler
                  ? '${result.measurementNote}\nNot found in database — try Search tab.'
                  : 'Confidence: ${(result.confidence * 100).toStringAsFixed(1)}%\nNot found in database.'),
            ),
          ),
          if (!isRuler) _reportButton(context),
        ],
      );
    }

    // ── Legacy single-product result ─────────────────────────────────────────
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        ProductResultCard(
          product:        product,
          confidence:     isRuler ? null : result.confidence,
          alternatives:   result.topPredictions.skip(1).toList(),
          measurementNote: result.measurementNote,
        ),
        if (!isRuler) _reportButton(context),
      ],
    );
  }
}

class _ErrorCard extends StatelessWidget {
  final String message;
  const _ErrorCard({required this.message});

  @override
  Widget build(BuildContext context) => Card(
        color: Colors.red.shade50,
        child: ListTile(
          leading:
              const Icon(Icons.error_outline, color: AppTheme.errorColor),
          title: Text(message,
              style: const TextStyle(color: AppTheme.errorColor)),
        ),
      );
}

// ── Barcode Tab ───────────────────────────────────────────────────────────────

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
            const Icon(Icons.qr_code_scanner,
                size: 80, color: AppTheme.primaryColor),
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

// ── Search Tab ────────────────────────────────────────────────────────────────

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
                    controller.text.isEmpty
                        ? 'Type to search products'
                        : 'No results found',
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
                        child: Text(
                            p.brand.isNotEmpty
                                ? p.brand[0].toUpperCase()
                                : '?',
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
      child: Text(label,
          style: TextStyle(
              color: color, fontSize: 11, fontWeight: FontWeight.bold)),
    );
  }
}