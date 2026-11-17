package com.draken.rune_mobile

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityWindowInfo

class RuneAccessibilityService : AccessibilityService() {
    companion object {
        @Volatile var instance: RuneAccessibilityService? = null
            private set
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}
    override fun onDestroy() {
        if (instance === this) instance = null
        super.onDestroy()
    }

    fun observeUi(): Map<String, Any?> {
        val root = rootInActiveWindow ?: return mapOf("available" to false, "reason" to "no_active_window")
        val packageName = root.packageName?.toString()
        val windowCount = windows?.size ?: 0
        val nodes = mutableListOf<Map<String, Any?>>()
        try {
            collect(root, nodes, 0)
        } finally {
            root.recycle()
        }
        return mapOf(
            "available" to true,
            "packageName" to packageName,
            "windowCount" to windowCount,
            "nodes" to nodes.take(250)
        )
    }

    private fun collect(node: AccessibilityNodeInfo, output: MutableList<Map<String, Any?>>, depth: Int) {
        if (depth > 18 || output.size >= 250) return
        val bounds = Rect()
        node.getBoundsInScreen(bounds)
        val password = node.isPassword
        val text = if (password) null else node.text?.toString()?.take(300)
        val description = if (password) null else node.contentDescription?.toString()?.take(300)
        if (!text.isNullOrBlank() || !description.isNullOrBlank() || node.isClickable || node.isScrollable) {
            output.add(mapOf(
                "text" to text,
                "description" to description,
                "className" to node.className?.toString(),
                "clickable" to node.isClickable,
                "scrollable" to node.isScrollable,
                "editable" to node.isEditable,
                "password" to password,
                "bounds" to mapOf("left" to bounds.left, "top" to bounds.top,
                    "right" to bounds.right, "bottom" to bounds.bottom),
                "depth" to depth
            ))
        }
        for (i in 0 until node.childCount) {
            node.getChild(i)?.let { child ->
                collect(child, output, depth + 1)
                child.recycle()
            }
        }
    }

    fun tap(x: Float, y: Float): Boolean {
        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 70))
            .build()
        return dispatchGesture(gesture, null, null)
    }

    fun scroll(direction: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val target = try { findScrollable(root) } finally { root.recycle() } ?: return false
        val action = if (direction == "up") AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD
                     else AccessibilityNodeInfo.ACTION_SCROLL_FORWARD
        return try { target.performAction(action) } finally { target.recycle() }
    }

    private fun findScrollable(node: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        if (node.isScrollable) return AccessibilityNodeInfo.obtain(node)
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            val found = findScrollable(child)
            child.recycle()
            if (found != null) return found
        }
        return null
    }

    fun typeText(value: String): Boolean {
        if (value.length > 4000) return false
        val root = rootInActiveWindow ?: return false
        val target = try { findFocusedEditable(root) } finally { root.recycle() } ?: return false
        val args = Bundle().apply {
            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, value)
        }
        return try { target.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args) }
               finally { target.recycle() }
    }

    private fun findFocusedEditable(node: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        if (node.isFocused && node.isEditable && !node.isPassword) {
            return AccessibilityNodeInfo.obtain(node)
        }
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            val found = findFocusedEditable(child)
            child.recycle()
            if (found != null) return found
        }
        return null
    }
}
