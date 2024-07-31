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

public class AccessInformationPointRightsMapper extends AbstractOIDCProtocolMapper
    implements OIDCAccessTokenMapper, OIDCIDTokenMapper, UserInfoTokenMapper {

    public static final String PROVIDER_ID = "oidc-access-information-point-rights-mapper";
	private static final String TOKEN_MAPPER_CATEGORY = "Access Information Point Rights Mapper";

    private static final List<ProviderConfigProperty> configProperties = new ArrayList<>();

    static {
        OIDCAttributeMapperHelper.addTokenClaimNameConfig(configProperties);
        OIDCAttributeMapperHelper.addIncludeInTokensConfig(configProperties, AccessInformationPointRightsMapper.class);
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
        String userId = userSession.getUser().getId();
        String serviceUrl = "http://aii-service.services.svc.cluster.local:8080/aii/users/" + userId + "/rights"; //TODO: Should come from configmap
        
        try {
			URL url = new URI(serviceUrl).toURL();
            HttpURLConnection con = (HttpURLConnection) url.openConnection();
            con.setRequestMethod("GET");

            int status = con.getResponseCode();
            if (status == 200) {
                BufferedReader in = new BufferedReader(new InputStreamReader(con.getInputStream()));
                String inputLine;
                StringBuilder content = new StringBuilder();
                while ((inputLine = in.readLine()) != null) {
                    content.append(inputLine);
                }
                in.close();

                // Parse the response
                ObjectMapper objectMapper = new ObjectMapper();
                JsonNode jsonNode = objectMapper.readTree(content.toString());

                Map<String, List<String>> claimsMap = new HashMap<>();

                for (JsonNode node : jsonNode) {
                    String claimKey = node.get("claim_key").asText();
                    String claimValue = node.get("claim_value").asText();
                    int projectId = node.get("project_id").asInt();
                    
                    // Add project ID to claim value
                    String fullClaimValue = claimValue + "_" + projectId;

                    claimsMap.computeIfAbsent(claimKey, k -> new ArrayList<>()).add(fullClaimValue);
                }

                // Set claims directly on the token
                // There are no single value claims, only lists
                for (Map.Entry<String, List<String>> entry : claimsMap.entrySet()) {
                    Object existingClaim = token.getOtherClaims().get(entry.getKey());
                    if (existingClaim != null && existingClaim instanceof List) {
                        // Append new values to existing list
                        List<String> existingList = (List<String>) existingClaim;
                        existingList.addAll(entry.getValue());
                        token.getOtherClaims().put(entry.getKey(), existingList);
                    } else if (existingClaim != null) {
                        // Convert existing single value to list and add new values
                        List<String> newList = new ArrayList<>();
                        newList.add(existingClaim.toString());
                        newList.addAll(entry.getValue());
                        token.getOtherClaims().put(entry.getKey(), newList);
                    } else {
                        // Add new values as list
                        token.getOtherClaims().put(entry.getKey(), entry.getValue());
                    }
                }
            } else {
                // Just log non-200 response keep the login flow going
                System.out.println("Error fetching rights: " + status);
            }

            con.disconnect();
        } catch (Exception e) {
            // Just log any exception to keep the login flow going (e.g. if the service is down and admin wants to login)
            e.printStackTrace();
        }
    }
}
