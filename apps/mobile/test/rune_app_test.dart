import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:rune_mobile/app/rune_app.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('first launch opens onboarding', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const RuneApp());
    await tester.pumpAndSettle();
    expect(find.text('Intelligence that\nstays with you.'), findsOneWidget);
    expect(find.text('CONTINUE'), findsOneWidget);
  });
  testWidgets('returning launch opens the command center', (tester) async {
    SharedPreferences.setMockInitialValues({
      'rune.onboarded': true,
      'rune.owner': 'Draken',
      'rune.api': 'http://127.0.0.1:8765',
    });
    await tester.pumpWidget(const RuneApp());
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('R.U.N.E.'), findsOneWidget);
    expect(find.text('Your command center is ready.'), findsOneWidget);
    expect(find.text('Profile'), findsOneWidget);
    await tester.tap(find.text('Profile').last);
    await tester.pump();
    expect(find.text('IDENTITY · PREFERENCES · ACCESS'), findsOneWidget);
    expect(find.text('Security & access'), findsOneWidget);
  });
}
