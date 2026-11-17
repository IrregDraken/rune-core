package com.draken.rune_mobile

import android.content.Intent
import android.os.Build
import android.provider.Settings
import android.view.accessibility.AccessibilityManager
import android.content.Context
import android.content.pm.PackageManager
import android.media.MediaPlayer
import android.media.MediaRecorder
import java.io.File
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val channelName = "rune/device"
    private var mediaRecorder: MediaRecorder? = null
    private var recordingFile: File? = null
    private var mediaPlayer: MediaPlayer? = null
    private var playbackFile: File? = null

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
                    "hasMicrophonePermission" -> {
                        result.success(checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED)
                    }
                    "requestMicrophonePermission" -> {
                        if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                            requestPermissions(arrayOf(android.Manifest.permission.RECORD_AUDIO), 4203)
                            result.success(false)
                        } else {
                            result.success(true)
                        }
                    }
                    "startVoiceRecording" -> {
                        if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                            result.error("microphone_permission", "Microphone permission is required", null)
                        } else {
                            var pendingRecorder: MediaRecorder? = null
                            var pendingFile: File? = null
                            try {
                                val file = File(cacheDir, "rune-utterance-${System.currentTimeMillis()}.m4a")
                                pendingFile = file
                                val recorder = if (Build.VERSION.SDK_INT >= 31) MediaRecorder(this) else MediaRecorder()
                                pendingRecorder = recorder
                                recorder.setAudioSource(MediaRecorder.AudioSource.MIC)
                                recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                                recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                                recorder.setAudioSamplingRate(16000)
                                recorder.setAudioEncodingBitRate(64000)
                                recorder.setOutputFile(file.absolutePath)
                                recorder.prepare()
                                recorder.start()
                                mediaRecorder = recorder
                                recordingFile = file
                                result.success(true)
                            } catch (error: Exception) {
                                pendingRecorder?.release()
                                pendingFile?.delete()
                                mediaRecorder = null
                                recordingFile = null
                                result.error("recording_start_failed", "Could not start voice recording", null)
                            }
                        }
                    }
                    "stopVoiceRecording" -> {
                        try {
                            val recorder = mediaRecorder ?: throw IllegalStateException("No recording is active")
                            recorder.stop()
                            recorder.release()
                            mediaRecorder = null
                            val file = recordingFile ?: throw IllegalStateException("Recording file unavailable")
                            recordingFile = null
                            result.success(file.absolutePath)
                        } catch (error: Exception) {
                            mediaRecorder?.release()
                            mediaRecorder = null
                            recordingFile?.delete()
                            recordingFile = null
                            result.error("recording_stop_failed", "Recording was too short or could not be finalized", null)
                        }
                    }
                    "playAudio" -> {
                        val audio = call.argument<ByteArray>("audio")
                        if (audio == null || audio.isEmpty()) {
                            result.error("invalid_audio", "Audio bytes are required", null)
                        } else {
                            try {
                                mediaPlayer?.release()
                                playbackFile?.delete()
                                val file = File(cacheDir, "rune-response-${System.currentTimeMillis()}.mp3")
                                file.writeBytes(audio)
                                playbackFile = file
                                val player = MediaPlayer()
                                mediaPlayer = player
                                player.setDataSource(file.absolutePath)
                                player.setOnCompletionListener {
                                    it.release()
                                    if (mediaPlayer === it) mediaPlayer = null
                                    file.delete()
                                    if (playbackFile == file) playbackFile = null
                                }
                                player.setOnErrorListener { mp, _, _ ->
                                    mp.release()
                                    if (mediaPlayer === mp) mediaPlayer = null
                                    file.delete()
                                    if (playbackFile == file) playbackFile = null
                                    true
                                }
                                player.setOnPreparedListener { it.start() }
                                player.prepareAsync()
                                result.success(true)
                            } catch (error: Exception) {
                                result.error("playback_failed", "Could not play RUNE audio", null)
                            }
                        }
                    }
                    "stopAudio" -> {
                        mediaPlayer?.let {
                            runCatching { if (it.isPlaying) it.stop() }
                            it.release()
                        }
                        mediaPlayer = null
                        playbackFile?.delete()
                        playbackFile = null
                        result.success(true)
                    }
                    "requestNotificationPermission" -> {
                        if (Build.VERSION.SDK_INT >= 33 &&
                            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 4202)
                            result.success(false)
                        } else {
                            result.success(true)
                        }
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

    override fun onDestroy() {
        runCatching { mediaRecorder?.stop() }
        mediaRecorder?.release()
        mediaRecorder = null
        mediaPlayer?.release()
        mediaPlayer = null
        playbackFile?.delete()
        playbackFile = null
        super.onDestroy()
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
