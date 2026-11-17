import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../theme/rune_colors.dart';
import '../screens/onboarding_page.dart';
import '../screens/rune_pages.dart';
import '../screens/rune_experience.dart';
import '../services/rune_api.dart';

class RuneApp extends StatefulWidget {
  const RuneApp({super.key});

  @override
  State<RuneApp> createState() => _RuneAppState();
}

class _RuneAppState extends State<RuneApp> {
  bool ready = false;
  bool onboarded = false;
  String owner = 'Owner';
  String apiUrl = 'https://rune-core-production-e1cb.up.railway.app';
  String sessionToken = '';
  final secureStorage = const FlutterSecureStorage();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final preferences = await SharedPreferences.getInstance();
      owner = preferences.getString('rune.owner') ?? 'Owner';
      apiUrl = preferences.getString('rune.api') ?? apiUrl;
      onboarded = preferences.getBool('rune.onboarded') ?? false;
    } catch (_) {
      // Keep first-run defaults if local preferences are temporarily unavailable.
    }
    if (mounted) setState(() => ready = true);

    // Secure storage remains non-blocking so a platform keystore issue cannot
    // strand the user on the launch screen.
    try {
      sessionToken =
          await secureStorage.read(key: 'rune.local_core_session') ?? '';
      if (mounted) setState(() {});
    } catch (_) {
      sessionToken = '';
    }
  }

  Future<void> _complete(String name, String url) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString('rune.owner', name);
    await preferences.setString('rune.api', url);
    await preferences.setBool('rune.onboarded', true);
    if (!mounted) return;
    setState(() {
      owner = name;
      apiUrl = url;
      onboarded = true;
    });
  }

  Future<void> _updateApi(String url) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString('rune.api', url);
    if (mounted) setState(() => apiUrl = url);
  }

  Future<void> _updateSessionToken(String token) async {
    await secureStorage.write(key: 'rune.local_core_session', value: token);
    if (mounted) setState(() => sessionToken = token);
  }

  @override
  Widget build(BuildContext context) {
    final base = ThemeData(
      brightness: Brightness.dark,
      useMaterial3: true,
      scaffoldBackgroundColor: RuneColors.obsidian,
      colorScheme: const ColorScheme.dark(
        primary: RuneColors.brightEmerald,
        secondary: RuneColors.aurum,
        surface: RuneColors.carbon,
        onSurface: RuneColors.ivory,
      ),
    );
    final sora = GoogleFonts.soraTextTheme(base.textTheme).apply(
      bodyColor: RuneColors.ivory,
      displayColor: RuneColors.ivory,
    );
    final textTheme = sora.copyWith(
      bodyLarge: GoogleFonts.inter(
        textStyle: sora.bodyLarge,
        color: RuneColors.ivory,
      ),
      bodyMedium: GoogleFonts.inter(
        textStyle: sora.bodyMedium,
        color: RuneColors.ivory,
      ),
      bodySmall: GoogleFonts.inter(
        textStyle: sora.bodySmall,
        color: RuneColors.muted,
      ),
      labelLarge: GoogleFonts.inter(
        textStyle: sora.labelLarge,
        fontWeight: FontWeight.w600,
      ),
    );

    final theme = base.copyWith(
      textTheme: textTheme,
      scaffoldBackgroundColor: RuneColors.obsidian,
      appBarTheme: const AppBarTheme(
        backgroundColor: RuneColors.obsidian,
        foregroundColor: RuneColors.ivory,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
      ),
      dividerColor: RuneColors.border,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: RuneColors.carbon,
        hintStyle: const TextStyle(color: RuneColors.muted),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 17, vertical: 17),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: RuneColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: RuneColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(
            color: RuneColors.brightEmerald,
            width: 1.3,
          ),
        ),
      ),
      cardTheme: CardThemeData(
        color: RuneColors.carbon,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: RuneColors.border),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: 72,
        backgroundColor: const Color(0xF20D130F),
        indicatorColor: RuneColors.emerald.withValues(alpha: .18),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return TextStyle(
            color: selected ? RuneColors.brightEmerald : RuneColors.muted,
            fontSize: 10,
            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            letterSpacing: .2,
          );
        }),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: RuneColors.brightEmerald,
          foregroundColor: RuneColors.obsidian,
          disabledBackgroundColor: RuneColors.pine,
          disabledForegroundColor: RuneColors.muted,
          minimumSize: const Size(0, 52),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: const TextStyle(
            fontWeight: FontWeight.w700,
            letterSpacing: .2,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: RuneColors.ivory,
          side: const BorderSide(color: RuneColors.border),
          minimumSize: const Size(0, 50),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
      ),
    );

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'R.U.N.E.',
      theme: theme,
      home: !ready
          ? const _Loading()
          : !onboarded
              ? OnboardingPage(onComplete: _complete)
              : RuneExperienceShell(
                  owner: owner,
                  apiUrl: apiUrl,
                  sessionToken: sessionToken,
                  onApiChanged: _updateApi,
                  onSessionTokenChanged: _updateSessionToken,
                ),
    );
  }
}

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) => const Scaffold(
        body: Center(
          child: CircularProgressIndicator(color: RuneColors.brightEmerald),
        ),
      );
}

