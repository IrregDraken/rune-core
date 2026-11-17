import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:rune_mobile/app/rune_app.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<void> pumpApp(WidgetTester tester) async {
    await tester.pumpWidget(const RuneApp());
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets('first launch opens onboarding', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await pumpApp(tester);
    expect(find.text('Intelligence that\nstays with you.'), findsOneWidget);
    expect(find.text('CONTINUE'), findsOneWidget);
  });

  testWidgets('returning launch opens the command center', (tester) async {
    SharedPreferences.setMockInitialValues({
      'rune.onboarded': true,
      'rune.owner': 'Draken',
      'rune.api': 'http://127.0.0.1:8765',
    });
    await pumpApp(tester);
    expect(find.text('R.U.N.E.'), findsOneWidget);
    expect(find.text('SYSTEM SNAPSHOT'), findsOneWidget);
  });
}
