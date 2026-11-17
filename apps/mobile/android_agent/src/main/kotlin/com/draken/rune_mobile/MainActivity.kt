package com.draken.rune_mobile

import android.content.Intent
import android.os.Build
import android.provider.Settings
import android.view.accessibility.AccessibilityManager
import android.content.Context
import android.content.pm.PackageManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val channelName = "rune/device"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "capabilities" -> result.success(capabilities())
                    "installedApps" -> result.success(installedApps())
                    "launchApp" -> {
                        val packageName = call.argument<String>("packageName")
                        if (packageName.isNullOrBlank()) {
                            result.error("invalid_argument", "packageName is required", null)
                        } else {
                            val intent = packageManager.getLaunchIntentForPackage(packageName)
                            if (intent == null) result.success(false)
                            else {
                                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                startActivity(intent)
                                result.success(true)
                            }
                        }
                    }
                    "openAccessibilitySettings" -> {
                        startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
                        result.success(true)
                    }
                    "startBackgroundOperator" -> {
                        val backendUrl = call.argument<String>("backendUrl")
                        val deviceId = call.argument<String>("deviceId")
                        val deviceToken = call.argument<String>("deviceToken")
                        if (backendUrl.isNullOrBlank() || deviceId.isNullOrBlank() || deviceToken.isNullOrBlank()) {
                            result.error("invalid_argument", "Backend URL and enrolled device credentials are required", null)
                        } else {
                            val service = Intent(this, RuneOperatorService::class.java).apply {
                                action = RuneOperatorService.ACTION_START
                                putExtra("backendUrl", backendUrl)
                                putExtra("deviceId", deviceId)
                                putExtra("deviceToken", deviceToken)
                            }
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(service)
                            else startService(service)
                            result.success(true)
                        }
                    }
                    "stopBackgroundOperator" -> {
                        startService(Intent(this, RuneOperatorService::class.java).setAction(RuneOperatorService.ACTION_STOP))
                        result.success(true)
                    }
                    "observeUi" -> {
                        val service = RuneAccessibilityService.instance
                        if (service == null) result.error("accessibility_disabled", "Enable RUNE Accessibility in Android Settings", null)
                        else result.success(service.observeUi())
                    }
                    "tap" -> {
                        val x = call.argument<Double>("x")
                        val y = call.argument<Double>("y")
                        val service = RuneAccessibilityService.instance
                        if (service == null || x == null || y == null) result.success(false)
                        else result.success(service.tap(x.toFloat(), y.toFloat()))
                    }
                    "scroll" -> {
                        val direction = call.argument<String>("direction") ?: "down"
                        val service = RuneAccessibilityService.instance
                        if (service == null) result.success(false)
                        else result.success(service.scroll(direction))
                    }
                    "typeText" -> {
                        val value = call.argument<String>("text") ?: ""
                        val service = RuneAccessibilityService.instance
                        if (service == null) result.success(false)
                        else result.success(service.typeText(value))
                    }
                    else -> result.notImplemented()
                }
            }
    }

    private fun capabilities(): Map<String, Any> {
        val enabled = try {
            val manager = getSystemService(Context.ACCESSIBILITY_SERVICE) as AccessibilityManager
            manager.isEnabled && RuneAccessibilityService.instance != null
        } catch (_: Exception) { false }
        return mapOf(
            "platform" to "android",
            "accessibilityEnabled" to enabled,
            "appDiscovery" to true,
            "appLaunch" to true,
            "uiObservation" to enabled,
            "uiInteraction" to enabled,
            "notifications" to false,
            "mediaControl" to false
        )
    }

    private fun installedApps(): List<Map<String, String>> {
        val intent = Intent(Intent.ACTION_MAIN, null).addCategory(Intent.CATEGORY_LAUNCHER)
        return packageManager.queryIntentActivities(intent, PackageManager.MATCH_ALL)
            .map { info ->
                mapOf(
                    "packageName" to info.activityInfo.packageName,
                    "appName" to info.loadLabel(packageManager).toString()
                )
            }
            .distinctBy { it["packageName"] }
            .sortedBy { it["appName"]?.lowercase() }
    }
}
