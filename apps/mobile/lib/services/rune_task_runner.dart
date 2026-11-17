import 'dart:async';

import 'rune_device_agent.dart';
import 'rune_remote_api.dart';

class RuneTaskRunner {
  RuneTaskRunner({required this.remote,required this.device});
  final RuneRemoteApi remote;
  final RuneDeviceAgent device;
  Timer? _timer;
  bool _busy=false;
  bool get running=>_timer?.isActive??false;

  void start({Duration interval=const Duration(seconds:10)}) {
    if(running)return;
    _timer=Timer.periodic(interval,(_)=>pollOnce());
    pollOnce();
  }

  void stop(){_timer?.cancel();_timer=null;}

  Future<void> pollOnce() async {
    if(_busy)return;
    _busy=true;
    try {
      final caps=await device.capabilities();
      // App discovery and app launch do not require Accessibility. Always
      // poll after advertising the exact capabilities available on this phone.
      // UI observation/interaction remain absent from the heartbeat unless the
      // owner has enabled the Accessibility Service.
      await remote.heartbeat(_advertised(caps));
      final task=await remote.nextTask();
      if(task==null)return;
      await _execute(task);
    } on RuneRemoteException catch (error) {
      if(error.statusCode==401||error.statusCode==403) {
        stop();
        await remote.clearDeviceCredentials();
      }
      // Other remote errors are retried on the next poll.
    } catch (_) {
      // A transient network error is retried on the next poll. No success
      // response is fabricated and no task is marked complete here.
    } finally {_busy=false;}
  }

  List<String> _advertised(Map<String,dynamic> c) {
    final values=<String>[];
    if(c['appDiscovery']==true)values.add('app.list');
    if(c['appLaunch']==true)values.add('app.launch');
    if(c['uiObservation']==true)values.add('ui.observe');
    if(c['uiInteraction']==true)values.add('ui.interact');
    return values;
  }

  Future<void> _execute(Map<String,dynamic> task) async {
    final id=task['id']?.toString();
    final capability=task['capability']?.toString()??'';
    final args=task['arguments'] is Map
        ? Map<String,dynamic>.from(task['arguments'] as Map)
        : <String,dynamic>{};
    if(id==null)return;
    try {
      switch(capability) {
        case 'app.list':
          final apps=await device.installedApps();
          await remote.submitResult(id,status:'completed',output:{'apps':apps},
            evidence:{'source':'android_package_manager','count':apps.length});
          return;
        case 'app.launch':
          final packageName=(args['packageName']??args['package_name'])?.toString()??'';
          if(packageName.isEmpty)throw const RuneDeviceTaskException('package_name_required');
          final launched=await device.launchApp(packageName);
          if(!launched)throw const RuneDeviceTaskException('app_launch_unavailable');
          await Future<void>.delayed(const Duration(milliseconds:700));
          final observation=await device.observeUi();
          final active=observation['packageName']?.toString();
          final confirmed=active==packageName;
          await remote.submitResult(id,status:confirmed?'completed':'uncertain',
            output:{'launched':launched,'active_package':active},
            evidence:{'source':'accessibility_active_window','expected_package':packageName,
              'observed_package':active,'confirmed':confirmed});
          return;
        case 'ui.observe':
          final observation=await device.observeUi();
          if(observation['available']!=true)throw const RuneDeviceTaskException('accessibility_unavailable');
          await remote.submitResult(id,status:'completed',output:observation,
            evidence:{'source':'android_accessibility_service','package':observation['packageName']});
          return;
        case 'ui.interact':
          final action=args['action']?.toString()??'';
          bool ok=false;
          if(action=='tap') {
            final x=(args['x'] as num?)?.toDouble();
            final y=(args['y'] as num?)?.toDouble();
            if(x==null||y==null)throw const RuneDeviceTaskException('tap_coordinates_required');
            ok=await device.tap(x,y);
          } else if(action=='scroll') {
            ok=await device.scroll(args['direction']?.toString()??'down');
          } else if(action=='type') {
            ok=await device.typeText(args['text']?.toString()??'');
          } else {
            throw const RuneDeviceTaskException('unsupported_ui_action');
          }
          final observation=ok?await device.observeUi():<String,dynamic>{};
          await remote.submitResult(id,status:ok?'uncertain':'failed',
            output:{'action':action,'accepted_by_android':ok,'observation':observation},
            evidence:{'source':'android_accessibility_service','action_dispatched':ok,
              'note':'Dispatch acceptance is not proof that the intended app outcome occurred.'},
            errorCode:ok?null:'action_dispatch_failed');
          return;
        default:
          await remote.submitResult(id,status:'blocked',output:{},
            evidence:{'reason':'capability_not_implemented_by_this_device_agent'},
            errorCode:'capability_not_implemented');
      }
    } on RuneDeviceTaskException catch(e) {
      await remote.submitResult(id,status:'blocked',errorCode:e.code,
        evidence:{'reason':e.code});
    } catch (_) {
      await remote.submitResult(id,status:'uncertain',errorCode:'device_execution_uncertain',
        evidence:{'reason':'execution_or_verification_failed'});
    }
  }

  void dispose(){stop();}
}

class RuneDeviceTaskException implements Exception {
  const RuneDeviceTaskException(this.code);
  final String code;
  @override String toString()=>code;
}
