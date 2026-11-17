import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

void main() => runApp(const RuneApp());

const obsidian = Color(0xFF0A0D0B);
const carbon = Color(0xFF111713);
const pine = Color(0xFF0F2D1F);
const emerald = Color(0xFF00C16A);
const brightEmerald = Color(0xFF00E68A);
const aurum = Color(0xFFD4AF37);
const ivory = Color(0xFFF5F7F6);
const muted = Color(0xFF9AA8A0);

class RuneApp extends StatelessWidget {
  const RuneApp({super.key});

  @override
  Widget build(BuildContext context) {
    final base = ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: obsidian,
      colorScheme: const ColorScheme.dark(
        primary: emerald, secondary: aurum, surface: carbon,
        onPrimary: obsidian, onSurface: ivory,
      ),
      textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme).apply(
        bodyColor: ivory, displayColor: ivory,
      ),
      useMaterial3: true,
    );
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'R.U.N.E.',
      theme: base.copyWith(
        textTheme: base.textTheme.copyWith(
          headlineMedium: GoogleFonts.sora(fontSize: 27, fontWeight: FontWeight.w600, color: ivory),
          titleLarge: GoogleFonts.sora(fontSize: 18, fontWeight: FontWeight.w600, color: ivory),
        ),
      ),
      home: const RuneShell(),
    );
  }
}

class RuneShell extends StatefulWidget {
  const RuneShell({super.key});
  @override
  State<RuneShell> createState() => _RuneShellState();
}

