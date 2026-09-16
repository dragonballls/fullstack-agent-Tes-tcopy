package com.dragonballls.jarvis.phone;

import org.json.JSONObject;

/** Small helpers around JSONObject so the companion has no third-party dependencies. */
final class JsonUtil {
    private JsonUtil() {}

    static String error(String code, String message) {
        return new JSONObject()
                .put("ok", false)
                .put("code", code)
                .put("message", message)
                .toString();
    }

    static String ok(JSONObject payload) {
        payload.put("ok", true);
        return payload.toString();
    }
}