class RuneShell extends StatefulWidget {
  const RuneShell({
    super.key,
    required this.owner,
    required this.apiUrl,
    required this.sessionToken,
    required this.onApiChanged,
    required this.onSessionTokenChanged,
  });

  final String owner;
  final String apiUrl;
  final String sessionToken;
  final Future<void> Function(String) onApiChanged;
  final Future<void> Function(String) onSessionTokenChanged;

  @override
  State<RuneShell> createState() => _RuneShellState();
}

class _RuneShellState extends State<RuneShell> {
  // Assistant is the first screen after authentication; Home remains available.
  int index = 1;
  late RuneApi api;

  @override
  void initState() {
    super.initState();
    api = RuneApi(baseUrl: widget.apiUrl, sessionToken: widget.sessionToken);
  }

  @override
  void didUpdateWidget(covariant RuneShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.apiUrl != widget.apiUrl ||
        oldWidget.sessionToken != widget.sessionToken) {
      api.close();
      api = RuneApi(baseUrl: widget.apiUrl, sessionToken: widget.sessionToken);
    }
  }

  @override
  void dispose() {
    api.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomePage(
        owner: widget.owner,
        api: api,
        apiUrl: widget.apiUrl,
        onApiChanged: widget.onApiChanged,
        onSessionTokenChanged: widget.onSessionTokenChanged,
        onNavigate: (value) => setState(() => index = value),
      ),
      AssistantPage(api: api),
      WorkPage(api: api),
      ExplorePage(api: api),
    ];

    return Scaffold(
      extendBody: true,
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -.88),
            radius: 1.15,
            colors: [Color(0xFF10291D), RuneColors.obsidian],
            stops: [0, .72],
          ),
        ),
        child: SafeArea(
          bottom: false,
          child: IndexedStack(index: index, children: pages),
        ),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        minimum: const EdgeInsets.fromLTRB(16, 0, 16, 10),
        child: Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: const Color(0xF20D130F),
            borderRadius: BorderRadius.circular(25),
            border: Border.all(color: RuneColors.emerald.withOpacity(.20)),
            boxShadow: [
              BoxShadow(color: Colors.black.withOpacity(.28), blurRadius: 24, offset: const Offset(0, 8)),
              BoxShadow(color: RuneColors.emerald.withOpacity(.045), blurRadius: 22, spreadRadius: 1),
            ],
          ),
          child: Row(
            children: [
              _RuneNavItem(icon: Icons.grid_view_rounded, label: 'Home', selected: index == 0, onTap: () => setState(() => index = 0)),
              _RuneNavItem(icon: Icons.auto_awesome_rounded, label: 'Assistant', selected: index == 1, onTap: () => setState(() => index = 1)),
              _RuneNavItem(icon: Icons.work_outline_rounded, label: 'Work', selected: index == 2, onTap: () => setState(() => index = 2)),
              _RuneNavItem(icon: Icons.hub_outlined, label: 'Explore', selected: index == 3, onTap: () => setState(() => index = 3)),
            ],
          ),
        ),
      ),
    );
  }
}

class _RuneNavItem extends StatelessWidget {
  const _RuneNavItem({required this.icon, required this.label, required this.selected, required this.onTap});
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Expanded(
    child: Semantics(
      button: true,
      selected: selected,
      label: label,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(19),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: selected ? RuneColors.emerald.withOpacity(.15) : Colors.transparent,
            borderRadius: BorderRadius.circular(19),
            border: Border.all(color: selected ? RuneColors.emerald.withOpacity(.22) : Colors.transparent),
          ),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, size: 19, color: selected ? RuneColors.brightEmerald : RuneColors.muted),
            const SizedBox(height: 4),
            Text(label, style: TextStyle(
              fontSize: 9,
              letterSpacing: .1,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              color: selected ? RuneColors.mint : RuneColors.muted,
            )),
          ]),
        ),
      ),
    ),
  );
}
