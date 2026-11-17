import 'package:flutter/services.dart';

class RuneDeviceAgent {
  static const MethodChannel _channel = MethodChannel('rune/device');

  Future<Map<String, dynamic>> capabilities() async {
    final value = await _channel.invokeMapMethod<String, dynamic>('capabilities');
    return value ?? <String, dynamic>{};
  }

  Future<List<Map<String, String>>> installedApps() async {
    final values = await _channel.invokeListMethod<dynamic>('installedApps') ?? [];
    return values.whereType<Map>().map((item) => item.map(
      (key, value) => MapEntry(key.toString(), value.toString()),
    )).toList();
  }

  Future<bool> launchApp(String packageName) async =>
      await _channel.invokeMethod<bool>('launchApp', {'packageName': packageName}) ?? false;

  Future<void> openAccessibilitySettings() =>
      _channel.invokeMethod<void>('openAccessibilitySettings');

  Future<Map<String, dynamic>> observeUi() async {
    final value = await _channel.invokeMapMethod<String, dynamic>('observeUi');
    return value ?? <String, dynamic>{'available': false};
  }

  Future<bool> tap(double x, double y) async =>
      await _channel.invokeMethod<bool>('tap', {'x': x, 'y': y}) ?? false;

  Future<bool> scroll(String direction) async =>
      await _channel.invokeMethod<bool>('scroll', {'direction': direction}) ?? false;

  Future<bool> typeText(String text) async =>
      await _channel.invokeMethod<bool>('typeText', {'text': text}) ?? false;
}
