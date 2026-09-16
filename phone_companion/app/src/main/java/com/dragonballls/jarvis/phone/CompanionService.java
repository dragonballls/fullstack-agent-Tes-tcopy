package com.dragonballls.jarvis.phone;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.os.IBinder;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

public final class CompanionService extends Service {
    private static final int PORT = 18765;
    private static final String CHANNEL = "jarvis_companion";
    private static volatile boolean running;
    private ServerSocket server;
    private Thread acceptThread;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        startForeground(18765, buildNotification());
        startServer();
    }

    public static boolean isRunning() {
        return running;
    }

    private Notification buildNotification() {
        Intent launch = new Intent(this, MainActivity.class);
        PendingIntent pending = PendingIntent.getActivity(this, 0, launch, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this, CHANNEL)
                .setContentTitle("Jarvis Phone Companion")
                .setContentText("Local device bridge active")
                .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
                .setContentIntent(pending)
                .setOngoing(true)
                .build();
    }

    private void createNotificationChannel() {
        NotificationChannel channel = new NotificationChannel(CHANNEL, "Jarvis Phone Companion", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Local companion status");
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager != null) manager.createNotificationChannel(channel);
    }

    private void startServer() {
        if (running) return;
        acceptThread = new Thread(() -> {
            try (ServerSocket socket = new ServerSocket(PORT, 16, java.net.InetAddress.getLoopbackAddress())) {
                server = socket;
                running = true;
                while (!Thread.currentThread().isInterrupted()) {
                    handle(socket.accept());
                }
            } catch (IOException ignored) {
                // Service shutdown or socket closure.
            } finally {
                running = false;
            }
        }, "JarvisCompanionServer");
        acceptThread.start();
    }

    private void handle(Socket socket) {
        try (Socket client = socket;
             BufferedReader reader = new BufferedReader(new InputStreamReader(client.getInputStream(), StandardCharsets.UTF_8));
             OutputStream output = client.getOutputStream()) {
            String requestLine = reader.readLine();
            if (requestLine == null) return;
            String[] parts = requestLine.split(" ");
            if (parts.length < 2) {
                write(output, 400, JsonUtil.error("INVALID", "malformed request"));
                return;
            }
            int contentLength = 0;
            String header;
            while ((header = reader.readLine()) != null && !header.isEmpty()) {
                String lower = header.toLowerCase(java.util.Locale.ROOT);
                if (lower.startsWith("content-length:")) {
                    try { contentLength = Math.min(Integer.parseInt(header.substring(15).trim()), 8192); } catch (NumberFormatException ignored) { contentLength = 0; }
                }
            }
            char[] body = new char[contentLength];
            int offset = 0;
            while (offset < contentLength) {
                int read = reader.read(body, offset, contentLength - offset);
                if (read < 0) break;
                offset += read;
            }
            JSONObject payload = contentLength > 0 ? new JSONObject(new String(body, 0, offset)) : new JSONObject();
            String response;
            if ("GET".equals(parts[0]) && "/health".equals(parts[1])) {
                response = JsonUtil.ok(new JSONObject()
                        .put("service", "jarvis-phone-companion")
                        .put("version", 1)
                        .put("running", running)
                        .put("notifications", JarvisNotificationListener.getInstance() != null)
                        .put("accessibility", JarvisAccessibilityService.getInstance() != null));
                write(output, 200, response);
                return;
            }
            if ("GET".equals(parts[0]) && "/notifications".equals(parts[1])) {
                JarvisNotificationListener listener = JarvisNotificationListener.getInstance();
                if (listener == null) {
                    write(output, 503, JsonUtil.error("UNAVAILABLE", "notification listener is not enabled"));
                    return;
                }
                response = JsonUtil.ok(new JSONObject().put("notifications", listener.snapshot()));
                write(output, 200, response);
                return;
            }
            if ("POST".equals(parts[0]) && "/action".equals(parts[1])) {
                response = handleAction(payload);
                write(output, response.startsWith("{\"ok\":true") ? 200 : 400, response);
                return;
            }
            write(output, 404, JsonUtil.error("NOT_FOUND", "endpoint not found"));
        } catch (Exception exc) {
            try {
                OutputStream ignored = socket.getOutputStream();
                write(ignored, 500, JsonUtil.error("ERROR", exc.getMessage() == null ? "request failed" : exc.getMessage()));
            } catch (Exception ignoredAgain) {}
        }
    }

    private String handleAction(JSONObject payload) {
        String action = payload.optString("action", "").trim();
        if (action.isEmpty()) return JsonUtil.error("INVALID", "action is required");
        JarvisAccessibilityService accessibility = JarvisAccessibilityService.getInstance();
        try {
            if ("home".equals(action)) {
                if (accessibility == null || !accessibility.performGlobalAction(AccessibilityServiceAction.HOME)) return JsonUtil.error("UNAVAILABLE", "accessibility action unavailable");
                return JsonUtil.ok(new JSONObject().put("action", action));
            }
            if ("back".equals(action)) {
                if (accessibility == null || !accessibility.performGlobalAction(AccessibilityServiceAction.BACK)) return JsonUtil.error("UNAVAILABLE", "accessibility action unavailable");
                return JsonUtil.ok(new JSONObject().put("action", action));
            }
            if ("click_text".equals(action)) {
                String text = payload.optString("text", "").trim();
                if (text.isEmpty()) return JsonUtil.error("INVALID", "text is required");
                if (accessibility == null || !accessibility.clickText(text)) return JsonUtil.error("NOT_FOUND", "no clickable matching text found");
                return JsonUtil.ok(new JSONObject().put("action", action).put("text", text));
            }
            return JsonUtil.error("UNSUPPORTED", "unsupported companion action");
        } catch (JSONException exc) {
            return JsonUtil.error("ERROR", "unable to build companion action response");
        }
    }

    private void write(OutputStream output, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        String reason = status == 200 ? "OK" : status == 400 ? "Bad Request" : status == 404 ? "Not Found" : status == 503 ? "Service Unavailable" : "Internal Server Error";
        String headers = "HTTP/1.1 " + status + " " + reason + "\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: " + bytes.length + "\r\nConnection: close\r\n\r\n";
        output.write(headers.getBytes(StandardCharsets.UTF_8));
        output.write(bytes);
        output.flush();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        running = false;
        if (acceptThread != null) acceptThread.interrupt();
        try { if (server != null) server.close(); } catch (IOException ignored) {}
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    static final class AccessibilityServiceAction {
        static final int HOME = 2;
        static final int BACK = 1;
        private AccessibilityServiceAction() {}
    }
}
