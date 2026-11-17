import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../services/rune_api.dart';
import '../services/rune_device_agent.dart';
import '../services/rune_remote_api.dart';
import '../services/rune_task_runner.dart';
import '../theme/rune_colors.dart';
import '../widgets/rune_intelligence_orb.dart';

class HomePage extends StatefulWidget {
 const HomePage({super.key,required this.owner,required this.api,required this.apiUrl,required this.onApiChanged,required this.onSessionTokenChanged,required this.onNavigate});
 final String owner;final RuneApi api;final String apiUrl;final Future<void> Function(String) onApiChanged,onSessionTokenChanged;final ValueChanged<int> onNavigate;
 @override State<HomePage> createState()=>_HomePageState();
}
class _HomePageState extends State<HomePage>{
 Map<String,dynamic>? state;bool online=false;String? error;
 @override void initState(){super.initState();refresh();}
 Future<void> refresh()async{try{final result=await widget.api.state();if(mounted)setState(() { state=result; online=true; error=null; });}catch(e){if(mounted)setState(() { online=false; error=e.toString(); });}}
 @override Widget build(BuildContext context){
  final hour=DateTime.now().hour;final greeting=hour<12?'Good morning':hour<17?'Good afternoon':'Good evening';
  return RefreshIndicator(onRefresh:refresh,color:RuneColors.brightEmerald,child:ListView(padding:const EdgeInsets.fromLTRB(21,18,21,30),children:[
   Row(children:[const _RuneMark(size:32),const SizedBox(width:10),const Text('R.U.N.E.',style:TextStyle(fontSize:16,fontWeight:FontWeight.w800,letterSpacing:2.7)),const Spacer(),_OnlineChip(online:online),const SizedBox(width:10),_IconButton(icon:Icons.shield_outlined,onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>SecurityPage(api:widget.api)))),_IconButton(icon:Icons.settings_outlined,onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>SettingsPage(apiUrl:widget.apiUrl,onSave:widget.onApiChanged,sessionToken:widget.api.sessionToken,onSessionTokenSave:widget.onSessionTokenChanged,api:widget.api))))]),
   const SizedBox(height:27),Text(DateTime.now().toLocal().toString().substring(0,10).toUpperCase(),style:const TextStyle(fontSize:9,color:RuneColors.muted,letterSpacing:1.8)),const SizedBox(height:7),Text('$greeting, ${widget.owner}.',style:const TextStyle(fontSize:26,fontWeight:FontWeight.w700,letterSpacing:-.7)),const SizedBox(height:4),const Text('Your command center is ready.',style:TextStyle(color:RuneColors.muted,fontSize:12)),
   const SizedBox(height:12),Center(child:Column(children:[const RuneIntelligenceOrb(),Text(online?'CORE REACHABLE':'CORE DISCONNECTED',style:TextStyle(fontSize:9,color:online?RuneColors.mint:RuneColors.aurum,letterSpacing:2,fontWeight:FontWeight.w700)),const SizedBox(height:5),Text(online?'Intelligence runtime responding':'Connect your core to activate intelligence',style:const TextStyle(fontSize:10,color:RuneColors.muted))])),
   const SizedBox(height:18),GestureDetector(onTap:()=>widget.onNavigate(1),child:Container(padding:const EdgeInsets.symmetric(horizontal:15,vertical:16),decoration:BoxDecoration(color:RuneColors.carbon,borderRadius:BorderRadius.circular(15),border:Border.all(color:Colors.white.withOpacity(.07))),child:const Row(children:[Icon(Icons.auto_awesome,color:RuneColors.brightEmerald,size:18),SizedBox(width:11),Expanded(child:Text('Ask R.U.N.E. anything...',style:TextStyle(color:RuneColors.muted,fontSize:12))),Icon(Icons.arrow_forward_rounded,color:RuneColors.muted,size:17)]))),
   const SizedBox(height:24),const _SectionTitle('QUICK ACTIONS'),
   const SizedBox(height:11),Row(children:[_QuickTile(icon:Icons.route_rounded,title:'Plan',onTap:()=>widget.onNavigate(2)),const SizedBox(width:9),_QuickTile(icon:Icons.bolt_rounded,title:'Execute',onTap:()=>widget.onNavigate(2)),const SizedBox(width:9),_QuickTile(icon:Icons.account_tree_outlined,title:'Automate',onTap:()=>widget.onNavigate(3)),const SizedBox(width:9),_QuickTile(icon:Icons.add_link_rounded,title:'Connect',onTap:()=>widget.onNavigate(3))]),
   const SizedBox(height:25),Row(children:[const _SectionTitle('SYSTEM SNAPSHOT'),const Spacer(),TextButton(onPressed:refresh,child:const Text('REFRESH',style:TextStyle(fontSize:9,letterSpacing:1,color:RuneColors.brightEmerald)))]),
   _Panel(child:Column(children:[_InfoRow('Runtime',online?'Reachable':'Offline',online?RuneColors.brightEmerald:RuneColors.aurum),_InfoRow('Identity',state==null?'Not loaded':(state?['identity']?['name']?.toString()??'Local identity'),RuneColors.muted),_InfoRow('Memory records',(state?['long_term_memory'] is List?(state!['long_term_memory'] as List).length:0).toString(),RuneColors.muted),_InfoRow('Current goal',state?['current_goal']?.toString()??'No active goal',RuneColors.muted)])),
   if(error!=null)...[const SizedBox(height:12),_Notice(text:error!,warning:true)],
   const SizedBox(height:24),const _SectionTitle('YOUR WORKSPACE'),
   const SizedBox(height:10),Row(children:[Expanded(child:_LinkCard(icon:Icons.psychology_outlined,title:'Memory',subtitle:'What R.U.N.E. knows',onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>MemoryPage(api:widget.api))))),const SizedBox(width:10),Expanded(child:_LinkCard(icon:Icons.security_outlined,title:'Security',subtitle:'Access and safeguards',onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>SecurityPage(api:widget.api)))))])
  ]));
 }
}

class AssistantPage extends StatefulWidget {
 const AssistantPage({super.key,required this.api});
 final RuneApi api;
 @override State<AssistantPage> createState()=>_AssistantPageState();
}
class _AssistantPageState extends State<AssistantPage>{
 final controller=TextEditingController();
 final scroll=ScrollController();
 final device=RuneDeviceAgent();
 final messages=<({bool user,String text})>[];
 final secureStorage=const FlutterSecureStorage();
 bool sending=false,recording=false,voiceBusy=false,awaitingConfirmation=false,historyLoaded=false,coreOnline=false;
 Timer? voiceTimer;
 @override void initState(){super.initState();_loadConversation();_refreshHealth();}
 @override void dispose(){voiceTimer?.cancel();controller.dispose();scroll.dispose();super.dispose();}

