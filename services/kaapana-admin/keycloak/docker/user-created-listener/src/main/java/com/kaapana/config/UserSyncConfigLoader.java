package com.kaapana.usersync.config;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.File;
import java.util.concurrent.atomic.AtomicReference;

public final class UserSyncConfigLoader {

    private static final AtomicReference<UserSyncConfig> CACHE =
            new AtomicReference<>();

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private UserSyncConfigLoader() {}

    public static UserSyncConfig getConfig() {
        UserSyncConfig cfg = CACHE.get();
        if (cfg != null) {
            return cfg;
        }

        synchronized (UserSyncConfigLoader.class) {
            cfg = CACHE.get();
            if (cfg == null) {
                cfg = load();
                CACHE.set(cfg);
            }
            return cfg;
        }
    }

    private static UserSyncConfig load() {
        try {
            String path = System.getenv("USER_SYNC_CONFIG_PATH");
            if (path == null || path.isBlank()) {
                throw new IllegalStateException(
                    "USER_SYNC_CONFIG_PATH environment variable not set"
                );
            }

            File file = new File(path);
            if (!file.exists()) {
                throw new IllegalStateException(
                    "Config file does not exist: " + path
                );
            }

            return MAPPER.readValue(file, UserSyncConfig.class);

        } catch (Exception e) {
            throw new RuntimeException("Failed to load user sync config", e);
        }
    }
}
