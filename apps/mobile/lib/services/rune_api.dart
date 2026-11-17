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

class RuneApi {
  RuneApi({required this.baseUrl, this.sessionToken = ''});
  final String baseUrl;
  final String sessionToken;
  final HttpClient _client = HttpClient()..connectionTimeout = const Duration(seconds: 8);

  Uri _uri(String path) => Uri.parse(baseUrl.trim().replaceAll(RegExp(r'/+$'), '') + path);

  Future<Map<String, dynamic>> _request(String path, {Map<String, dynamic>? body}) async {
    HttpClientRequest request;
    try {
      request = body == null
          ? await _client.getUrl(_uri(path)).timeout(const Duration(seconds: 12))
          : await _client.postUrl(_uri(path)).timeout(const Duration(seconds: 12));
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      if (body != null) {
        request.headers.contentType = ContentType.json;
        request.write(jsonEncode(body));
      }
      if (sessionToken.isNotEmpty) request.headers.set('X-RUNE-Session', sessionToken);
      final response = await request.close().timeout(const Duration(seconds: 18));
      final text = await response.transform(utf8.decoder).join();
      final decoded = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
      final payload = decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw RuneApiException(payload['error']?.toString() ?? 'R.U.N.E. returned HTTP ${response.statusCode}.', statusCode: response.statusCode);
      }
      return payload;
    } on SocketException {
      throw const RuneApiException('Cannot reach the R.U.N.E. core. Check the API address and network.');
    } on TimeoutException {
      throw const RuneApiException('R.U.N.E. took too long to respond.');
    } on FormatException {
      throw const RuneApiException('The R.U.N.E. core returned an invalid response.');
    } on HandshakeException {
      throw const RuneApiException('Secure connection failed. Check the API host and TLS certificate.');
    }
  }


  Future<String> transcribeAudio(List<int> audio, {String contentType = 'audio/mp4'}) async {
    if (audio.isEmpty || audio.length > 25 * 1024 * 1024) {
      throw const RuneApiException('Voice recording must be between 1 byte and 25 MB.');
    }
    try {
      final request = await _client.postUrl(_uri('/api/voice/transcribe')).timeout(const Duration(seconds: 12));
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      request.headers.contentType = ContentType.parse(contentType);
      if (sessionToken.isNotEmpty) request.headers.set('X-RUNE-Session', sessionToken);
      request.add(audio);
      final response = await request.close().timeout(const Duration(seconds: 60));
      final text = await response.transform(utf8.decoder).join();
      final payload = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final message = payload is Map ? payload['error'] : null;
        throw RuneApiException(message?.toString() ?? 'Speech recognition failed (${response.statusCode}).',
            statusCode: response.statusCode);
      }
      return payload is Map ? payload['text']?.toString() ?? '' : '';
    } on SocketException {
      throw const RuneApiException('Cannot reach the R.U.N.E. core for transcription.');
    } on TimeoutException {
      throw const RuneApiException('Speech recognition timed out.');
    } on FormatException {
      throw const RuneApiException('Speech recognition returned invalid data.');
    }
  }

  Future<List<int>> synthesizeSpeech(String text) async {
    try {
      final request = await _client.postUrl(_uri('/api/voice/synthesize')).timeout(const Duration(seconds: 12));
      request.headers.set(HttpHeaders.acceptHeader, 'audio/mpeg');
      request.headers.contentType = ContentType.json;
      if (sessionToken.isNotEmpty) request.headers.set('X-RUNE-Session', sessionToken);
      request.write(jsonEncode({'text': text}));
      final response = await request.close().timeout(const Duration(seconds: 60));
      final bytes = await response.fold<List<int>>(<int>[], (buffer, chunk) => buffer..addAll(chunk));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final message = utf8.decode(bytes, allowMalformed: true);
        throw RuneApiException(message.isEmpty ? 'Speech synthesis failed (${response.statusCode}).' : message,
            statusCode: response.statusCode);
      }
      return bytes;
    } on SocketException {
      throw const RuneApiException('Cannot reach the R.U.N.E. core for speech synthesis.');
    } on TimeoutException {
      throw const RuneApiException('Speech synthesis timed out.');
    }
  }

  Future<bool> health() async {
    final result = await _request('/api/health');
    return result['status'] == 'online';
  }
  Future<Map<String, dynamic>> state() => _request('/api/state');
  Future<String> chat(String message) async => (await _request('/api/chat', body: {'message': message}))['response']?.toString() ?? '';
  Future<List<dynamic>> activity() async => (await _request('/api/activity'))['events'] as List<dynamic>? ?? [];
  Future<List<dynamic>> tools() async => (await _request('/api/tools'))['tools'] as List<dynamic>? ?? [];
  Future<Map<String, dynamic>> setGoal(String goal) => _request('/api/goal', body: {'goal': goal});
  Future<Map<String, dynamic>> remember(String key, String value) => _request('/api/memory', body: {'key': key, 'value': value, 'kind': 'semantic', 'salience': .8});
  Future<Map<String, dynamic>> createPlan(String goal, List<String> steps) => _request('/api/plan', body: {
    'goal': goal,
    'steps': [for (var i = 0; i < steps.length; i++) {'id': 'step-${i + 1}', 'description': steps[i]}],
  });
  void close() => _client.close(force: true);
}