 Future<void> _refreshHealth() async {
  try {
   final online=await widget.api.health();
   if(mounted)setState(()=>coreOnline=online);
  } catch (_) {
   if(mounted)setState(()=>coreOnline=false);
  }
 }

 Future<void> _loadConversation() async {
  try {
   final raw=await secureStorage.read(key:'rune.conversation.v1');
   if(raw!=null) {
    final decoded=jsonDecode(raw);
    if(decoded is List) {
     for(final item in decoded.take(60)) {
      if(item is Map && item['text'] is String && item['user'] is bool) {
       messages.add((user:item['user'] as bool,text:(item['text'] as String).substring(0,math.min(6000,(item['text'] as String).length))));
      }
     }
    }
   }
  } catch (_) {
   // Conversation history is optional; a storage failure must not block chat.
  }
  historyLoaded=true;
  if(mounted)setState((){});
 }

 Future<void> _persistConversation() async {
  if(!historyLoaded)return;
  final recent=messages.length>60?messages.sublist(messages.length-60):messages;
  try {
   await secureStorage.write(key:'rune.conversation.v1',value:jsonEncode([
    for(final message in recent)
     {'user':message.user,'text':message.text.length>6000?message.text.substring(0,6000):message.text}
   ]));
  } catch (_) {
   if(mounted)ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content:Text('Conversation could not be saved securely on this device.')));
  }
 }

 Future<void> _clearConversation() async {
  final confirmed=await showDialog<bool>(context:context,builder:(context)=>AlertDialog(
   title:const Text('Clear conversation?'),
   content:const Text('This removes the locally saved conversation from this device. It does not delete memories stored by the R.U.N.E. core.'),
   actions:[
    TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('KEEP')),
    FilledButton(onPressed:()=>Navigator.pop(context,true),child:const Text('CLEAR')),
   ],
  ));
  if(confirmed!=true)return;
  messages.clear();
  await secureStorage.delete(key:'rune.conversation.v1').catchError((_) {});
  if(mounted)setState((){});
 }

 void scheduleConfirmationTimeout() {
  voiceTimer?.cancel();
  voiceTimer=Timer(const Duration(seconds:15),()async{
   try {await widget.api.voiceSessionAction('tick');} catch (_) {}
   if(mounted)setState(()=>awaitingConfirmation=false);
  });
 }

 void scheduleVoiceInactivity() {
  voiceTimer?.cancel();
  voiceTimer=Timer(const Duration(seconds:120),()async{
   try {
    final result=await widget.api.voiceSessionAction('tick');
    final prompt=result['prompt']?.toString();
    if(prompt!=null&&prompt.isNotEmpty) {
     if(mounted)setState(()=>awaitingConfirmation=true);
     try {
      final audio=await widget.api.synthesizeSpeech(prompt);
      await device.playAudio(audio);
     } finally {
      try {await widget.api.voiceSessionAction('confirmation_prompted');} catch (_) {}
      scheduleConfirmationTimeout();
     }
    }
   } catch (_) {}
  });
 }

 Future<void> send({bool speakResponse=false}) async {
  final text=controller.text.trim();
  if(text.isEmpty||sending)return;
  setState((){messages.add((user:true,text:text));sending=true;});
  await _persistConversation();
  controller.clear();
  try {
   final response=await widget.api.chat(text);
   final answer=response.isEmpty?'R.U.N.E. returned an empty response.':response;
   if(mounted)setState(() {
    messages.add((user:false,text:answer));
    sending=false;
   });
   await _persistConversation();
   if(speakResponse&&response.isNotEmpty) {
    var interrupted=false;
    try {
     await widget.api.voiceSessionAction('speech_started');
     final audio=await widget.api.synthesizeSpeech(response);
     interrupted=!(await device.playAudio(audio));
    } catch(e) {
     if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('Voice output unavailable: $e')));
    } finally {
     try {await widget.api.voiceSessionAction('speech_finished');} catch (_) {}
     if(!interrupted)scheduleVoiceInactivity();
    }
   }
  } catch(e) {
   if(mounted)setState(() {
    messages.add((user:false,text:'Connection error: $e'));
    sending=false;
   });
   await _persistConversation();
  }
  WidgetsBinding.instance.addPostFrameCallback((_){
   if(scroll.hasClients)scroll.animateTo(scroll.position.maxScrollExtent,
    duration:const Duration(milliseconds:250),curve:Curves.easeOut);
  });
 }

 Future<void> toggleVoice() async {
  if(voiceBusy)return;
  setState(()=>voiceBusy=true);
  String? temporaryRecording;
  try {
   if(!recording) {
    final granted=await device.requestMicrophonePermission();
    if(!granted) {
     if(mounted)ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content:Text('Allow microphone access, then tap the microphone again.')));
     return;
    }
    voiceTimer?.cancel();
    await device.stopAudio();
    if(!awaitingConfirmation)await widget.api.voiceSessionAction('wake');
    await device.startVoiceRecording();
    if(mounted)setState(()=>recording=true);
   } else {
    final path=await device.stopVoiceRecording();
    if(mounted)setState(()=>recording=false);
    if(path==null)throw const RuneApiException('Recording could not be finalized.');
    temporaryRecording=path;
    final bytes=await File(path).readAsBytes();
    final transcript=await widget.api.transcribeAudio(bytes,contentType:'audio/mp4');
    if(transcript.trim().isEmpty) {
     if(mounted)ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content:Text('No speech was detected. Try again.')));
     if(awaitingConfirmation)scheduleConfirmationTimeout();
     else scheduleVoiceInactivity();
    } else {
     final spoken=transcript.trim();
     final lowerSpoken=spoken.toLowerCase().replaceAll(RegExp(r"[.!?]"),"").trim();
     if(lowerSpoken=="stop"||lowerSpoken=="rune stop") {
      await widget.api.voiceSessionAction('stop');
      if(mounted)setState(()=>awaitingConfirmation=false);
      scheduleVoiceInactivity();
      return;
     }
     if(awaitingConfirmation) {
      final lower=spoken.toLowerCase();
      final done=RegExp(r"^(no|we're good|thats all|that's all|done|we are good)[.! ]*$").hasMatch(lower);
      await widget.api.voiceSessionAction('confirmation',continueSession:!done);
      if(mounted)setState(()=>awaitingConfirmation=false);
      if(done) {
       voiceTimer?.cancel();
       return;
      }
      if(RegExp(r"^(yes|yeah|yep|continue|i'm here|im here)[.! ]*$").hasMatch(lower)) {
       scheduleVoiceInactivity();
       return;
      }
     } else {
      await widget.api.voiceSessionAction('processing');
     }
     controller.text=spoken;
     await send(speakResponse:true);
    }
   }
  } catch(e) {
   if(mounted) {
    setState(()=>recording=false);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('Voice input failed: $e')));
   }
   if(awaitingConfirmation)scheduleConfirmationTimeout();
   else scheduleVoiceInactivity();
  } finally {
   if(temporaryRecording!=null) {
    await File(temporaryRecording).delete().catchError((_)=>File(temporaryRecording!));
   }
   if(mounted)setState(()=>voiceBusy=false);
  }
 }

 @override
 Widget build(BuildContext context) => Column(
  children: [
   Padding(
    padding: const EdgeInsets.fromLTRB(20, 17, 18, 13),
    child: Row(
     children: [
      const _RuneMark(size: 30),
      const SizedBox(width: 11),
      const Expanded(child: Column(
       crossAxisAlignment: CrossAxisAlignment.start,
       children: [
        Text('R.U.N.E.', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, letterSpacing: 2.1)),
        SizedBox(height: 3),
        Text('PERSONAL AI EXECUTIVE', style: TextStyle(fontSize: 8, color: RuneColors.muted, letterSpacing: 1.45)),
       ],
      )),
      Container(
       padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
       decoration: BoxDecoration(
        color: RuneColors.carbon.withOpacity(.82),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: (coreOnline ? RuneColors.emerald : RuneColors.aurum).withOpacity(.28)),
       ),
       child: Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 6, height: 6, decoration: BoxDecoration(
         color: coreOnline ? RuneColors.brightEmerald : RuneColors.aurum,
         shape: BoxShape.circle,
         boxShadow: [BoxShadow(color: (coreOnline ? RuneColors.brightEmerald : RuneColors.aurum).withOpacity(.45), blurRadius: 7)],
        )),
        const SizedBox(width: 7),
        Text(coreOnline ? 'CONNECTED' : 'OFFLINE', style: const TextStyle(fontSize: 8, letterSpacing: .9, color: RuneColors.muted, fontWeight: FontWeight.w700)),
       ]),
      ),
      if (messages.isNotEmpty)
       IconButton(
        tooltip: 'Clear saved conversation',
        onPressed: sending ? null : _clearConversation,
        icon: const Icon(Icons.more_horiz_rounded, color: RuneColors.muted),
       ),
     ],
    ),
   ),
   Expanded(
    child: messages.isEmpty
     ? LayoutBuilder(builder: (context, constraints) => SingleChildScrollView(
        physics: const BouncingScrollPhysics(),
        child: ConstrainedBox(
         constraints: BoxConstraints(minHeight: constraints.maxHeight),
         child: Padding(
          padding: const EdgeInsets.fromLTRB(22, 8, 22, 18),
          child: Column(
           mainAxisAlignment: MainAxisAlignment.center,
           children: [
            const SizedBox(height: 5),
            RuneIntelligenceOrb(size: math.min(250, constraints.maxWidth * .72), intensity: coreOnline ? 1.25 : .72),
            const SizedBox(height: 8),
            Text(coreOnline ? 'YOUR INTELLIGENCE IS READY' : 'YOUR INTELLIGENCE CORE',
             style: const TextStyle(fontSize: 8, color: RuneColors.mint, letterSpacing: 2.0, fontWeight: FontWeight.w700)),
            const SizedBox(height: 14),
            const Text('What’s on your mind?',
             textAlign: TextAlign.center,
             style: TextStyle(fontSize: 25, height: 1.15, fontWeight: FontWeight.w700, letterSpacing: -.8)),
            const SizedBox(height: 9),
            Text(
             coreOnline
              ? 'Think out loud. Make a plan. Put R.U.N.E. to work.'
              : 'Your assistant interface is ready. Connect the R.U.N.E. core to start a live conversation.',
             textAlign: TextAlign.center,
             style: const TextStyle(color: RuneColors.muted, fontSize: 11, height: 1.6),
            ),
            const SizedBox(height: 24),
            Align(alignment: Alignment.centerLeft, child: Text('START WITH', style: const TextStyle(fontSize: 8, color: RuneColors.muted, letterSpacing: 1.6, fontWeight: FontWeight.w700))),
            const SizedBox(height: 10),
            Wrap(
             spacing: 8,
             runSpacing: 8,
             alignment: WrapAlignment.center,
             children: [
              _PromptChip('Plan my day', Icons.calendar_today_outlined, () { controller.text = 'Help me plan my day.'; send(); }),
              _PromptChip('Think through an idea', Icons.lightbulb_outline_rounded, () { controller.text = 'Help me think through an idea.'; send(); }),
              _PromptChip('Review my work', Icons.layers_outlined, () { controller.text = 'Help me review my current work.'; send(); }),
             ],
            ),
           ],
          ),
         ),
        ),
       ))
     : ListView.builder(
        controller: scroll,
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(18, 12, 18, 24),
        itemCount: messages.length + (sending ? 1 : 0),
        itemBuilder: (context, i) {
         if (i >= messages.length) return const _Typing();
         final message = messages[i];
         return Align(
          alignment: message.user ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
           constraints: const BoxConstraints(maxWidth: 320),
           margin: const EdgeInsets.only(bottom: 13),
           padding: const EdgeInsets.fromLTRB(15, 12, 15, 13),
           decoration: BoxDecoration(
            color: message.user ? RuneColors.pine.withOpacity(.82) : RuneColors.carbon.withOpacity(.94),
            borderRadius: BorderRadius.only(
             topLeft: const Radius.circular(18),
             topRight: const Radius.circular(18),
             bottomLeft: Radius.circular(message.user ? 18 : 5),
             bottomRight: Radius.circular(message.user ? 5 : 18),
            ),
            border: Border.all(color: message.user ? RuneColors.emerald.withOpacity(.22) : Colors.white.withOpacity(.065)),
           ),
           child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(message.user ? 'YOU' : 'R.U.N.E.',
             style: const TextStyle(fontSize: 8, color: RuneColors.mint, letterSpacing: 1.4, fontWeight: FontWeight.w700)),
            const SizedBox(height: 7),
            Text(message.text, style: const TextStyle(fontSize: 12, height: 1.6)),
           ]),
          ),
         );
        },
       ),
   ),
   SafeArea(
    top: false,
    child: Padding(
     padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
     child: Container(
      padding: const EdgeInsets.fromLTRB(7, 5, 7, 5),
      decoration: BoxDecoration(
       color: const Color(0xE6101813),
       borderRadius: BorderRadius.circular(27),
       border: Border.all(color: RuneColors.mint.withOpacity(.24)),
       boxShadow: [BoxShadow(color: RuneColors.emerald.withOpacity(.07), blurRadius: 24, spreadRadius: 1)],
      ),
      child: Row(children: [
       IconButton(
        onPressed: null,
        tooltip: 'Attachments coming with the connected core',
        icon: const Icon(Icons.add_rounded, color: RuneColors.muted, size: 20),
       ),
       Expanded(child: TextField(
        controller: controller,
        minLines: 1,
        maxLines: 5,
        onSubmitted: (_) => send(),
        textInputAction: TextInputAction.send,
        decoration: const InputDecoration(
         filled: false,
         border: InputBorder.none,
         enabledBorder: InputBorder.none,
         focusedBorder: InputBorder.none,
         contentPadding: EdgeInsets.symmetric(vertical: 11),
         hintText: 'Message R.U.N.E...',
        ),
       )),
       IconButton(
        onPressed: voiceBusy ? null : toggleVoice,
        tooltip: recording ? 'Stop recording' : 'Push to talk',
        style: IconButton.styleFrom(
         backgroundColor: recording ? Colors.redAccent.withOpacity(.16) : RuneColors.pine,
         foregroundColor: recording ? Colors.redAccent : RuneColors.mint,
        ),
        icon: Icon(recording ? Icons.stop_rounded : Icons.mic_none_rounded, size: 19),
       ),
       const SizedBox(width: 3),
       IconButton.filled(
        onPressed: sending ? null : () => send(),
        style: IconButton.styleFrom(
         backgroundColor: RuneColors.brightEmerald,
         foregroundColor: RuneColors.obsidian,
        ),
        icon: const Icon(Icons.arrow_upward_rounded, size: 19),
       ),
      ]),
     ),
    ),
   ),
  ],
 );
}

