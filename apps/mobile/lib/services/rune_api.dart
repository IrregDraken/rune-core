import 'dart:async';
import 'dart:convert';
import 'dart:io';

class RuneApiException implements Exception {
  const RuneApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;
  @override
  String toString() => message;
}

class RuneApiResponse {
  const RuneApiResponse({required this.statusCode, required this.body});
  final int statusCode;
  final String body;
}

typedef RuneApiSender = Future<RuneApiResponse> Function(
  Uri uri, {
  required String method,
  required Map<String, dynamic>? body,
  required String? sessionToken,
});

class RuneApi {
  RuneApi(
      {required this.baseUrl, this.sessionToken = '', RuneApiSender? sender})
      : _sender = sender;
  final String baseUrl;
  final String sessionToken;
  final RuneApiSender? _sender;
  final HttpClient _client = HttpClient()
    ..connectionTimeout = const Duration(seconds: 8);

  Uri _uri(String path) =>
      Uri.parse(baseUrl.trim().replaceAll(RegExp(r'/+$'), '') + path);

  Future<Map<String, dynamic>> _request(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    try {
      final uri = _uri(path);
      final method = body == null ? 'GET' : 'POST';
      late int statusCode;
      late String text;
      if (_sender != null) {
        final response = await _sender(
          uri,
          method: method,
          body: body,
          sessionToken: sessionToken.isEmpty ? null : sessionToken,
        ).timeout(const Duration(seconds: 18));
        statusCode = response.statusCode;
        text = response.body;
      } else {
        final request = method == 'GET'
            ? await _client.getUrl(uri).timeout(const Duration(seconds: 12))
            : await _client.postUrl(uri).timeout(const Duration(seconds: 12));
        request.headers.set(HttpHeaders.acceptHeader, 'application/json');
        if (body != null) {
          request.headers.contentType = ContentType.json;
          request.write(jsonEncode(body));
        }
        if (sessionToken.isNotEmpty) {
          request.headers.set('X-RUNE-Session', sessionToken);
        }
        final response = await request.close().timeout(
              const Duration(seconds: 18),
            );
        statusCode = response.statusCode;
        text = await response.transform(utf8.decoder).join();
      }
      final decoded = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
      final payload =
          decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
      if (statusCode < 200 || statusCode >= 300) {
        throw RuneApiException(
          payload['error']?.toString() ?? 'R.U.N.E. returned HTTP $statusCode.',
          statusCode: statusCode,
        );
      }
      return payload;
    } on SocketException {
      throw const RuneApiException(
        'Cannot reach the R.U.N.E. core. Check the API address and network.',
      );
    } on TimeoutException {
      throw const RuneApiException('R.U.N.E. took too long to respond.');
    } on FormatException {
      throw const RuneApiException(
        'The R.U.N.E. core returned an invalid response.',
      );
    } on HandshakeException {
      throw const RuneApiException(
        'Secure connection failed. Check the API host and TLS certificate.',
      );
    }
  }

  Future<bool> health() async {
    final result = await _request('/api/health');
    return result['status'] == 'online';
  }

  Future<Map<String, dynamic>> state() => _request('/api/state');
  Future<String> chat(String message) async =>
      (await _request(
        '/api/chat',
        body: {'message': message},
      ))['response']
          ?.toString() ??
      '';
  Future<List<dynamic>> activity() async =>
      (await _request('/api/activity'))['events'] as List<dynamic>? ?? [];
  Future<List<dynamic>> tools() async =>
      (await _request('/api/tools'))['tools'] as List<dynamic>? ?? [];
  Future<Map<String, dynamic>> setGoal(String goal) =>
      _request('/api/goal', body: {'goal': goal});
  Future<Map<String, dynamic>> remember(String key, String value) => _request(
        '/api/memory',
        body: {'key': key, 'value': value, 'kind': 'semantic', 'salience': .8},
      );
  Future<Map<String, dynamic>> createPlan(String goal, List<String> steps) =>
      _request(
        '/api/plan',
        body: {
          'goal': goal,
          'steps': [
            for (var i = 0; i < steps.length; i++)
              {'id': 'step-${i + 1}', 'description': steps[i]},
          ],
        },
      );
  void close() => _client.close(force: true);
}
