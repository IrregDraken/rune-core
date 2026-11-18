import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class RuneRemoteException implements Exception {
  const RuneRemoteException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;
  @override
  String toString() => message;
}

class RuneRemoteApi {
  RuneRemoteApi({
    required this.backendUrl,
    required this.supabaseUrl,
    required this.publishableKey,
  }) : _storage = const FlutterSecureStorage();

  final String backendUrl;
  final String supabaseUrl;
  final String publishableKey;
  final FlutterSecureStorage _storage;
  final HttpClient _http = HttpClient()
    ..connectionTimeout = const Duration(seconds: 8);

  String get _backend => backendUrl.trim().replaceAll(RegExp(r'/+$'), '');
  String get _auth => supabaseUrl.trim().replaceAll(RegExp(r'/+$'), '');

  bool _secureOrLocal(String value) {
    final uri = Uri.tryParse(value);
    if (uri == null) return false;
    return uri.scheme == 'https' ||
        uri.host == 'localhost' ||
        uri.host == '127.0.0.1';
  }

  void _requireSecureEndpoint(String value, String label) {
    if (!_secureOrLocal(value)) {
      throw RuneRemoteException(
        '$label must use HTTPS except for localhost development.',
      );
    }
  }

  Future<Map<String, dynamic>> _send(
    String method,
    String url, {
    Map<String, String>? headers,
    Map<String, dynamic>? body,
  }) async {
    try {
      final request = await _http
          .openUrl(method, Uri.parse(url))
          .timeout(const Duration(seconds: 12));
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      headers?.forEach((name, value) => request.headers.set(name, value));
      if (body != null) {
        request.headers.contentType = ContentType.json;
        request.write(jsonEncode(body));
      }
      final response =
          await request.close().timeout(const Duration(seconds: 20));
      final text = await response.transform(utf8.decoder).join();
      final decoded =
          text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
      final payload = decoded is Map<String, dynamic>
          ? decoded
          : <String, dynamic>{};
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final message = payload['msg'] ??
            payload['message'] ??
            payload['detail'] ??
            'Remote service returned HTTP ${response.statusCode}.';
        throw RuneRemoteException(
          message.toString(),
          statusCode: response.statusCode,
        );
      }
      return payload;
    } on SocketException {
      throw const RuneRemoteException('Remote service is unreachable.');
    } on TimeoutException {
      throw const RuneRemoteException('Remote service timed out.');
    } on FormatException {
      throw const RuneRemoteException('Remote service returned invalid data.');
    } on HandshakeException {
      throw const RuneRemoteException(
        'Secure connection failed. Check HTTPS configuration.',
      );
    }
  }

  Future<List<dynamic>> _sendList(
    String method,
    String url, {
    Map<String, String>? headers,
  }) async {
    try {
      final request = await _http
          .openUrl(method, Uri.parse(url))
          .timeout(const Duration(seconds: 12));
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      headers?.forEach((name, value) => request.headers.set(name, value));
      final response =
          await request.close().timeout(const Duration(seconds: 20));
      final text = await response.transform(utf8.decoder).join();
      final decoded = text.isEmpty ? <dynamic>[] : jsonDecode(text);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final payload =
            decoded is Map ? decoded : <String, dynamic>{};
        throw RuneRemoteException(
          (payload['detail'] ??
                  payload['message'] ??
                  'Remote service returned HTTP ${response.statusCode}.')
              .toString(),
          statusCode: response.statusCode,
        );
      }
      return decoded is List ? decoded : <dynamic>[];
    } on SocketException {
      throw const RuneRemoteException('Remote service is unreachable.');
    } on TimeoutException {
      throw const RuneRemoteException('Remote service timed out.');
    } on FormatException {
      throw const RuneRemoteException('Remote service returned invalid data.');
    } on HandshakeException {
      throw const RuneRemoteException(
        'Secure connection failed. Check HTTPS configuration.',
      );
    }
  }

  Future<void> signIn(String email, String password) async {
    _requireSecureEndpoint(_auth, 'Supabase URL');
    final result = await _send(
      'POST',
      '$_auth/auth/v1/token?grant_type=password',
      headers: {'apikey': publishableKey},
      body: {'email': email.trim(), 'password': password},
    );
    final access = result['access_token']?.toString();
    final refresh = result['refresh_token']?.toString();
    if (access == null || refresh == null) {
      throw const RuneRemoteException(
        'Identity provider did not issue a valid session.',
      );
    }
    await _storage.write(key: 'rune.owner_access_token', value: access);
    await _storage.write(key: 'rune.owner_refresh_token', value: refresh);
    final expiresIn = (result['expires_in'] as num?)?.toInt() ?? 3600;
    await _storage.write(
      key: 'rune.owner_expires_at',
      value: DateTime.now()
          .add(Duration(seconds: expiresIn))
          .millisecondsSinceEpoch
          .toString(),
    );
  }

  Future<String?> _ownerToken() async {
    var token = await _storage.read(key: 'rune.owner_access_token');
    final refresh = await _storage.read(key: 'rune.owner_refresh_token');
    if (token == null) return null;
    final expiry = int.tryParse(
          await _storage.read(key: 'rune.owner_expires_at') ?? '0',
        ) ??
        0;
    final refreshDue =
        DateTime.now().add(const Duration(seconds: 60)).millisecondsSinceEpoch;
    if (refresh != null && expiry <= refreshDue) {
      try {
        final result = await _send(
          'POST',
          '$_auth/auth/v1/token?grant_type=refresh_token',
          headers: {'apikey': publishableKey},
          body: {'refresh_token': refresh},
        );
        token = result['access_token']?.toString() ?? token;
        await _storage.write(key: 'rune.owner_access_token', value: token);
        final expiresIn = (result['expires_in'] as num?)?.toInt() ?? 3600;
        await _storage.write(
          key: 'rune.owner_expires_at',
          value: DateTime.now()
              .add(Duration(seconds: expiresIn))
              .millisecondsSinceEpoch
              .toString(),
        );
        final next = result['refresh_token']?.toString();
        if (next != null) {
          await _storage.write(key: 'rune.owner_refresh_token', value: next);
        }
      } on RuneRemoteException catch (error) {
        if (error.statusCode == 400 || error.statusCode == 401) {
          await signOut();
          rethrow;
        }
      }
    }
    return token;
  }

  Future<Map<String, String>> _ownerHeaders() async {
    final token = await _ownerToken();
    if (token == null) {
      throw const RuneRemoteException(
        'Sign in to your RUNE account first.',
      );
    }
    return {'Authorization': 'Bearer $token'};
  }

  Future<Map<String, dynamic>> registerDevice({
    required String name,
    required List<String> capabilities,
    required String appVersion,
  }) async {
    _requireSecureEndpoint(_backend, 'RUNE backend URL');
    final result = await _send(
      'POST',
      '$_backend/v1/devices/register',
      headers: await _ownerHeaders(),
      body: {
        'device_name': name,
        'platform': 'android',
        'app_version': appVersion,
        'capabilities': capabilities,
      },
    );
    final device = result['device'] as Map<String, dynamic>;
    final deviceToken = result['device_token']?.toString();
    final deviceId = device['id']?.toString();
    if (deviceToken == null || deviceId == null) {
      throw const RuneRemoteException(
        'Backend did not return device enrollment credentials.',
      );
    }
    await _storage.write(key: 'rune.device_id', value: deviceId);
    await _storage.write(key: 'rune.device_token', value: deviceToken);
    return device;
  }

  Future<Map<String, dynamic>?> deviceCredentials() async {
    final id = await _storage.read(key: 'rune.device_id');
    final token = await _storage.read(key: 'rune.device_token');
    if (id == null || token == null) return null;
    return {'id': id, 'token': token};
  }

  Future<Map<String, dynamic>> heartbeat(List<String> capabilities) async {
    final credentials = await deviceCredentials();
    if (credentials == null) {
      throw const RuneRemoteException('This phone has not been enrolled.');
    }
    return _send(
      'POST',
      '$_backend/v1/devices/${credentials['id']}/heartbeat',
      headers: {
        'X-RUNE-Device-Token': credentials['token'] as String,
      },
      body: {
        'status': 'online',
        'capabilities': capabilities,
        'app_version': '0.2.0',
      },
    );
  }

  Future<Map<String, dynamic>?> nextTask() async {
    final credentials = await deviceCredentials();
    if (credentials == null) {
      throw const RuneRemoteException('This phone has not been enrolled.');
    }
    final result = await _send(
      'GET',
      '$_backend/v1/devices/${credentials['id']}/tasks/next',
      headers: {
        'X-RUNE-Device-Token': credentials['token'] as String,
      },
    );
    return result['task'] as Map<String, dynamic>?;
  }

  Future<void> submitResult(
    String taskId, {
    required String status,
    Map<String, dynamic> output = const {},
    Map<String, dynamic> evidence = const {},
    String? errorCode,
  }) async {
    final credentials = await deviceCredentials();
    if (credentials == null) {
      throw const RuneRemoteException('This phone has not been enrolled.');
    }
    await _send(
      'POST',
      '$_backend/v1/devices/${credentials['id']}/tasks/$taskId/result',
      headers: {
        'X-RUNE-Device-Token': credentials['token'] as String,
      },
      body: {
        'status': status,
        'output': output,
        'evidence': evidence,
        'error_code': errorCode,
      },
    );
  }

  Future<List<dynamic>> devices() async => _sendList(
        'GET',
        '$_backend/v1/devices',
        headers: await _ownerHeaders(),
      );

  Future<List<dynamic>> pendingTasks() async => _sendList(
        'GET',
        '$_backend/v1/tasks?status=awaiting_approval',
        headers: await _ownerHeaders(),
      );

  Future<Map<String, dynamic>> approveTask(String taskId) async => _send(
        'POST',
        '$_backend/v1/tasks/$taskId/approve',
        headers: await _ownerHeaders(),
        body: {},
      );

  Future<Map<String, dynamic>> cancelTask(String taskId) async => _send(
        'POST',
        '$_backend/v1/tasks/$taskId/cancel',
        headers: await _ownerHeaders(),
        body: {},
      );

  Future<void> revokeThisDevice() async {
    final credentials = await deviceCredentials();
    if (credentials == null) return;
    await _send(
      'DELETE',
      '$_backend/v1/devices/${credentials['id']}',
      headers: await _ownerHeaders(),
    );
    await clearDeviceCredentials();
  }

  Future<void> clearDeviceCredentials() async {
    await _storage.delete(key: 'rune.device_id');
    await _storage.delete(key: 'rune.device_token');
  }

  /// Restores a previously authenticated owner session and verifies it with
  /// the control plane. Returns false only when no local owner session exists.
  /// Invalid/expired credentials are cleared by _ownerToken; network failures
  /// remain visible to the caller and never silently enroll a new device.
  Future<Map<String, dynamic>?> restoreOwnerSession() async {
    final token = await _ownerToken();
    if (token == null) return null;
    _requireSecureEndpoint(_backend, 'RUNE backend URL');
    return _send('GET', '$_backend/v1/me', headers: {'Authorization': 'Bearer $token'});
  }

  Future<void> signOut() async {
    await _storage.delete(key: 'rune.owner_access_token');
    await _storage.delete(key: 'rune.owner_refresh_token');
    await _storage.delete(key: 'rune.owner_expires_at');
    await clearDeviceCredentials();
  }

  void close() => _http.close(force: true);
}
