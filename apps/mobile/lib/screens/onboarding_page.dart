import 'package:flutter/material.dart';
import '../theme/rune_colors.dart';
import '../widgets/rune_intelligence_orb.dart';

class OnboardingPage extends StatefulWidget {
  const OnboardingPage({super.key, required this.onComplete});
  final Future<void> Function(String owner, String apiUrl) onComplete;
  @override State<OnboardingPage> createState() => _OnboardingPageState();
}
class _OnboardingPageState extends State<OnboardingPage> {
  final name = TextEditingController();
  final api = TextEditingController(text: 'http://127.0.0.1:8765');
  int step = 0;
  bool busy = false;
  @override void dispose() { name.dispose(); api.dispose(); super.dispose(); }
  Future<void> finish() async {
    setState(() => busy = true);
    await widget.onComplete(name.text.trim().isEmpty ? 'Owner' : name.text.trim(), api.text.trim());
    if (mounted) setState(() => busy = false);
  }
  @override Widget build(BuildContext context) {
    final views = [intro(), identity(), connection()];
    return Scaffold(body: SafeArea(child: Padding(padding: const EdgeInsets.fromLTRB(26,20,26,24), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [const _Mark(), const SizedBox(width:10), const Text('R.U.N.E.', style: TextStyle(fontWeight:FontWeight.w800,letterSpacing:2.8)), const Spacer(), Text('${step+1} / 3',style:const TextStyle(color:RuneColors.muted,fontSize:11))]),
      const SizedBox(height:28),
      Row(children: List.generate(3,(i)=>Expanded(child:Container(height:3,margin:EdgeInsets.only(right:i==2?0:7),decoration:BoxDecoration(color:i<=step?RuneColors.brightEmerald:const Color(0xFF26312B),borderRadius:BorderRadius.circular(5)))))),
      const SizedBox(height:22), Expanded(child:SingleChildScrollView(child:AnimatedSwitcher(duration:const Duration(milliseconds:240),child:views[step]))),
      Row(children:[if(step>0) TextButton(onPressed:busy?null:()=>setState(()=>step--),child:const Text('BACK')),const Spacer(),FilledButton(onPressed:busy?null:()=>step<2?setState(()=>step++):finish(),style:FilledButton.styleFrom(backgroundColor:RuneColors.brightEmerald,foregroundColor:RuneColors.obsidian,padding:const EdgeInsets.symmetric(horizontal:25,vertical:15)),child:busy?const SizedBox(width:18,height:18,child:CircularProgressIndicator(strokeWidth:2,color:RuneColors.obsidian)):Text(step==2?'ENTER R.U.N.E.':'CONTINUE',style:const TextStyle(fontWeight:FontWeight.w800,letterSpacing:1)))]),
    ]))));
  }
  Widget intro()=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const SizedBox(height:12),const Center(child:RuneIntelligenceOrb(size:220, intensity:1.15)),const SizedBox(height:24),const Text('Intelligence that\nstays with you.',style:TextStyle(fontSize:34,height:1.12,fontWeight:FontWeight.w700,letterSpacing:-1.2)),const SizedBox(height:14),const Text('One intelligence layer for thinking, planning and acting across the systems you trust.',style:TextStyle(color:RuneColors.muted,height:1.7,fontSize:13)),const SizedBox(height:20),const _Feature(Icons.hub_outlined,'One intelligence, multiple interfaces'),const _Feature(Icons.verified_user_outlined,'Approval before consequential actions'),const _Feature(Icons.memory_rounded,'Persistent context and memory')]);
  Widget identity()=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const SizedBox(height:26),const Text('First, let’s set\nup your space.',style:TextStyle(fontSize:32,height:1.12,fontWeight:FontWeight.w700,letterSpacing:-1)),const SizedBox(height:12),const Text('This creates a local profile on this device. It is not proof of identity or a secure login.',style:TextStyle(color:RuneColors.muted,height:1.6)),const SizedBox(height:32),const _Label('YOUR DISPLAY NAME'),const SizedBox(height:8),TextField(controller:name,textCapitalization:TextCapitalization.words,decoration:const InputDecoration(hintText:'What should R.U.N.E. call you?')),const SizedBox(height:20),Container(padding:const EdgeInsets.all(15),decoration:BoxDecoration(color:RuneColors.carbon,borderRadius:BorderRadius.circular(14),border:Border.all(color:Colors.white10)),child:const Row(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(Icons.lock_outline,color:RuneColors.brightEmerald,size:19),SizedBox(width:11),Expanded(child:Text('Your profile stays on this device. R.U.N.E. will not request biometric data during setup.',style:TextStyle(color:RuneColors.muted,fontSize:12,height:1.5)))]))]);
  Widget connection()=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const SizedBox(height:26),const Text('Connect your\nintelligence core.',style:TextStyle(fontSize:32,height:1.12,fontWeight:FontWeight.w700,letterSpacing:-1)),const SizedBox(height:12),const Text('Enter the reachable base URL of your R.U.N.E. API. You can change it later in Settings.',style:TextStyle(color:RuneColors.muted,height:1.6)),const SizedBox(height:30),const _Label('R.U.N.E. API BASE URL'),const SizedBox(height:8),TextField(controller:api,keyboardType:TextInputType.url,autocorrect:false,decoration:const InputDecoration(prefixIcon:Icon(Icons.link),hintText:'https://your-rune-api.example.com')),const SizedBox(height:12),const Text('On a phone, 127.0.0.1 points to the phone itself, not your computer. Use your computer’s LAN IP for local testing or a secured HTTPS endpoint for remote access.',style:TextStyle(color:RuneColors.muted,fontSize:11,height:1.6)),const SizedBox(height:22),Container(padding:const EdgeInsets.all(14),decoration:BoxDecoration(color:RuneColors.pine.withOpacity(.38),borderRadius:BorderRadius.circular(13)),child:const Text('Setup only stores your core address and display name. Add the core session token in Settings after the server is configured. Enroll this phone from Device & security when the remote control plane is ready.',style:TextStyle(color:RuneColors.mint,fontSize:11,height:1.55)))]);
}
class _Mark extends StatelessWidget { const _Mark(); @override Widget build(BuildContext context)=>const SizedBox(width:28,height:28,child:CustomPaint(painter:_Glyph())); }
class _WelcomeOrb extends StatelessWidget { const _WelcomeOrb(); @override Widget build(BuildContext context)=>Container(width:190,height:190,decoration:BoxDecoration(shape:BoxShape.circle,gradient:const RadialGradient(colors:[RuneColors.pine,RuneColors.obsidian]),border:Border.all(color:RuneColors.emerald.withOpacity(.35)),boxShadow:[BoxShadow(color:RuneColors.emerald.withOpacity(.10),blurRadius:55,spreadRadius:8)]),child:const Center(child:SizedBox(width:72,height:72,child:CustomPaint(painter:_Glyph())))); }
class _Glyph extends CustomPainter {
 const _Glyph();
 @override
 void paint(Canvas canvas,Size size) {
  final rect=Rect.fromLTWH(size.width*.17,size.height*.17,size.width*.66,size.height*.66);
  final rounded=RRect.fromRectAndRadius(rect,Radius.circular(size.width*.19));
  final glow=Paint()
   ..style=PaintingStyle.stroke
   ..strokeWidth=size.width*.07
   ..color=RuneColors.emerald.withOpacity(.25)
   ..maskFilter=const MaskFilter.blur(BlurStyle.normal,4);
  final outline=Paint()
   ..style=PaintingStyle.stroke
   ..strokeWidth=size.width*.055
   ..shader=const LinearGradient(
    colors:[RuneColors.mint,RuneColors.brightEmerald,RuneColors.emerald],
    begin:Alignment.topLeft,
    end:Alignment.bottomRight,
   ).createShader(rect);
  canvas.drawRRect(rounded,glow);
  canvas.drawRRect(rounded,outline);
  canvas.save();
  canvas.translate(size.width/2,size.height/2);
  canvas.rotate(-.48);
  canvas.drawOval(
   Rect.fromCenter(center:Offset.zero,width:size.width*.98,height:size.height*.30),
   Paint()..style=PaintingStyle.stroke..strokeWidth=size.width*.035..color=RuneColors.aurum,
  );
  canvas.restore();
 }
 @override
 bool shouldRepaint(covariant CustomPainter oldDelegate)=>false;
}
class _Feature extends StatelessWidget { const _Feature(this.icon,this.text); final IconData icon;final String text; @override Widget build(BuildContext context)=>Padding(padding:const EdgeInsets.only(bottom:13),child:Row(children:[Icon(icon,size:17,color:RuneColors.brightEmerald),const SizedBox(width:12),Text(text,style:const TextStyle(fontSize:12))]));}
class _Label extends StatelessWidget { const _Label(this.text);final String text;@override Widget build(BuildContext context)=>Text(text,style:const TextStyle(color:RuneColors.muted,fontSize:9,letterSpacing:1.5,fontWeight:FontWeight.w700));}
