package com.kaapana.listener;

import com.kaapana.usersync.http.UserAssignmentClient;
import org.keycloak.events.Event;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventType;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;

public class FirstLoginEventListenerProvider implements EventListenerProvider {

    private static final String ASSIGNED_ATTR = "downstream-assigned";

    private final KeycloakSession session;

    public FirstLoginEventListenerProvider(KeycloakSession session) {
        this.session = session;
    }

    // ---- USER EVENTS (login etc.) ----
    @Override
    public void onEvent(Event event) {

        if (event.getType() != EventType.LOGIN) {
            return;
        }

        String userId = event.getUserId();
        String realmId = event.getRealmId();

        if (userId == null || realmId == null) {
            return;
        }

        RealmModel realm = session.realms().getRealm(realmId);
        if (realm == null) {
            return;
        }

        UserModel user = session.users().getUserById(realm, userId);
        if (user == null) {
            return;
        }

        // already processed?
        if (user.getFirstAttribute(ASSIGNED_ATTR) != null) {
            return;
        }

        try {
            UserAssignmentClient.assignUser(userId);
            user.setSingleAttribute(ASSIGNED_ATTR, "true");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // ---- ADMIN EVENTS (not used here) ----
    @Override
    public void onEvent(AdminEvent event, boolean includeRepresentation) {
        // no-op
    }

    @Override
    public void close() {}
}