class _RuneShellState extends State<RuneShell> {
  int index = 0;
  final pages = const [HomePage(), AssistantPage(), WorkPage(), ExplorePage()];
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(child: IndexedStack(index: index, children: pages)),
      bottomNavigationBar: NavigationBar(
        height: 72,
        backgroundColor: const Color(0xF20D120F),
        indicatorColor: emerald.withOpacity(.15),
        selectedIndex: index,
        onDestinationSelected: (value) => setState(() => index = value),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.grid_view_rounded), selectedIcon: Icon(Icons.grid_view_rounded, color: brightEmerald), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.forum_outlined), selectedIcon: Icon(Icons.forum_rounded, color: brightEmerald), label: 'Assistant'),
          NavigationDestination(icon: Icon(Icons.work_outline_rounded), selectedIcon: Icon(Icons.work_rounded, color: brightEmerald), label: 'Work'),
          NavigationDestination(icon: Icon(Icons.hub_outlined), selectedIcon: Icon(Icons.hub_rounded, color: brightEmerald), label: 'Explore'),
        ],
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String orbState = 'ONLINE';
  @override
  Widget build(BuildContext context) {
    return CustomScrollView(
      physics: const BouncingScrollPhysics(),
      slivers: [
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(22, 18, 22, 28),
          sliver: SliverList(delegate: SliverChildListDelegate([
            Row(children: [
              const RuneGlyph(size: 34),
              const SizedBox(width: 10),
              Text('R.U.N.E.', style: GoogleFonts.sora(fontSize: 17, fontWeight: FontWeight.w600, letterSpacing: 3)),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
                decoration: BoxDecoration(color: pine.withOpacity(.55), borderRadius: BorderRadius.circular(30), border: Border.all(color: emerald.withOpacity(.22))),
                child: const Row(children: [Icon(Icons.circle, size: 7, color: brightEmerald), SizedBox(width: 7), Text('SYSTEM ONLINE', style: TextStyle(fontSize: 9, letterSpacing: 1.1, color: muted))]),
              ),
              const SizedBox(width: 12),
              const CircleAvatar(radius: 17, backgroundColor: pine, child: Icon(Icons.person_outline, size: 18, color: ivory)),
            ]),
            const SizedBox(height: 28),
            Text('TUESDAY, 17 NOVEMBER', style: TextStyle(color: muted, fontSize: 10, letterSpacing: 1.8)),
            const SizedBox(height: 7),
            Text('Good afternoon.', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 3),
            const Text('Your command center is ready.', style: TextStyle(color: muted, fontSize: 13)),
            const SizedBox(height: 6),
            Center(
              child: GestureDetector(
                onTap: () => setState(() => orbState = orbState == 'LISTENING' ? 'ONLINE' : 'LISTENING'),
                child: Column(children: [
                  RuneOrb(state: orbState),
                  Text(orbState == 'LISTENING' ? 'LISTENING' : 'READY WHEN YOU ARE',
                    style: const TextStyle(fontSize: 9, color: Color(0xFFB8DCC9), letterSpacing: 2.1, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 5),
                  const Text('Tap the orb to start a voice session', style: TextStyle(fontSize: 11, color: muted)),
                ]),
              ),
            ),
            const SizedBox(height: 25),
            Container(
              padding: const EdgeInsets.fromLTRB(15, 13, 12, 13),
              decoration: BoxDecoration(color: carbon, borderRadius: BorderRadius.circular(17), border: Border.all(color: Colors.white.withOpacity(.07))),
              child: Row(children: [
                const Icon(Icons.auto_awesome, color: brightEmerald, size: 18),
                const SizedBox(width: 10),
                const Expanded(child: Text('Ask R.U.N.E anything...', style: TextStyle(color: muted, fontSize: 13))),
                Container(width: 34, height: 34, decoration: BoxDecoration(color: pine, borderRadius: BorderRadius.circular(11)), child: const Icon(Icons.mic_none_rounded, color: brightEmerald, size: 18)),
              ]),
            ),
            const SizedBox(height: 24),
            const SectionHeading(title: 'QUICK ACTIONS', trailing: 'CUSTOMIZE'),
            const SizedBox(height: 12),
            Row(children: const [
              Expanded(child: QuickAction(icon: Icons.route_rounded, title: 'Plan', subtitle: 'Think ahead')),
              SizedBox(width: 9),
              Expanded(child: QuickAction(icon: Icons.bolt_rounded, title: 'Execute', subtitle: 'Get it done')),
              SizedBox(width: 9),
              Expanded(child: QuickAction(icon: Icons.account_tree_outlined, title: 'Automate', subtitle: 'Build a flow')),
              SizedBox(width: 9),
              Expanded(child: QuickAction(icon: Icons.add_link_rounded, title: 'Connect', subtitle: 'Add tools')),
            ]),
            const SizedBox(height: 26),
            const SectionHeading(title: 'TODAY', trailing: 'VIEW ALL'),
            const SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(color: carbon, borderRadius: BorderRadius.circular(18), border: Border.all(color: Colors.white.withOpacity(.06))),
              child: Column(children: const [
                TaskRow(icon: Icons.code_rounded, title: 'Review Rune mobile foundation', meta: 'Development · Due today', tag: 'IN PROGRESS'),
                Divider(height: 1, color: Color(0x1FFFFFFF), indent: 16, endIndent: 16),
                TaskRow(icon: Icons.layers_outlined, title: 'Define core app screens', meta: 'Product · Planned', tag: 'NEXT'),
                Divider(height: 1, color: Color(0x1FFFFFFF), indent: 16, endIndent: 16),
                TaskRow(icon: Icons.shield_outlined, title: 'Review security boundaries', meta: 'System · Planned', tag: 'NEXT'),
              ]),
            ),
            const SizedBox(height: 24),
            const SectionHeading(title: 'SYSTEM STATUS'),
            const SizedBox(height: 12),
            Row(children: const [
              Expanded(child: StatusTile(label: 'CORE', value: 'Connected', icon: Icons.memory_rounded)),
              SizedBox(width: 10),
              Expanded(child: StatusTile(label: 'MEMORY', value: 'Available', icon: Icons.database_outlined)),
            ]),
          ])),
        ),
      ],
    );
  }
}

class RuneOrb extends StatefulWidget {
  final String state;
  const RuneOrb({super.key, required this.state});
  @override
  State<RuneOrb> createState() => _RuneOrbState();
}
class _RuneOrbState extends State<RuneOrb> with SingleTickerProviderStateMixin {
  late final AnimationController controller = AnimationController(vsync: this, duration: const Duration(seconds: 16))..repeat();
  @override
  void dispose() { controller.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (_, __) => SizedBox(
        width: 280, height: 270,
        child: CustomPaint(painter: OrbPainter(controller.value, widget.state)),
      ),
    );
  }
}