class WorkPage extends StatefulWidget{const WorkPage({super.key,required this.api});final RuneApi api;@override State<WorkPage> createState()=>_WorkPageState();}
class _WorkPageState extends State<WorkPage>{
 final goal=TextEditingController();final steps=TextEditingController();Map<String,dynamic>? state;List<dynamic> events=[];bool busy=false;String? note;
 @override void initState(){super.initState();load();}
 @override void dispose(){goal.dispose();steps.dispose();super.dispose();}
 Future<void> load()async{try{final s=await widget.api.state();final e=await widget.api.activity();if(mounted)setState(() { state=s; events=e; });}catch(e){if(mounted)setState(()=>note=e.toString());}}
 Future<void> create()async{if(goal.text.trim().isEmpty)return;setState(()=>busy=true);try{await widget.api.setGoal(goal.text.trim());final list=steps.text.split('\n').map((e)=>e.trim()).where((e)=>e.isNotEmpty).toList();if(list.isNotEmpty)await widget.api.createPlan(goal.text.trim(),list);goal.clear();steps.clear();setState(()=>note='Goal submitted to the core.');await load();}catch(e){setState(()=>note=e.toString());}if(mounted)setState(()=>busy=false);}
 @override Widget build(BuildContext context)=>ListView(padding:const EdgeInsets.fromLTRB(20,20,20,30),children:[const _PageHeader(title:'Work',eyebrow:'PLANS · TASKS · EXECUTION'),const SizedBox(height:20),_Panel(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('Set an objective',style:TextStyle(fontSize:15,fontWeight:FontWeight.w700)),const SizedBox(height:6),const Text('Create a goal in the R.U.N.E. core. Add optional plan steps, one per line.',style:TextStyle(color:RuneColors.muted,fontSize:11,height:1.5)),const SizedBox(height:14),TextField(controller:goal,decoration:const InputDecoration(hintText:'What outcome do you want?')),const SizedBox(height:9),TextField(controller:steps,minLines:2,maxLines:5,decoration:const InputDecoration(hintText:'Plan steps (optional, one per line)')),const SizedBox(height:12),Align(alignment:Alignment.centerRight,child:FilledButton(onPressed:busy?null:create,child:Text(busy?'SENDING...':'CREATE PLAN')))])),
 if(note!=null)...[const SizedBox(height:10),_Notice(text:note!)],
 const SizedBox(height:24),const _SectionTitle('ACTIVE GOAL'),const SizedBox(height:10),_Panel(child:Text(state?['current_goal']?.toString()??'No active goal has been set.',style:const TextStyle(fontSize:13,height:1.5))),
 const SizedBox(height:24),const _SectionTitle('RECENT ACTIVITY'),const SizedBox(height:10),if(events.isEmpty)_Panel(child:const Text('No activity events returned by the core.',style:TextStyle(color:RuneColors.muted,fontSize:11)))else ...events.take(12).map((e)=>_ActivityTile(event:e as Map<String,dynamic>))
 ]);
}

