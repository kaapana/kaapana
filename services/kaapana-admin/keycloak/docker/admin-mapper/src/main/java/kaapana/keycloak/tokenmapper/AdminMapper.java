package kaapana.keycloak.tokenmapper;

import org.keycloak.models.ClientSessionContext;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.ProtocolMapperModel;
import org.keycloak.models.UserSessionModel;
import org.keycloak.protocol.oidc.mappers.AbstractOIDCProtocolMapper;
import org.keycloak.protocol.oidc.mappers.OIDCAccessTokenMapper;
import org.keycloak.protocol.oidc.mappers.OIDCAttributeMapperHelper;
import org.keycloak.protocol.oidc.mappers.OIDCIDTokenMapper;
import org.keycloak.protocol.oidc.mappers.UserInfoTokenMapper;
import org.keycloak.provider.ProviderConfigProperty;
import org.keycloak.representations.IDToken;
import org.keycloak.models.RoleModel;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URI;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

public class AdminMapper extends AbstractOIDCProtocolMapper
    implements OIDCAccessTokenMapper, OIDCIDTokenMapper, UserInfoTokenMapper {

    public static final String PROVIDER_ID = "oidc-admin-mapper";
	private static final String TOKEN_MAPPER_CATEGORY = "Admin Mapper";

    private static final List<ProviderConfigProperty> configProperties = new ArrayList<>();

    static {
        OIDCAttributeMapperHelper.addTokenClaimNameConfig(configProperties);
        OIDCAttributeMapperHelper.addIncludeInTokensConfig(configProperties, AdminMapper.class);
    }

    @Override
    public String getId() {
        return PROVIDER_ID;
    }

    @Override
    public String getDisplayCategory() {
        return TOKEN_MAPPER_CATEGORY;
    }

    @Override
    public String getDisplayType() {
        return "Access Information Point Rights Mapper";
    }

    @Override
    public String getHelpText() {
        return "Fetch rights from an external service and map them to token claims.";
    }

    @Override
    public List<ProviderConfigProperty> getConfigProperties() {
        return configProperties;
    }

    @Override
    protected void setClaim(IDToken token, ProtocolMapperModel mappingModel, UserSessionModel userSession, KeycloakSession keycloakSession, ClientSessionContext clientSessionCtx) {   
        try {
            RoleModel adminRole = userSession.getRealm().getRole("admin");
            RoleModel userRole = userSession.getRealm().getRole("user");
            // Set admin system admin rights for MinIO and OpenSearch
            if (userSession.getUser().hasRole(adminRole)) {
                // if user hasRole admin, add admin to opensearch claim
                Object existingClaim = token.getOtherClaims().get("opensearch");
                if (existingClaim != null && existingClaim instanceof List) {
                    // Append new value to existing list
                    List<String> existingList = (List<String>) existingClaim;
                    existingList.add("admin");
                    token.getOtherClaims().put("opensearch", existingList);
                } else if (existingClaim != null) {
                    // Convert existing single value to list and add new value
                    List<String> newList = new ArrayList<>();
                    newList.add(existingClaim.toString());
                    newList.add("admin");
                    token.getOtherClaims().put("opensearch", newList);
                } else {
                    // Add new value as list
                    List<String> newList = new ArrayList<>();
                    newList.add("admin");
                    token.getOtherClaims().put("opensearch", newList);
                }
                
                // if user hasRole admin, add consoleAdmin to policy claim
                existingClaim = token.getOtherClaims().get("policy");
                if (existingClaim != null && existingClaim instanceof List) {
                    // Append new value to existing list
                    List<String> existingList = (List<String>) existingClaim;
                    existingList.add("consoleAdmin");
                    token.getOtherClaims().put("policy", existingList);
                } else if (existingClaim != null) {
                    // Convert existing single value to list and add new value
                    List<String> newList = new ArrayList<>();
                    newList.add(existingClaim.toString());
                    newList.add("consoleAdmin");
                    token.getOtherClaims().put("policy", newList);
                } else {
                    // Add new value as list
                    List<String> newList = new ArrayList<>();
                    newList.add("consoleAdmin");
                    token.getOtherClaims().put("policy", newList);
                }
            }

            // Set kaapanaUser policy for MinIO
            else if (userSession.getUser().hasRole(userRole)) {              
                Object existingClaim = token.getOtherClaims().get("policy");  
                // if user hasRole user, add kaapanaUser to policy claim
                existingClaim = token.getOtherClaims().get("policy");
                if (existingClaim != null && existingClaim instanceof List) {
                    // Append new value to existing list
                    List<String> existingList = (List<String>) existingClaim;
                    existingList.add("kaapanaUser");
                    token.getOtherClaims().put("policy", existingList);
                } else if (existingClaim != null) {
                    // Convert existing single value to list and add new value
                    List<String> newList = new ArrayList<>();
                    newList.add(existingClaim.toString());
                    newList.add("kaapanaUser");
                    token.getOtherClaims().put("policy", newList);
                } else {
                    // Add new value as list
                    List<String> newList = new ArrayList<>();
                    newList.add("kaapanaUser");
                    token.getOtherClaims().put("policy", newList);
                }
            }

        } catch (Exception e) {
            // Just log any exception to keep the login flow going (e.g. if the service is down and admin wants to login)
            e.printStackTrace();
        }
    }
}
