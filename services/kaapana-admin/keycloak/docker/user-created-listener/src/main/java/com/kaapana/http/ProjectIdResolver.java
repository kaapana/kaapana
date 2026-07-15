package com.kaapana.usersync.http;

import com.kaapana.usersync.config.UserSyncConfig;
import com.kaapana.usersync.config.UserSyncConfigLoader;
import com.kaapana.usersync.http.ProjectDto;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Arrays;
import java.util.concurrent.atomic.AtomicReference;

public final class ProjectIdResolver {

    private static final AtomicReference<String> PROJECT_ID_CACHE =
            new AtomicReference<>();

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private ProjectIdResolver() {}

    public static String getProjectId() {
        String cached = PROJECT_ID_CACHE.get();
        if (cached != null) {
            return cached;
        }

        synchronized (ProjectIdResolver.class) {
            cached = PROJECT_ID_CACHE.get();
            if (cached == null) {
                cached = resolve();
                PROJECT_ID_CACHE.set(cached);
            }
            return cached;
        }
    }

    private static String resolve() {
        try {
            UserSyncConfig cfg = UserSyncConfigLoader.getConfig();

            URL url = new URL("http://aii-service.services.svc:8080/projects");
            HttpURLConnection conn =
                (HttpURLConnection) url.openConnection();

            conn.setRequestMethod("GET");
            conn.setConnectTimeout(2000);
            conn.setReadTimeout(2000);

            ProjectDto[] projects =
                MAPPER.readValue(conn.getInputStream(), ProjectDto[].class);

            conn.disconnect();

            return Arrays.stream(projects)
                .filter(p -> cfg.project_name.equals(p.name))
                .findFirst()
                .orElseThrow(() -> new IllegalStateException(
                    "Project not found: " + cfg.project_name
                ))
                .id;

        } catch (Exception e) {
            throw new RuntimeException("Failed to resolve project ID", e);
        }
    }
}
