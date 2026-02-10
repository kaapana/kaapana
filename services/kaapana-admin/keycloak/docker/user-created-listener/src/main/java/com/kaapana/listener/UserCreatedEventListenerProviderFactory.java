package com.kaapana.listener;

import org.keycloak.Config;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventListenerProviderFactory;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;

public class UserCreatedEventListenerProviderFactory
        implements EventListenerProviderFactory {

    public static final String ID = "user-created-http-listener";

    @Override
    public EventListenerProvider create(KeycloakSession session) {
        return new UserCreatedEventListenerProvider();
    }

    @Override
    public void init(Config.Scope config) {
        // optional
    }

    @Override
    public void postInit(KeycloakSessionFactory factory) {
        // optional
    }

    @Override
    public void close() {
        // optional
    }

    @Override
    public String getId() {
        return ID;
    }
}
