package com.dragonballls.jarvis.phone;

import android.app.Activity;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

public final class MainActivity extends Activity {
    private TextView status;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(32, 32, 32, 32);

        TextView title = new TextView(this);
        title.setText("Jarvis Phone Companion");
        title.setTextSize(24);
        root.addView(title, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        status = new TextView(this);
        root.addView(status, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        Button start = new Button(this);
        start.setText("Start Jarvis Companion");
        start.setOnClickListener(v -> startCompanion());
        root.addView(start);

        Button stop = new Button(this);
        stop.setText("Stop Jarvis Companion");
        stop.setOnClickListener(v -> stopService(new Intent(this, CompanionService.class)));
        root.addView(stop);

        Button notifications = new Button(this);
        notifications.setText("Enable notification access");
        notifications.setOnClickListener(v -> startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)));
        root.addView(notifications);

        Button accessibility = new Button(this);
        accessibility.setText("Enable Jarvis accessibility");
        accessibility.setOnClickListener(v -> startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)));
        root.addView(accessibility);

        TextView note = new TextView(this);
        note.setText("Jarvis keeps the phone's Android apps and data on the phone. The PC connection uses ADB forwarding to this phone-local service.");
        root.addView(note);

        setContentView(root);
        updateStatus();
    }

    private void startCompanion() {
        Intent service = new Intent(this, CompanionService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(service);
        } else {
            startService(service);
        }
        updateStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateStatus();
    }

    private void updateStatus() {
        if (status != null) {
            JarvisNotificationListener listener = JarvisNotificationListener.getInstance();
            JarvisAccessibilityService accessibility = JarvisAccessibilityService.getInstance();
            status.setText("Companion: " + (CompanionService.isRunning() ? "running" : "stopped")
                    + "\nNotifications: " + (listener != null ? "enabled" : "not enabled")
                    + "\nAccessibility: " + (accessibility != null ? "enabled" : "not enabled"));
        }
    }
}
