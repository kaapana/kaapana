package com.kaapana.usersync.http;

import com.kaapana.usersync.config.UserSyncConfig;
import com.kaapana.usersync.config.UserSyncConfigLoader;

import java.net.HttpURLConnection;
import java.net.URL;

public final class UserAssignmentClient {

    private UserAssignmentClient() {}

    public static void assignUser(String userId) {
        try {
            UserSyncConfig cfg = UserSyncConfigLoader.getConfig();
            if (cfg == null) {
                return;
            }

            String url = String.format(
                "http://aii-service.services.svc/projects/%s/role/%s/user/%s",
                cfg.project_id,
                cfg.role_name,
                userId
            );

            HttpURLConnection conn =
                (HttpURLConnection) new URL(url).openConnection();

            conn.setRequestMethod("POST");
            conn.setConnectTimeout(2000);
            conn.setReadTimeout(2000);

            conn.getResponseCode();
            conn.disconnect();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
