package com.draken.rune_mobile

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.KeyStore
import java.util.concurrent.Executors
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class RuneOperatorService : Service() {
    companion object {
        const val ACTION_START = "com.draken.rune_mobile.OPERATOR_START"
        const val ACTION_STOP = "com.draken.rune_mobile.OPERATOR_STOP"
        private const val CHANNEL = "rune_device_operator"
        private const val NOTIFICATION_ID = 4201
        private const val KEY_ALIAS = "rune_device_operator_v1"
        private const val PREFS = "rune_operator_encrypted"
    }

    @Volatile private var running = false
    private val executor = Executors.newSingleThreadExecutor()
    private var lastHeartbeat = 0L
    private var backendUrl = ""
    private var deviceId = ""
    private var deviceToken = ""

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            running = false
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            return START_NOT_STICKY
        }
        if (intent?.action == ACTION_START) {
            backendUrl = intent.getStringExtra("backendUrl") ?: ""
            deviceId = intent.getStringExtra("deviceId") ?: ""
            deviceToken = intent.getStringExtra("deviceToken") ?: ""
            val parsedBackend = runCatching { URL(backendUrl) }.getOrNull()
            if (parsedBackend == null ||
                (parsedBackend.protocol != "https" && parsedBackend.host !in setOf("localhost", "127.0.0.1"))) {
                stopSelf()
                return START_NOT_STICKY
            }
            if (backendUrl.isBlank() || deviceId.isBlank() || deviceToken.isBlank()) {
                stopSelf()
                return START_NOT_STICKY
            }
            saveCredentials()
        } else {
            loadCredentials()
        }
        if (backendUrl.isBlank() || deviceId.isBlank() || deviceToken.isBlank()) {
            stopSelf()
            return START_NOT_STICKY
        }
        startOperatorNotification()
        if (!running) {
            running = true
            executor.execute { operatorLoop() }
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        running = false
        executor.shutdownNow()
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL, "RUNE Device Operator",
                NotificationManager.IMPORTANCE_LOW).apply {
                description = "Shows when RUNE is available to carry out approved device tasks."
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun startOperatorNotification() {
        val launch = packageManager.getLaunchIntentForPackage(packageName)
        val pending = launch?.let {
            PendingIntent.getActivity(this, 0, it,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        }
        val notification = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL)
        } else {
            @Suppress("DEPRECATION") Notification.Builder(this)
        }.setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("RUNE device operator active")
            .setContentText("Waiting for approved device tasks")
            .setOngoing(true)
            .setContentIntent(pending)
            .build()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun operatorLoop() {
        while (running) {
            try {
                val now = System.currentTimeMillis()
                if (now - lastHeartbeat > 20000L) {
                    val capabilities = JSONArray().put("app.list").put("app.launch")
                    if (RuneAccessibilityService.instance != null) {
                        capabilities.put("ui.observe").put("ui.interact")
                    }
                    post("/v1/devices/$deviceId/heartbeat",
                        JSONObject().put("status", "online")
                            .put("app_version", "0.2.0")
                            .put("capabilities", capabilities))
                    lastHeartbeat = now
                }
                val response = request("GET", "/v1/devices/$deviceId/tasks/next", null)
                val task = response.optJSONObject("task")
                if (task != null) executeTask(task)
            } catch (_: Exception) {
                // Retry after a short delay. A network error never marks a task successful.
            }
            try { Thread.sleep(3500L) } catch (_: InterruptedException) { break }
        }
    }

    private fun executeTask(task: JSONObject) {
        val taskId = task.optString("id")
        val capability = task.optString("capability")
        val args = task.optJSONObject("arguments") ?: JSONObject()
        if (taskId.isBlank()) return
        try {
            when (capability) {
                "app.list" -> {
                    val apps = JSONArray()
                    val intent = Intent(Intent.ACTION_MAIN, null).addCategory(Intent.CATEGORY_LAUNCHER)
                    packageManager.queryIntentActivities(intent, PackageManager.MATCH_ALL)
                        .distinctBy { it.activityInfo.packageName }
                        .forEach { info ->
                            apps.put(JSONObject().put("packageName", info.activityInfo.packageName)
                                .put("appName", info.loadLabel(packageManager).toString()))
                        }
                    submit(taskId, "completed", JSONObject().put("apps", apps),
                        JSONObject().put("source", "android_package_manager").put("count", apps.length()))
                }
                "app.launch" -> {
                    val packageName = args.optString("packageName", args.optString("package_name"))
                    val launch = packageManager.getLaunchIntentForPackage(packageName)
                    if (launch == null) {
                        submit(taskId, "failed", JSONObject(), JSONObject().put("reason", "launch_intent_unavailable"), "app_launch_unavailable")
                    } else {
                        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        startActivity(launch)
                        Thread.sleep(700L)
                        val observation = RuneAccessibilityService.instance?.observeUi()
                        val active = observation?.get("packageName")?.toString()
                        val confirmed = active == packageName
                        submit(taskId, if (confirmed) "completed" else "uncertain",
                            JSONObject().put("launched", true).put("active_package", active ?: JSONObject.NULL),
                            JSONObject().put("source", "accessibility_active_window")
                                .put("expected_package", packageName)
                                .put("observed_package", active ?: JSONObject.NULL)
                                .put("confirmed", confirmed))
                    }
                }
                "ui.observe" -> {
                    val observation = RuneAccessibilityService.instance?.observeUi()
                    if (observation == null || observation["available"] != true) {
                        submit(taskId, "blocked", JSONObject(), JSONObject().put("reason", "accessibility_unavailable"), "accessibility_unavailable")
                    } else {
                        val output = JSONObject(observation)
                        submit(taskId, "completed", output,
                            JSONObject().put("source", "android_accessibility_service")
                                .put("package", observation["packageName"]?.toString() ?: JSONObject.NULL))
                    }
                }
                "ui.interact" -> executeUiInteraction(taskId, args)
                else -> submit(taskId, "blocked", JSONObject(),
                    JSONObject().put("reason", "capability_not_implemented"), "capability_not_implemented")
            }
        } catch (_: Exception) {
            submit(taskId, "uncertain", JSONObject(),
                JSONObject().put("reason", "execution_or_verification_failed"), "device_execution_uncertain")
        }
    }

    private fun executeUiInteraction(taskId: String, args: JSONObject) {
        val service = RuneAccessibilityService.instance
        if (service == null) {
            submit(taskId, "blocked", JSONObject(), JSONObject().put("reason", "accessibility_unavailable"), "accessibility_unavailable")
            return
        }
        val action = args.optString("action")
        val accepted = when (action) {
            "tap" -> service.tap(args.optDouble("x").toFloat(), args.optDouble("y").toFloat())
            "scroll" -> service.scroll(args.optString("direction", "down"))
            "type" -> service.typeText(args.optString("text"))
            else -> false
        }
        val observation = if (accepted) JSONObject(service.observeUi()) else JSONObject()
        submit(taskId, if (accepted) "uncertain" else "failed",
            JSONObject().put("action", action).put("accepted_by_android", accepted).put("observation", observation),
            JSONObject().put("source", "android_accessibility_service")
                .put("action_dispatched", accepted)
                .put("note", "Dispatch acceptance is not proof of the intended outcome."),
            if (accepted) null else "action_dispatch_failed")
    }

    private fun submit(taskId: String, status: String, output: JSONObject,
                       evidence: JSONObject, errorCode: String? = null) {
        val body = JSONObject().put("status", status).put("output", output)
            .put("evidence", evidence).put("error_code", errorCode ?: JSONObject.NULL)
        post("/v1/devices/$deviceId/tasks/$taskId/result", body)
    }

    private fun post(path: String, body: JSONObject) {
        request("POST", path, body)
    }

    private fun request(method: String, path: String, body: JSONObject?): JSONObject {
        val connection = URL(backendUrl.trimEnd('/') + path).openConnection() as HttpURLConnection
        connection.requestMethod = method
        connection.connectTimeout = 8000
        connection.readTimeout = 12000
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Content-Type", "application/json")
        connection.setRequestProperty("X-RUNE-Device-Token", deviceToken)
        if (body != null) {
            connection.doOutput = true
            connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
        }
        val code = connection.responseCode
        val stream = if (code in 200..299) connection.inputStream else connection.errorStream
        val text = stream?.bufferedReader()?.use { it.readText() } ?: "{}"
        connection.disconnect()
        if (code !in 200..299) throw IllegalStateException("RUNE backend HTTP $code")
        return JSONObject(text)
    }

    private fun saveCredentials() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        prefs.edit().putString("backend", encrypt(backendUrl))
            .putString("device", encrypt(deviceId))
            .putString("token", encrypt(deviceToken)).apply()
    }

    private fun loadCredentials() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        backendUrl = decrypt(prefs.getString("backend", null))
        deviceId = decrypt(prefs.getString("device", null))
        deviceToken = decrypt(prefs.getString("token", null))
    }

    private fun secretKey(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = store.getKey(KEY_ALIAS, null) as? SecretKey
        if (existing != null) return existing
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder(KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setRandomizedEncryptionRequired(true).build())
        return generator.generateKey()
    }

    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val encrypted = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        return Base64.encodeToString(cipher.iv + encrypted, Base64.NO_WRAP)
    }

    private fun decrypt(value: String?): String {
        if (value.isNullOrBlank()) return ""
        return try {
            val packed = Base64.decode(value, Base64.NO_WRAP)
            val iv = packed.copyOfRange(0, 12)
            val ciphertext = packed.copyOfRange(12, packed.size)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, iv))
            String(cipher.doFinal(ciphertext), Charsets.UTF_8)
        } catch (_: Exception) { "" }
    }
}
