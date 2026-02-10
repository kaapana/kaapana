package com.example.keycloak.listener;

import org.keycloak.events.Event;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventType;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.events.admin.OperationType;
import org.keycloak.events.admin.ResourceType;

import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class UserCreatedEventListenerProvider implements EventListenerProvider {

    /* Self-registration */
    @Override
    public void onEvent(Event event) {
        if (event.getType() == EventType.REGISTER) {
            sendDummyRequest(event.getUserId());
        }
    }

    /* Admin-created users */
    @Override
    public void onEvent(AdminEvent adminEvent, boolean includeRepresentation) {
        if (adminEvent.getResourceType() == ResourceType.USER &&
            adminEvent.getOperationType() == OperationType.CREATE) {

            // Extract userId from resource path: "users/{id}"
            String resourcePath = adminEvent.getResourcePath();
            String userId = resourcePath.substring(resourcePath.lastIndexOf('/') + 1);

            sendDummyRequest(userId);
        }
    }

    private void getDefaultProject() {
        URL url = new URL("http://project-service.services.svc:80/v1/projects");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(2000);
        conn.setReadTimeout(2000);
        conn.getResponseCode();
        conn.disconnect();
    }

    private void sendDummyRequest(String userId) {
        try {
            URL url = new URL("http://notification-service.services.svc:80/v1/4beec505-9c9b-44b6-997c-ecddc65569aa");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(2000);
            conn.setReadTimeout(2000);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");

            String payload = """
            {
            "topic": "Keycloak",
            "title": "User created",
            "description": "User %s created",
            "icon": "mdi-information"
            }
            """.formatted(userId);
            conn.getOutputStream().write(payload.getBytes(StandardCharsets.UTF_8));

            conn.getResponseCode();
            conn.disconnect();
        } catch (Exception e) {
            e.printStackTrace(); // replace with Keycloak logger in prod
        }
    }

    @Override
    public void close() {
        // no-op
    }
}
