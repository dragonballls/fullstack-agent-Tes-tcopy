package com.dragonballls.jarvis.phone;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityNodeInfo;

public final class JarvisAccessibilityService extends AccessibilityService {
    private static volatile JarvisAccessibilityService instance;

    public static JarvisAccessibilityService getInstance() {
        return instance;
    }

    @Override
    protected void onServiceConnected() {
        instance = this;
    }

    public boolean clickText(String text) {
        if (text == null || text.trim().isEmpty()) return false;
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return false;
        try {
            java.util.List<AccessibilityNodeInfo> nodes = root.findAccessibilityNodeInfosByText(text);
            for (AccessibilityNodeInfo node : nodes) {
                if (node.isClickable() && node.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                    return true;
                }
                AccessibilityNodeInfo parent = node.getParent();
                if (parent != null && parent.isClickable() && parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                    return true;
                }
            }
            return false;
        } finally {
            root.recycle();
        }
    }

    @Override
    public void onAccessibilityEvent(android.view.accessibility.AccessibilityEvent event) {
        // State is queried on demand; no permanent UI mirror is stored here.
    }

    @Override
    public void onInterrupt() {
        instance = null;
    }

    @Override
    public void onDestroy() {
        instance = null;
        super.onDestroy();
    }
}