class ExplorePage extends StatefulWidget{const ExplorePage({super.key,required this.api});final RuneApi api;@override State<ExplorePage> createState()=>_ExplorePageState();}
class _ExplorePageState extends State<ExplorePage>{
 List<dynamic> tools=[];bool loading=true;String? error;
 @override void initState(){super.initState();load();}
 Future<void> load()async{try{final t=await widget.api.tools();if(mounted)setState(() { tools=t; loading=false; error=null; });}catch(e){if(mounted)setState(() { loading=false; error=e.toString(); });}}
 @override Widget build(BuildContext context)=>ListView(padding:const EdgeInsets.fromLTRB(20,20,20,30),children:[const _PageHeader(title:'Explore',eyebrow:'CAPABILITIES · INTEGRATIONS'),const SizedBox(height:9),const Text('Discover what your connected runtime exposes. External int
class _PromptChip extends StatelessWidget {
 const _PromptChip(this.label, this.icon, this.onTap);
 final String label;
 final IconData icon;
 final VoidCallback onTap;
 @override
 Widget build(BuildContext context) => ActionChip(
  onPressed: onTap,
  avatar: Icon(icon, size: 14, color: RuneColors.mint),
  label: Text(label, style: const TextStyle(fontSize: 10)),
  backgroundColor: RuneColors.carbon.withOpacity(.8),
  side: BorderSide(color: RuneColors.emerald.withOpacity(.22)),
  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 5),
 );
}
egrations appear only when they are actually configured.',style:TextStyle(color:RuneColors.muted,fontSize:11,height:1.6)),const SizedBox(height:22),const _SectionTitle('CORE CAPABILITIES'),const SizedBox(height:10),if(loading)const Center(child:CircularProgressIndicator())else if(error!=null)_Notice(text:error!,warning:true)else if(tools.isEmpty)_Panel(child:const Text('The core has not exposed any tools yet.',style:TextStyle(color:RuneColors.muted,fontSize:11)))else ...tools.map((item){final t=item as Map<String,dynamic>;return _ToolTile(tool:t);}),const SizedBox(height:24),const _SectionTitle('INTEGRATION CHANNELS'),const SizedBox(height:10),const _Panel(child:Column(children:[_IntegrationRow('Google Workspace','Not connected',Icons.mail_outline),_IntegrationRow('WhatsApp','Not connected',Icons.chat_bubble_outline),_IntegrationRow('Discord','Not connected',Icons.forum_outlined),_IntegrationRow('GitHub','Not connected',Icons.code),_IntegrationRow('Notion','Not connected',Icons.article_outlined)])),const SizedBox(height:8),const Text('Connectors are shown as unavailable until credentials and permission scopes are configured in the core.',style:TextStyle(color:RuneColors.muted,fontSize:10,height:1.5))]);
}

class MemoryPage extends StatefulWidget {
  const MemoryPage({super.key, required this.api});
  final RuneApi api;
  @override
  State<MemoryPage> createState() => _MemoryPageState();
}

class _MemoryPageState extends State<MemoryPage> {
  Map<String, dynamic>? state;
  String? error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final result = await widget.api.state();
      if (mounted) setState(() => state = result);
    } catch (exception) {
      if (mounted) setState(() => error = exception.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final rawRecords = state?['long_term_memory'];
    final records = rawRecords is List ? rawRecords : const <dynamic>[];
    return Scaffold(
      appBar: AppBar(title: const Text('Memory')),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          const Text('PERSISTENT CONTEXT', style: TextStyle(color: RuneColors.muted, fontSize: 9, letterSpacing: 1.5)),
          const SizedBox(height: 8),
          const Text('What R.U.N.E. remembers', style: TextStyle(fontSize: 23, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          const Text('Memory is owned by the core. This screen displays records returned by the connected runtime.', style: TextStyle(color: RuneColors.muted, fontSize: 11, height: 1.5)),
          const SizedBox(height: 18),
          if (error != null)
            _Notice(text: error!, warning: true)
          else if (records.isEmpty)
            _Panel(child: Text(state == null ? 'Loading memory...' : 'No memory records were returned.', style: const TextStyle(color: RuneColors.muted, fontSize: 11)))
          else
            ...records.map((record) {
              final item = record is Map ? Map<String, dynamic>.from(record) : <String, dynamic>{};
              return _Panel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item['key']?.toString() ?? 'Untitled memory', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                    const SizedBox(height: 6),
                    Text(item['value']?.toString() ?? '', style: const TextStyle(fontSize: 11, height: 1.5)),
                    const SizedBox(height: 8),
                    Text('${item['kind'] ?? 'memory'} · salience ${item['salience'] ?? '—'}', style: const TextStyle(color: RuneColors.muted, fontSize: 9)),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }
}

class SecurityPage extends StatefulWidget {
 const SecurityPage({super.key,required this.api});
 final RuneApi api;
 @override State<SecurityPage> createState()=>_SecurityPageState();
}
class _SecurityPageState extends State<SecurityPage> {
 final agent=RuneDeviceAgent();
 final backend=TextEditingController();
 final supabase=TextEditingController();
 final publishable=TextEditingController();
 final email=TextEditingController();
 final password=TextEditingController();
 Map<String,dynamic> capabilities={};
 List<Map<String,String>> apps=[];
 List<dynamic> pending=[];
 RuneRemoteApi? remote;
 RuneTaskRunner? runner;
 String? error;
 String status='Not enrolled';
 bool loading=true,busy=false;
 @override void initState(){super.initState();load();}
 @override void dispose(){runner?.dispose();remote?.close();backend.dispose();supabase.dispose();publishable.dispose();email.dispose();password.dispose();super.dispose();}
 Future<void> load() async {
  try {
   final c=await agent.capabilities();
   final a=await agent.installedApps();
   if(mounted)setState(() { capabilities=c; apps=a; loading=false; error=null; });
  } catch(e) {
   if(mounted)setState(() { loading=false; error='Native Android agent unavailable: $e'; });
  }
 }
 Future<void> refreshPending() async {
  final api=remote;
  if(api==null)return;
  try {final items=await api.pendingTasks();if(mounted)setState(()=>pending=items);}
  catch(e){if(mounted)setState(()=>error=e.toString());}
 }
 Future<void> stopOperator() async {
  try {await agent.stopBackgroundOperator();runner?.stop();if(mounted)setState(()=>status='Device operator paused');}
  catch(e){if(mounted)setState(()=>error=e.toString());}
 }
 Future<void> revokeDevice() async {
  final confirmed=await showDialog<bool>(context:context,builder:(context)=>AlertDialog(
   title:const Text('Revoke this device?'),
   content:const Text('RUNE will revoke this phone, cancel queued tasks and delete its locally stored device credential. An action already in progress may finish. You will need to enroll it again.'),
   actions:[
    TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('KEEP DEVICE')),
    FilledButton(onPressed:()=>Navigator.pop(context,true),child:const Text('REVOKE')),
   ],
  ));
  if(confirmed!=true)return;
  final api=remote;if(api==null)return;
  setState(()=>busy=true);
  try {
   await agent.stopBackgroundOperator();
   runner?.stop();
   await api.revokeThisDevice();
   if(mounted)setState(() { status='Device revoked'; remote=null; runner=null; pending=[]; });
  } catch(e){if(mounted)setState(()=>error=e.toString());}
  if(mounted)setState(()=>busy=false);
 }
 Future<void> approve(String taskId) async {
  final api=remote;if(api==null)return;
  setState(()=>busy=true);
  try {await api.approveTask(taskId);await refreshPending();}
  catch(e){if(mounted)setState(()=>error=e.toString());}
  if(mounted)setState(()=>busy=false);
 }
 Future<void> cancelTask(String taskId) async {
  final api=remote;if(api==null)return;
  setState(()=>busy=true);
  try {await api.cancelTask(taskId);await refreshPending();}
  catch(e){if(mounted)setState(()=>error=e.toString());}
  if(mounted)setState(()=>busy=false);
 }
 Future<void> enrollAndStart() async {
  if(backend.text.trim().isEmpty||supabase.text.trim().isEmpty||publishable.text.trim().isEmpty||email.text.trim().isEmpty||password.text.isEmpty)return;
  setState(()=>busy=true);
  try {
   final c=await agent.capabilities();
   final remoteApi=RuneRemoteApi(
    backendUrl:backend.text.trim(),
    supabaseUrl:supabase.text.trim(),
    publishableKey:publishable.text.trim(),
   );
   await remoteApi.signIn(email.text.trim(),password.text);
   password.clear();

   var credentials=await remoteApi.deviceCredentials();
   Map<String,dynamic>? device;
   if(credentials!=null) {
    final known=await remoteApi.devices();
    for(final item in known) {
     if(item is Map && item['id']?.toString()==credentials['id']?.toString() && item['status']!='revoked') {
      device=Map<String,dynamic>.from(item);
      break;
     }
    }
    if(device==null) {
     await remoteApi.clearDeviceCredentials();
     credentials=null;
    }
   }

   if(credentials==null) {
    final caps=<String>[];
    if(c['appDiscovery']==true)caps.add('app.list');
    if(c['appLaunch']==true)caps.add('app.launch');
    if(c['uiObservation']==true)caps.add('ui.observe');
    if(c['uiInteraction']==true)caps.add('ui.interact');
    device=await remoteApi.registerDevice(
     name:'RUNE Android Device',capabilities:caps,appVersion:'0.2.0');
    credentials=await remoteApi.deviceCredentials();
   }

   await agent.requestNotificationPermission();
   final started=credentials==null?false:await agent.startBackgroundOperator(
    backendUrl:backend.text.trim(),
    deviceId:credentials['id'].toString(),
    deviceToken:credentials['token'].toString(),
   );
   RuneTaskRunner? taskRunner;
   if(!started)taskRunner=RuneTaskRunner(remote:remoteApi,device:agent)..start();
   if(mounted)setState(() {
    remote=remoteApi;
    runner=taskRunner;
    status='Enrolled: ${device?['device_name']??'Android device'} · ${started?'background operator requested':'foreground-only operator started'}';
    error=null;
   });
   await refreshPending();
  } catch(e) {
   if(mounted)setState(()=>error=e.toString());
  }
  if(mounted)setState(()=>busy=false);
 }
 @override Widget build(BuildContext context)=>Scaffold(
  appBar:AppBar(title:const Text('Device & security')),
  body:ListView(padding:const EdgeInsets.all(18),children:[
   const _Notice(text:'RUNE uses Android Accessibility only after you explicitly enable it. It can inspect and interact with visible interfaces, not bypass app authentication or Android security.'),
   const SizedBox(height:16),
   const _SectionTitle('ANDROID DEVICE AGENT'),
   const SizedBox(height:10),
   _Panel(child:Column(children:[
    _InfoRow('Platform',capabilities['platform']?.toString()??'Checking…',RuneColors.muted),
    _InfoRow('App discovery',capabilities['appDiscovery']==true?'Available':'Unavailable',RuneColors.muted),
    _InfoRow('App launch',capabilities['appLaunch']==true?'Available':'Unavailable',RuneColors.muted),
    _InfoRow('Accessibility',capabilities['accessibilityEnabled']==true?'Enabled':'Not enabled',capabilities['accessibilityEnabled']==true?RuneColors.brightEmerald:RuneColors.aurum),
    _InfoRow('UI observation',capabilities['uiObservation']==true?'Available':'Permission required',RuneColors.muted),
    _InfoRow('UI interaction',capabilities['uiInteraction']==true?'Available':'Permission required',RuneColors.muted),
   ])),
   if(error!=null)_Notice(text:error!,warning:true),
   const SizedBox(height:8),
   FilledButton.icon(onPressed:loading?null:()async{try{await agent.openAccessibilitySettings();}catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}},icon:const Icon(Icons.accessibility_new),label:const Text('OPEN ACCESSIBILITY SETTINGS')),
   OutlinedButton.icon(onPressed:load,icon:const Icon(Icons.refresh),label:const Text('REFRESH DEVICE STATUS')),
   const SizedBox(height:20),
   const _SectionTitle('REMOTE ENROLLMENT'),
   const SizedBox(height:8),
   _Panel(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    Text(status,style:const TextStyle(color:RuneColors.brightEmerald,fontSize:11,fontWeight:FontWeight.w700)),
    const SizedBox(height:12),
    const Text('Remote backend URL',style:TextStyle(fontSize:10,color:RuneColors.muted)),
    const SizedBox(height:5),TextField(controller:backend,keyboardType:TextInputType.url,decoration:const InputDecoration(hintText:'https://your-rune-backend.example.com')),
    const SizedBox(height:10),const Text('Supabase project URL',style:TextStyle(fontSize:10,color:RuneColors.muted)),
    const SizedBox(height:5),TextField(controller:supabase,keyboardType:TextInputType.url,decoration:const InputDecoration(hintText:'https://project.supabase.co')),
    const SizedBox(height:10),const Text('Supabase publishable key',style:TextStyle(fontSize:10,color:RuneColors.muted)),
    const SizedBox(height:5),TextField(controller:publishable,decoration:const InputDecoration(hintText:'sb_publishable_…')),
    const SizedBox(height:10),const Text('Account email',style:TextStyle(fontSize:10,color:RuneColors.muted)),
    const SizedBox(height:5),TextField(controller:email,keyboardType:TextInputType.emailAddress,decoration:const InputDecoration(hintText:'you@example.com')),
    const SizedBox(height:10),const Text('Account password',style:TextStyle(fontSize:10,color:RuneColors.muted)),
    const SizedBox(height:5),TextField(controller:password,obscureText:true,decoration:const InputDecoration(hintText:'Supabase Auth password')),
    const SizedBox(height:14),
    SizedBox(width:double.infinity,child:FilledButton.icon(onPressed:busy?null:enrollAndStart,icon:const Icon(Icons.phonelink_lock),label:Text(busy?'ENROLLING…':'SIGN IN, ENROLL & START OPERATOR'))),
    if(remote!=null)OutlinedButton.icon(onPressed:stopOperator,icon:const Icon(Icons.pause_circle_outline),label:const Text('PAUSE DEVICE OPERATOR')),
    if(remote!=null)TextButton.icon(onPressed:busy?null:revokeDevice,icon:const Icon(Icons.phonelink_erase,color:Colors.redAccent),label:const Text('REVOKE THIS DEVICE',style:TextStyle(color:Colors.redAccent))),
    const SizedBox(height:8),
    const Text('The password is sent only to Supabase Auth over HTTPS. Owner and device tokens are stored securely. Android runs the remote operator as a foreground service with a persistent notification; Android may still impose background execution limits.',style:TextStyle(color:RuneColors.muted,fontSize:9,height:1.5)),
   ])),
   if(remote!=null)...[
    const SizedBox(height:20),
    Row(children:[const _SectionTitle('PENDING DEVICE ACTIONS'),const Spacer(),TextButton(onPressed:refreshPending,child:const Text('REFRESH'))]),
    if(pending.isEmpty)_Panel(child:const Text('No actions are waiting for your approval.',style:TextStyle(color:RuneColors.muted,fontSize:11)))
    else ...pending.map((item){
      final task=item as Map<String,dynamic>;
      return _Panel(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
       Text(task['capability']?.toString()??'Device action',style:const TextStyle(fontWeight:FontWeight.w700,fontSize:12)),
       const SizedBox(height:5),
       Text(task['arguments']?.toString()??'{}',style:const TextStyle(color:RuneColors.muted,fontSize:10)),
       const SizedBox(height:8),
       Row(children:[const Text('AWAITING APPROVAL',style:TextStyle(color:RuneColors.aurum,fontSize:8,letterSpacing:1)),const Spacer(),
        TextButton(onPressed:busy?null:()=>cancelTask(task['id'].toString()),child:const Text('CANCEL')),
        FilledButton.tonal(onPressed:busy?null:()=>approve(task['id'].toString()),child:const Text('APPROVE'))
       ])
      ]));
    })
   ],
   const SizedBox(height:20),
   const _SectionTitle('VISIBLE APP CATALOG'),
   const SizedBox(height:8),
   if(loading)const Center(child:CircularProgressIndicator())
   else if(apps.isEmpty)_Panel(child:const Text('No launchable apps returned, or native app discovery is unavailable.',style:TextStyle(color:RuneColors.muted,fontSize:11)))
   else ...apps.take(100).map((app)=>_Panel(child:Row(children:[
    const Icon(Icons.apps,color:RuneColors.brightEmerald),const SizedBox(width:10),
    Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
     Text(app['appName']??'Application',style:const TextStyle(fontSize:11,fontWeight:FontWeight.w700)),
     Text(app['packageName']??'',style:const TextStyle(fontSize:9,color:RuneColors.muted))
    ])),
    IconButton(onPressed:()async{try{final ok=await agent.launchApp(app['packageName']??'');if(!ok&&mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Android did not provide a launch intent.')));}catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}},icon:const Icon(Icons.open_in_new,color:RuneColors.brightEmerald))
   ]))),
  ])
 );
}

class SettingsPage extends StatefulWidget {
 const SettingsPage({super.key,required this.apiUrl,required this.onSave,required this.sessionToken,required this.onSessionTokenSave,required this.api});
 final String apiUrl,sessionToken;
 final Future<void> Function(String) onSave,onSessionTokenSave;
 final RuneApi api;
 @override State<SettingsPage> createState()=>_SettingsPageState();
}
class _SettingsPageState extends State<SettingsPage>{
 late TextEditingController url;
 late TextEditingController token;
 bool checking=false;
 String? status;
 @override void initState(){super.initState();url=TextEditingController(text:widget.apiUrl);token=TextEditingController(text:widget.sessionToken);}
 @override void dispose(){url.dispose();token.dispose();super.dispose();}
 @override Widget build(BuildContext context)=>Scaffold(
  appBar:AppBar(title:const Text('Settings')),
  body:ListView(padding:const EdgeInsets.all(18),children:[
   const _SectionTitle('CONNECTION'),const SizedBox(height:10),
   _Panel(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    const Text('Core API address',style:TextStyle(fontWeight:FontWeight.w700)),
    const SizedBox(height:8),
    TextField(controller:url,keyboardType:TextInputType.url,decoration:const InputDecoration(hintText:'https://your-rune-core.example.com')),
    const SizedBox(height:6),
    const Text('On a phone, localhost refers to the phone itself. Use the HTTPS address of your deployed core.',style:TextStyle(fontSize:9,color:RuneColors.muted,height:1.4)),
    const SizedBox(height:10),
    const Text('Local core session token',style:TextStyle(fontWeight:FontWeight.w700)),
    const SizedBox(height:8),
    TextField(controller:token,obscureText:true,decoration:const InputDecoration(hintText:'RUNE_SESSION_TOKEN from core environment')),
    const SizedBox(height:6),
    const Text('Stored using platform secure storage. It must match RUNE_SESSION_TOKEN on the core host.',style:TextStyle(fontSize:9,color:RuneColors.muted,height:1.4)),
    const SizedBox(height:10),
    if(status!=null)Text(status!,style:const TextStyle(fontSize:10,color:RuneColors.muted)),
    Row(children:[
     TextButton(onPressed:checking?null:()async{
      setState(()=>checking=true);
      RuneApi? probe;
      try {
       final client=RuneApi(baseUrl:url.text.trim(),sessionToken:token.text.trim());
       probe=client;
       final ok=await client.health();
       if(ok) {
        await client.state();
        setState(()=>status='Core reachable and session accepted.');
       } else {
        setState(()=>status='Core did not report online.');
       }
      } catch(e){setState(()=>status=e.toString());}
      finally {probe?.close();}
      setState(()=>checking=false);
     },child:const Text('TEST CONNECTION')),
     const Spacer(),
     FilledButton(onPressed:()async{
      await widget.onSave(url.text.trim());
      await widget.onSessionTokenSave(token.text.trim());
      if(mounted)Navigator.pop(context);
     },child:const Text('SAVE'))
    ])
   ])),
   const SizedBox(height:20),const _SectionTitle('ABOUT THIS BUILD'),
   const SizedBox(height:10),
   const _Panel(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    _InfoRow('App','R.U.N.E. Mobile',RuneColors.muted),
    _InfoRow('Platform','Flutter',RuneColors.muted),
    _InfoRow('Typography','Manrope + system mono',RuneColors.muted),
    _InfoRow('Session token','Encrypted local storage',RuneColors.muted)
   ]))
  ])
 );
}