class OrbPainter extends CustomPainter {
  final double t; final String state;
  OrbPainter(this.t, this.state);
  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width/2, size.height/2);
    final r = 100.0;
    final glow = Paint()..shader = RadialGradient(colors: [emerald.withOpacity(.18), pine.withOpacity(.13), Colors.transparent]).createShader(Rect.fromCircle(center:c, radius:132));
    canvas.drawCircle(c, 132, glow);
    final sphere = Paint()..shader = RadialGradient(colors: [const Color(0xFF173A29).withOpacity(.52), const Color(0xFF07100B).withOpacity(.92), const Color(0xFF020604)], stops: const [0,.55,1]).createShader(Rect.fromCircle(center:c, radius:r));
    canvas.drawCircle(c, r, sphere);
    final rim = Paint()..style=PaintingStyle.stroke..strokeWidth=1.4..shader=const SweepGradient(colors:[Color(0xFFB8FFE0),Color(0xFF00C16A),Color(0xFFD4AF37),Color(0xFF00E68A),Color(0xFFB8FFE0)]).createShader(Rect.fromCircle(center:c,radius:r));
    canvas.drawCircle(c, r, rim);
    for (int i=0;i<3;i++) {
      final p=Paint()..style=PaintingStyle.stroke..strokeWidth=i==0?1.5:.7..color=(i==1?aurum:brightEmerald).withOpacity(i==0?.8:.35);
      canvas.save(); canvas.translate(c.dx,c.dy); canvas.rotate(t*math.pi*2*(i.isEven?1:-.7)+i);
      canvas.drawOval(Rect.fromCenter(center:Offset.zero,width:r*2.2-i*13,height:r*.48+i*10),p); canvas.restore();
    }
    final runePaint=Paint()..style=PaintingStyle.stroke..strokeWidth=5..strokeCap=StrokeCap.round..strokeJoin=StrokeJoin.round..shader=const LinearGradient(colors:[Color(0xFFB8FFE0),Color(0xFF00E68A),Color(0xFF00A86B)]).createShader(Rect.fromCenter(center:c,width:110,height:120));
    final path=Path()
      ..moveTo(c.dx-48,c.dy-52)..lineTo(c.dx+8,c.dy-52)
      ..cubicTo(c.dx+65,c.dy-52,c.dx+63,c.dy+2,c.dx+8,c.dy+9)
      ..lineTo(c.dx-24,c.dy+9)..lineTo(c.dx+52,c.dy+61)
      ..moveTo(c.dx-24,c.dy+9)..lineTo(c.dx-24,c.dy+64);
    canvas.drawPath(path,runePaint);
    final orbit=Paint()..style=PaintingStyle.stroke..strokeWidth=1.8..color=aurum.withOpacity(.95);
    final orbitRect=Rect.fromCenter(center:c,width:174,height:62);
    canvas.save(); canvas.rotate(-.24); canvas.drawOval(orbitRect,orbit); canvas.restore();
    final spark=Offset(c.dx+math.cos(t*math.pi*2)*r, c.dy+math.sin(t*math.pi*2)*r);
    canvas.drawCircle(spark,3,Paint()..color=const Color(0xFFFFE9A6)..maskFilter=const MaskFilter.blur(BlurStyle.normal,5));
    canvas.drawCircle(spark,1.5,Paint()..color=ivory);
    canvas.drawCircle(c, r, Paint()..style=PaintingStyle.stroke..strokeWidth=1..color=Colors.white.withOpacity(.12));
  }
  @override
  bool shouldRepaint(covariant OrbPainter old) => old.t!=t || old.state!=state;
}

class RuneGlyph extends StatelessWidget {
  final double size;
  const RuneGlyph({super.key,this.size=32});
  @override
  Widget build(BuildContext context) => SizedBox(width:size,height:size,child:CustomPaint(painter:GlyphPainter()));
}
class GlyphPainter extends CustomPainter {
  @override
  void paint(Canvas canvas,Size s) {
    final p=Paint()..style=PaintingStyle.stroke..strokeWidth=s.width*.085..strokeCap=StrokeCap.square..strokeJoin=StrokeJoin.miter..color=brightEmerald;
    final path=Path()..moveTo(s.width*.18,s.height*.18)..lineTo(s.width*.55,s.height*.18)..cubicTo(s.width*.95,s.height*.18,s.width*.92,s.height*.52,s.width*.55,s.height*.55)..lineTo(s.width*.36,s.height*.55)..lineTo(s.width*.82,s.height*.92)..moveTo(s.width*.36,s.height*.55)..lineTo(s.width*.36,s.height*.98);
    canvas.drawPath(path,p);
  }
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate)=>false;
}

