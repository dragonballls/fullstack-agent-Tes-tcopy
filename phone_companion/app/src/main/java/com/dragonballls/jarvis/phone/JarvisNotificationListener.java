package com.dragonballls.jarvis.phone;

import android.app.Notification;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.LinkedList;

public final class JarvisNotificationListener extends NotificationListenerService {
    private static volatile JarvisNotificationListener instance;
    private final LinkedList<JSONObject> recent = new LinkedList<>();
    private static final int MAX_ITEMS = 100;

    public static JarvisNotificationListener getInstance() {
        return instance;
    }

    @Override
    public void onListenerConnected() {
        instance = this;
        StatusBarNotification[] active = getActiveNotifications();
        if (active != null) {
            for (StatusBarNotification notification : active) {
                record(notification);
            }
        }
    }

    @Override
    public void onListenerDisconnected() {
        instance = null;
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        record(sbn);
    }

    public synchronized JSONArray snapshot() {
        JSONArray result = new JSONArray();
        for (JSONObject item : recent) {
            result.put(new JSONObject(item.toString()));
        }
        return result;
    }

    private synchronized void record(StatusBarNotification sbn) {
        if (sbn == null || sbn.getNotification() == null) return;
        Notification notification = sbn.getNotification();
        CharSequence title = notification.extras != null ? notification.extras.getCharSequence(Notification.EXTRA_TITLE) : null;
        CharSequence text = notification.extras != null ? notification.extras.getCharSequence(Notification.EXTRA_TEXT) : null;
        JSONObject item = new JSONObject()
                .put("package", sbn.getPackageName())
                .put("title", title == null ? "" : title.toString())
                .put("text", text == null ? "" : text.toString())
                .put("id", sbn.getId())
                .put("posted_ms", sbn.getPostTime());
        recent.removeIf(existing -> existing.optInt("id", -1) == sbn.getId() && existing.optString("package").equals(sbn.getPackageName()));
        recent.addFirst(item);
        while (recent.size() > MAX_ITEMS) {
            recent.removeLast();
        }
    }
}
