package com.kaapana.listener;

import com.kaapana.usersync.http.UserAssignmentClient;

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
            UserAssignmentClient.assignUser(event.getUserId());
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

            UserAssignmentClient.assignUser(userId);
        }
    }

    @Override
    public void close() {
        // no-op
    }
}
