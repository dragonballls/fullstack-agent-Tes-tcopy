package com.dragonballls.jarvis.phone;

import org.json.JSONException;
import org.json.JSONObject;

/** Small helpers around JSONObject so the companion has no third-party dependencies. */
final class JsonUtil {
    private JsonUtil() {}

    static String error(String code, String message) {
        try {
            return new JSONObject()
                    .put("ok", false)
                    .put("code", code)
                    .put("message", message)
                    .toString();
        } catch (JSONException exc) {
            throw new IllegalStateException("Unable to build companion JSON error response", exc);
        }
    }

    static String ok(JSONObject payload) {
        try {
            payload.put("ok", true);
            return payload.toString();
        } catch (JSONException exc) {
            throw new IllegalStateException("Unable to build companion JSON response", exc);
        }
    }
}
