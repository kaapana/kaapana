package com.kaapana.listener;

import org.keycloak.Config;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventListenerProviderFactory;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;

public class FirstLoginEventListenerProviderFactory
        implements EventListenerProviderFactory {

    public static final String ID = "first-login-listener";

    @Override
    public EventListenerProvider create(KeycloakSession session) {
        return new FirstLoginEventListenerProvider(session);
    }

    @Override
    public void init(Config.Scope config) {}

    @Override
    public void postInit(KeycloakSessionFactory factory) {}

    @Override
    public void close() {}

    @Override
    public String getId() {
        return ID;
    }
}
