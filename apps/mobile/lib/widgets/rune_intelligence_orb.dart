import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../theme/rune_colors.dart';

/// The R.U.N.E. intelligence orb.
///
/// Built from the supplied 20,000-point sphere renderer. The touch-ripple
/// simulation has deliberately been removed: the orb is a calm, autonomous
/// visual presence, with slow rotation, depth, bloom and an orbital light.
class RuneIntelligenceOrb extends StatefulWidget {
  const RuneIntelligenceOrb({super.key, this.size = 230, this.intensity = 1});

  final double size;
  final double intensity;

  @override
  State<RuneIntelligenceOrb> createState() => _RuneIntelligenceOrbState();
}

class _RuneIntelligenceOrbState extends State<RuneIntelligenceOrb>
    with SingleTickerProviderStateMixin {
  late final AnimationController _animation = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 38),
  )..repeat();

  @override
  void dispose() {
    _animation.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => RepaintBoundary(
        child: AnimatedBuilder(
          animation: _animation,
          builder: (context, _) => SizedBox.square(
            dimension: widget.size,
            child: CustomPaint(
              painter: _RuneOrbPainter(
                progress: _animation.value,
                intensity: widget.intensity,
              ),
            ),
          ),
        ),
      );
}

class _RuneOrbPainter extends CustomPainter {
  _RuneOrbPainter({required this.progress, required this.intensity});

  static const int _count = 20000;
  static const double _radius = 1;
  static const double _cameraDistance = 3.4;

  static final Float32List _x = _createAxis(0);
  static final Float32List _y = _createAxis(1);
  static final Float32List _z = _createAxis(2);

  final double progress;
  final double intensity;
  final Float32List _front = Float32List(_count * 2);
  final Float32List _back = Float32List(_count * 2);
  final Paint _frontPaint = Paint()
    ..color = RuneColors.mint
    ..strokeWidth = 1.25
    ..strokeCap = StrokeCap.round
    ..isAntiAlias = true;
  final Paint _frontGlow = Paint()
    ..color = const Color(0x5500E58A)
    ..strokeWidth = 4.2
    ..strokeCap = StrokeCap.round
    ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2.8);
  final Paint _backPaint = Paint()
    ..color = const Color(0x5546C98C)
    ..strokeWidth = .85
    ..strokeCap = StrokeCap.round;

  static Float32List _createAxis(int axis) {
    final values = Float32List(_count);
    final thetaStep = math.sqrt(_count * math.pi);
    for (var i = 0; i < _count; i++) {
      final phi = math.acos(-1 + (2 * i) / _count);
      final theta = thetaStep * phi;
      final sinPhi = math.sin(phi);
      if (axis == 0) {
        values[i] = _radius * math.cos(theta) * sinPhi;
      } else if (axis == 1) {
        values[i] = _radius * math.sin(theta) * sinPhi;
      } else {
        values[i] = _radius * math.cos(phi);
      }
    }
    return values;
  }

  @override
  void paint(Canvas canvas, Size size) {
    final elapsed = progress * math.pi * 2;
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.shortestSide * .335;
    final pulse = 1 + math.sin(elapsed * .5) * .018;
    final yaw = elapsed * .42;
    final pitch = math.sin(elapsed * .22) * .12;
    final cy = math.cos(yaw), sy = math.sin(yaw);
    final cp = math.cos(pitch), sp = math.sin(pitch);
    final bloomRadius = radius * 1.7;

    canvas.drawCircle(
      center,
      bloomRadius,
      Paint()
        ..shader = RadialGradient(
          colors: [
            RuneColors.brightEmerald.withOpacity(.17 * intensity),
            RuneColors.emerald.withOpacity(.075 * intensity),
            Colors.transparent,
          ],
        ).createShader(Rect.fromCircle(center: center, radius: bloomRadius)),
    );

    var frontIndex = 0;
    var backIndex = 0;
    for (var i = 0; i < _count; i++) {
      final rx = _x[i] * cy - _z[i] * sy;
      final rz = _x[i] * sy + _z[i] * cy;
      final ry = _y[i] * cp - rz * sp;
      final depth = _y[i] * sp + rz * cp;
      final perspective = _cameraDistance / (_cameraDistance - depth * .48);
      final px = center.dx + rx * perspective * radius * pulse;
      final py = center.dy - ry * perspective * radius * pulse;

      if (depth >= -.04) {
        _front[frontIndex++] = px;
        _front[frontIndex++] = py;
      } else {
        _back[backIndex++] = px;
        _back[backIndex++] = py;
      }
    }

    if (backIndex > 0) {
      canvas.drawRawPoints(
        PointMode.points,
        Float32List.sublistView(_back, 0, backIndex),
        _backPaint,
      );
    }
    if (frontIndex > 0) {
      final points = Float32List.sublistView(_front, 0, frontIndex);
      canvas.drawRawPoints(PointMode.points, points, _frontGlow);
      canvas.drawRawPoints(PointMode.points, points, _frontPaint);
    }

    // A fine, tilted light ribbon gives the orb the flowing visual signature
    // from the approved R.U.N.E. identity boards.
    final ribbon = Path()
      ..moveTo(center.dx - radius * 1.42, center.dy + radius * .28)
      ..cubicTo(
        center.dx - radius * .55,
        center.dy - radius * .68,
        center.dx + radius * .72,
        center.dy - radius * .58,
        center.dx + radius * 1.38,
        center.dy - radius * .05,
      );
    canvas.drawPath(
      ribbon,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = math.max(1, size.width * .006)
        ..shader = const LinearGradient(
          colors: [
            Color(0x00A7FFD2),
            RuneColors.mint,
            RuneColors.brightEmerald,
            RuneColors.aurum,
            Color(0x00D4AF37),
          ],
          stops: [0, .2, .58, .82, 1],
        ).createShader(Rect.fromCircle(center: center, radius: radius * 1.5))
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 1.1),
    );

    final glintAngle = elapsed * .42 + .25;
    final glint = Offset(
      center.dx + math.cos(glintAngle) * radius * 1.04,
      center.dy + math.sin(glintAngle) * radius * .42,
    );
    canvas.drawCircle(
      glint,
      size.width * .012,
      Paint()
        ..color = RuneColors.ivory.withOpacity(.9)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5),
    );
    canvas.drawCircle(
      glint,
      size.width * .004,
      Paint()..color = RuneColors.ivory,
    );
  }

  @override
  bool shouldRepaint(covariant _RuneOrbPainter oldDelegate) =>
      oldDelegate.progress != progress ||
      oldDelegate.intensity != intensity;
}