class SectionHeading extends StatelessWidget {
  final String title; final String? trailing;
  const SectionHeading({super.key,required this.title,this.trailing});
  @override
  Widget build(BuildContext context)=>Row(children:[Text(title,style:const TextStyle(fontSize:10,fontWeight:FontWeight.w700,letterSpacing:1.5,color:muted)),const Spacer(),if(trailing!=null) Text(trailing!,style:const TextStyle(fontSize:9,color:brightEmerald,letterSpacing:1.1,fontWeight:FontWeight.w600))]);
}
class QuickAction extends StatelessWidget {
  final IconData icon; final String title,subtitle;
  const QuickAction({super.key,required this.icon,required this.title,required this.subtitle});
  @override
  Widget build(BuildContext context)=>Container(padding:const EdgeInsets.symmetric(vertical:13,horizontal:4),decoration:BoxDecoration(color:carbon,borderRadius:BorderRadius.circular(14),border:Border.all(color:Colors.white.withOpacity(.06))),child:Column(children:[Icon(icon,color:brightEmerald,size:19),const SizedBox(height:9),Text(title,style:const TextStyle(fontSize:11,fontWeight:FontWeight.w600)),const SizedBox(height:3),Text(subtitle,style:const TextStyle(fontSize:8,color:muted))]));
}
class TaskRow extends StatelessWidget {
  final IconData icon; final String title,meta,tag;
  const TaskRow({super.key,required this.icon,required this.title,required this.meta,required this.tag});
  @override
  Widget build(BuildContext context)=>Padding(padding:const EdgeInsets.symmetric(horizontal:15,vertical:14),child:Row(children:[Container(width:34,height:34,decoration:BoxDecoration(color:pine,borderRadius:BorderRadius.circular(10)),child:Icon(icon,color:brightEmerald,size:17)),const SizedBox(width:11),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(title,style:const TextStyle(fontSize:12,fontWeight:FontWeight.w500)),const SizedBox(height:4),Text(meta,style:const TextStyle(fontSize:10,color:muted))])),Text(tag,style:const TextStyle(fontSize:8,letterSpacing:.8,color:brightEmerald,fontWeight:FontWeight.w700))]));
}
class StatusTile extends StatelessWidget {
  final String label,value; final IconData icon;
  const StatusTile({super.key,required this.label,required this.value,required this.icon});
  @override
  Widget build(BuildContext context)=>Container(padding:const EdgeInsets.all(14),decoration:BoxDecoration(color:carbon,borderRadius:BorderRadius.circular(14),border:Border.all(color:Colors.white.withOpacity(.06))),child:Row(children:[Icon(icon,color:muted,size:17),const SizedBox(width:9),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(label,style:const TextStyle(fontSize:8,color:muted,letterSpacing:1.2)),const SizedBox(height:4),Text(value,style:const TextStyle(fontSize:11,fontWeight:FontWeight.w600))]))]));
}

class PlaceholderPage extends StatelessWidget {
  final String title,description; final IconData icon;
  const PlaceholderPage({super.key,required this.title,required this.description,required this.icon});
  @override
  Widget build(BuildContext context)=>Center(child:Padding(padding:const EdgeInsets.all(30),child:Column(mainAxisAlignment:MainAxisAlignment.center,children:[Icon(icon,size:42,color:brightEmerald),const SizedBox(height:20),Text(title,style:Theme.of(context).textTheme.headlineMedium),const SizedBox(height:8),Text(description,textAlign:TextAlign.center,style:const TextStyle(color:muted,height:1.5))])));
}
class AssistantPage extends StatelessWidget { const AssistantPage({super.key}); @override Widget build(BuildContext context)=>const PlaceholderPage(title:'Assistant',description:'Your persistent conversation space. Voice, context and actions will connect to the R.U.N.E. runtime.',icon:Icons.forum_outlined); }
class WorkPage extends StatelessWidget { const WorkPage({super.key}); @override Widget build(BuildContext context)=>const PlaceholderPage(title:'Work',description:'Tasks, projects, plans and execution history in one workspace.',icon:Icons.work_outline_rounded); }
class ExplorePage extends StatelessWidget { const ExplorePage({super.key}); @override Widget build(BuildContext context)=>const PlaceholderPage(title:'Explore',description:'Connect integrations, configure agents and build automations with explicit permissions.',icon:Icons.hub_outlined); }