class _PageHeader extends StatelessWidget{const _PageHeader({required this.title,required this.eyebrow});final String title,eyebrow;@override Widget build(BuildContext context)=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(eyebrow,style:const TextStyle(color:RuneColors.muted,fontSize:9,letterSpacing:1.5)),const SizedBox(height:6),Text(title,style:const TextStyle(fontSize:27,fontWeight:FontWeight.w700,letterSpacing:-.7))]);}
class _SectionTitle extends StatelessWidget{const _SectionTitle(this.text);final String text;@override Widget build(BuildContext context)=>Text(text,style:const TextStyle(fontSize:9,fontWeight:FontWeight.w800,letterSpacing:1.5,color:RuneColors.muted));}
class _Panel extends StatelessWidget{const _Panel({required this.child});final Widget child;@override Widget build(BuildContext context)=>Container(width:double.infinity,margin:const EdgeInsets.only(bottom:9),padding:const EdgeInsets.all(15),decoration:BoxDecoration(color:RuneColors.carbon,borderRadius:BorderRadius.circular(15),border:Border.all(color:Colors.white.withOpacity(.06))),child:child);}
class _InfoRow extends StatelessWidget{const _InfoRow(this.label,this.value,this.color);final String label,value;final Color color;@override Widget build(BuildContext context)=>Padding(padding:const EdgeInsets.symmetric(vertical:8),child:Row(children:[Expanded(child:Text(label,style:const TextStyle(color:RuneColors.muted,fontSize:11))),Flexible(child:Text(value,textAlign:TextAlign.right,style:TextStyle(color:color,fontSize:10,fontWeight:FontWeight.w600)))]));}
class _Notice extends StatelessWidget{const _Notice({required this.text,this.warning=false});final String text;final bool warning;@override Widget build(BuildContext context)=>Container(padding:const EdgeInsets.all(13),decoration:BoxDecoration(color:warning?const Color(0xFF302417):RuneColors.pine.withOpacity(.35),borderRadius:BorderRadius.circular(12),border:Border.all(color:warning?RuneColors.aurum.withOpacity(.2):RuneColors.emerald.withOpacity(.2))),child:Text(text,style:TextStyle(color:warning?const Color(0xFFE6C995):RuneColors.mint,fontSize:10,height:1.5)));}
class _OnlineChip extends StatelessWidget{const _OnlineChip({required this.online});final bool online;@override Widget build(BuildContext context)=>Container(padding:const EdgeInsets.symmetric(horizontal:9,vertical:7),decoration:BoxDecoration(color:RuneColors.pine.withOpacity(.5),borderRadius:BorderRadius.circular(30),border:Border.all(color:RuneColors.emerald.withOpacity(.2))),child:Row(children:[Icon(Icons.circle,size:6,color:online?RuneColors.brightEmerald:RuneColors.aurum),const SizedBox(width:6),Text(online?'CORE ONLINE':'CORE OFFLINE',style:const TextStyle(fontSize:8,letterSpacing:.8,color:RuneColors.muted))]));}
class _IconButton extends StatelessWidget{const _IconButton({required this.icon,required this.onTap});final IconData icon;final VoidCallback onTap;@override Widget build(BuildContext context)=>IconButton(onPressed:onTap,icon:Icon(icon,color:RuneColors.muted,size:20));}
class _QuickTile extends StatelessWidget{const _QuickTile({required this.icon,required this.title,required this.onTap});final IconData icon;final String title;final VoidCallback onTap;@override Widget build(BuildContext context)=>Expanded(child:InkWell(onTap:onTap,borderRadius:BorderRadius.circular(13),child:Container(padding:const EdgeInsets.symmetric(vertical:14),decoration:BoxDecoration(color:RuneColors.carbon,borderRadius:BorderRadius.circular(13),border:Border.all(color:Colors.white.withOpacity(.06))),child:Column(children:[Icon(icon,color:RuneColors.brightEmerald,size:18),const SizedBox(height:8),Text(title,style:const TextStyle(fontSize:10,fontWeight:FontWeight.w700))]))));}
class _LinkCard extends StatelessWidget{const _LinkCard({required this.icon,required this.title,required this.subtitle,required this.onTap});final IconData icon;final String title,subtitle;final VoidCallback onTap;@override Widget build(BuildContext context)=>Expanded(child:InkWell(onTap:onTap,borderRadius:BorderRadius.circular(14),child:Container(padding:const EdgeInsets.all(14),decoration:BoxDecoration(color:RuneColors.carbon,borderRadius:BorderRadius.circular(14),border:Border.all(color:Colors.white.withOpacity(.06))),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(icon,color:RuneColors.brightEmerald),const SizedBox(height:13),Text(title,style:const TextStyle(fontSize:12,fontWeight:FontWeight.w700)),const SizedBox(height:3),Text(subtitle,style:const TextStyle(fontSize:9,color:RuneColors.muted))]))));}
class _ActivityTile extends StatelessWidget{const _ActivityTile({required this.event});final Map<String,dynamic> event;@override Widget build(BuildContext context)=>_Panel(child:Row(children:[const Icon(Icons.bolt_outlined,color:RuneColors.brightEmerald,size:18),const SizedBox(width:10),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(event['type']?.toString()??'Event',style:const TextStyle(fontSize:11,fontWeight:FontWeight.w700)),Text(event['timestamp']?.toString()??'',style:const TextStyle(fontSize:9,color:RuneColors.muted))]))]));}
class _ToolTile extends StatelessWidget{const _ToolTile({required this.tool});final Map<String,dynamic> tool;@override Widget build(BuildContext context)=>_Panel(child:Row(children:[const Icon(Icons.extension_outlined,color:RuneColors.brightEmerald),const SizedBox(width:12),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(tool['name']?.toString()??'Capability',style:const TextStyle(fontSize:12,fontWeight:FontWeight.w700)),const SizedBox(height:4),Text(tool['description']?.toString()??'',style:const TextStyle(fontSize:10,color:RuneColors.muted,height:1.4))])),const SizedBox(width:8),Text(tool['risk']?.toString().toUpperCase()??'UNKNOWN',style:const TextStyle(fontSize:8,color:RuneColors.aurum,letterSpacing:.6))]));}
class _IntegrationRow extends StatelessWidget{const _IntegrationRow(this.name,this.status,this.icon);final String name,status;final IconData icon;@override Widget build(BuildContext context)=>Padding(padding:const EdgeInsets.symmetric(vertical:10),child:Row(children:[Icon(icon,color:RuneColors.muted,size:18),const SizedBox(width:12),Expanded(child:Text(name,style:const TextStyle(fontSize:11,fontWeight:FontWeight.w600))),Text(status,style:const TextStyle(fontSize:9,color:RuneColors.muted))]));}
class _Typing extends StatelessWidget{const _Typing();@override Widget build(BuildContext context)=>const Padding(padding:EdgeInsets.all(16),child:Align(alignment:Alignment.centerLeft,child:Text('R.U.N.E. is thinking…',style:TextStyle(color:RuneColors.muted,fontSize:11))));}
class _RuneMark extends StatelessWidget {
 const _RuneMark({this.size=30});
 final double size;
 @override
 Widget build(BuildContext context) => SizedBox(
  width:size,
  height:size,
  child:CustomPaint(painter:_GlyphPainter()),
 );
}

