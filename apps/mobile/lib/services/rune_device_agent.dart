import 'dart:typed_data';

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

  Future<void> openAccessibilitySettings() async {
    await _channel.invokeMethod<bool>('openAccessibilitySettings');
  }

  Future<bool> requestNotificationPermission() async =>
      await _channel.invokeMethod<bool>('requestNotificationPermission') ?? false;

  Future<bool> startBackgroundOperator({
    required String backendUrl,
    required String deviceId,
    required String deviceToken,
  }) async =>
      await _channel.invokeMethod<bool>('startBackgroundOperator', {
        'backendUrl': backendUrl,
        'deviceId': deviceId,
        'deviceToken': deviceToken,
      }) ??
      false;

  Future<void> stopBackgroundOperator() async {
    await _channel.invokeMethod<bool>('stopBackgroundOperator');
  }


  Future<bool> hasMicrophonePermission() async =>
      await _channel.invokeMethod<bool>('hasMicrophonePermission') ?? false;

  Future<bool> requestMicrophonePermission() async =>
      await _channel.invokeMethod<bool>('requestMicrophonePermission') ?? false;

  Future<bool> startVoiceRecording() async =>
      await _channel.invokeMethod<bool>('startVoiceRecording') ?? false;

  Future<String?> stopVoiceRecording() async =>
      _channel.invokeMethod<String>('stopVoiceRecording');

  Future<bool> playAudio(List<int> audio) async =>
      await _channel.invokeMethod<bool>('playAudio', {'audio': Uint8List.fromList(audio)}) ?? false;

  Future<void> stopAudio() async {
    await _channel.invokeMethod<bool>('stopAudio');
  }

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
