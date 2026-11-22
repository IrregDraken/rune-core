import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:rune_mobile/services/rune_api.dart';

void main() {
  final requests =
      <({String method, String path, Object? body, String? session})>[];
  late RuneApi api;

  setUp(() {
    requests.clear();
    api = RuneApi(
      baseUrl: 'https://core.example.test',
      sender: (uri,
          {required method, required body, required sessionToken}) async {
        requests.add((
          method: method,
          path: uri.path,
          body: body,
          session: sessionToken
        ));
        if (uri.path == '/api/health') {
          return const RuneApiResponse(
              statusCode: 200, body: '{"status":"online"}');
        }
        if (uri.path == '/api/chat') {
          final message = (body!['message']).toString();
          return RuneApiResponse(
              statusCode: 200,
              body: jsonEncode({'response': 'Received: $message'}));
        }
        if (uri.path == '/api/goal') {
          return const RuneApiResponse(
              statusCode: 403, body: '{"error":"privileged session required"}');
        }
        return const RuneApiResponse(
            statusCode: 404, body: '{"error":"Not found"}');
      },
    );
  });

  tearDown(() => api.close());

  test('health and chat use the documented routes and JSON payloads', () async {
    expect(await api.health(), isTrue);
    expect(await api.chat('hello'), 'Received: hello');
    expect(requests.map((request) => '${request.method} ${request.path}'), [
      'GET /api/health',
      'POST /api/chat',
    ]);
    expect(requests.last.body, {'message': 'hello'});
  });

  test('privileged errors are surfaced without claiming success', () async {
    await expectLater(
      api.setGoal('Plan a task'),
      throwsA(
        isA<RuneApiException>()
            .having((error) => error.statusCode, 'status code', 403)
            .having((error) => error.message, 'message',
                'privileged session required'),
      ),
    );
  });

  test('session header value is forwarded only when configured', () async {
    api.close();
    api = RuneApi(
      baseUrl: 'https://core.example.test',
      sessionToken: 'test-session',
      sender: (uri,
          {required method, required body, required sessionToken}) async {
        requests.add((
          method: method,
          path: uri.path,
          body: body,
          session: sessionToken
        ));
        return const RuneApiResponse(
            statusCode: 200, body: '{"status":"online"}');
      },
    );
    expect(await api.health(), isTrue);
    expect(requests.single.session, 'test-session');
  });
}
