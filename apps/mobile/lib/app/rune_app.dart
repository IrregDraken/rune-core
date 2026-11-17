import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/rune_colors.dart';
import '../screens/onboarding_page.dart';
import '../screens/rune_pages.dart';
import '../services/rune_api.dart';

class RuneApp extends StatefulWidget {
  const RuneApp({super.key});
  @override State<RuneApp> createState()=>_RuneAppState();
}
class _RuneAppState extends State<RuneApp> {
  bool ready=false, onboarded=false;
  String owner='Owner', apiUrl='http://127.0.0.1:8765';
  @override void initState(){super.initState();_load();}
  Future<void> _load() async {
    final p=await SharedPreferences.getInstance();
    owner=p.getString('rune.owner')??'Owner';
    apiUrl=p.getString('rune.api')??apiUrl;
    onboarded=p.getBool('rune.onboarded')??false;
    if(mounted)setState(()=>ready=true);
  }
  Future<void> _complete(String name,String url) async {
    final p=await SharedPreferences.getInstance();
    await p.setString('rune.owner',name);
    await p.setString('rune.api',url);
    await p.setBool('rune.onboarded',true);
    if(mounted)setState(()=>{owner=name,apiUrl=url,onboarded=true});
  }
  Future<void> _updateApi(String url) async {
    final p=await SharedPreferences.getInstance();await p.setString('rune.api',url);
    if(mounted)setState(()=>apiUrl=url);
  }
  @override Widget build(BuildContext context){
    final theme=ThemeData(brightness:Brightness.dark,useMaterial3:true,scaffoldBackgroundColor:RuneColors.obsidian,colorScheme:const ColorScheme.dark(primary:RuneColors.brightEmerald,secondary:RuneColors.aurum,surface:RuneColors.carbon,onSurface:RuneColors.ivory),fontFamily:'Manrope',textTheme:ThemeData.dark().textTheme.apply(bodyColor:RuneColors.ivory,displayColor:RuneColors.ivory),inputDecorationTheme:InputDecorationTheme(filled:true,fillColor:RuneColors.carbon,hintStyle:const TextStyle(color:RuneColors.muted),contentPadding:const EdgeInsets.symmetric(horizontal:15,vertical:15),border:OutlineInputBorder(borderRadius:BorderRadius.circular(13),borderSide:BorderSide(color:Colors.white.withOpacity(.08))),enabledBorder:OutlineInputBorder(borderRadius:BorderRadius.circular(13),borderSide:BorderSide(color:Colors.white.withOpacity(.08))),focusedBorder:OutlineInputBorder(borderRadius:BorderRadius.circular(13),borderSide:const BorderSide(color:RuneColors.emerald))));
    return MaterialApp(debugShowCheckedModeBanner:false,title:'R.U.N.E.',theme:theme,home:!ready?const _Loading():!onboarded?OnboardingPage(onComplete:_complete):RuneShell(owner:owner,apiUrl:apiUrl,onApiChanged:_updateApi));
  }
}
class _Loading extends StatelessWidget{const _Loading();@override Widget build(BuildContext context)=>const Scaffold(body:Center(child:CircularProgressIndicator(color:RuneColors.brightEmerald)));}
class RuneShell extends StatefulWidget {
 const RuneShell({super.key,required this.owner,required this.apiUrl,required this.onApiChanged});
 final String owner,apiUrl;final Future<void> Function(String) onApiChanged;
 @override State<RuneShell> createState()=>_RuneShellState();
}
class _RuneShellState extends State<RuneShell>{
 int index=0;late RuneApi api;
 @override void initState(){super.initState();api=RuneApi(baseUrl:widget.apiUrl);}
 @override void didUpdateWidget(covariant RuneShell old){super.didUpdateWidget(old);if(old.apiUrl!=widget.apiUrl){api.close();api=RuneApi(baseUrl:widget.apiUrl);}}
 @override void dispose(){api.close();super.dispose();}
 @override Widget build(BuildContext context){
  final pages=[HomePage(owner:widget.owner,api:api,onNavigate:(i)=>setState(()=>index=i)),AssistantPage(api:api),WorkPage(api:api),ExplorePage(api:api)];
  return Scaffold(body:SafeArea(child:IndexedStack(index:index,children:pages)),bottomNavigationBar:NavigationBar(height:70,backgroundColor:const Color(0xF20D120F),indicatorColor:RuneColors.emerald.withOpacity(.15),selectedIndex:index,onDestinationSelected:(v)=>setState(()=>index=v),destinations:const [NavigationDestination(icon:Icon(Icons.grid_view_rounded),selectedIcon:Icon(Icons.grid_view_rounded,color:RuneColors.brightEmerald),label:'Home'),NavigationDestination(icon:Icon(Icons.forum_outlined),selectedIcon:Icon(Icons.forum_rounded,color:RuneColors.brightEmerald),label:'Assistant'),NavigationDestination(icon:Icon(Icons.work_outline_rounded),selectedIcon:Icon(Icons.work_rounded,color:RuneColors.brightEmerald),label:'Work'),NavigationDestination(icon:Icon(Icons.hub_outlined),selectedIcon:Icon(Icons.hub_rounded,color:RuneColors.brightEmerald),label:'Explore')]));
 }
}