class _GlyphPainter extends CustomPainter {
 @override
 void paint(Canvas canvas,Size size) {
  final rect=Rect.fromLTWH(size.width*.17,size.height*.17,size.width*.66,size.height*.66);
  final radius=Radius.circular(size.width*.19);
  final glow=Paint()
   ..style=PaintingStyle.stroke
   ..strokeWidth=size.width*.07
   ..color=RuneColors.emerald.withOpacity(.22)
   ..maskFilter=const MaskFilter.blur(BlurStyle.normal,3);
  final outline=Paint()
   ..style=PaintingStyle.stroke
   ..strokeWidth=size.width*.055
   ..shader=const LinearGradient(
    colors:[RuneColors.mint,RuneColors.brightEmerald,RuneColors.emerald],
    begin:Alignment.topLeft,
    end:Alignment.bottomRight,
   ).createShader(rect);
  canvas.drawRRect(RRect.fromRectAndRadius(rect,radius),glow);
  canvas.drawRRect(RRect.fromRectAndRadius(rect,radius),outline);
  canvas.save();
  canvas.translate(size.width/2,size.height/2);
  canvas.rotate(-.48);
  final orbit=Rect.fromCenter(
   center:Offset.zero,
   width:size.width*.98,
   height:size.height*.30,
  );
  canvas.drawOval(orbit,Paint()
   ..style=PaintingStyle.stroke
   ..strokeWidth=size.width*.035
   ..color=RuneColors.aurum);
  canvas.restore();
 }
 @override
 bool shouldRepaint(covariant CustomPainter oldDelegate)=>false;
}
