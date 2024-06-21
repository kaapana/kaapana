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

public class AccessInformationPointProjectsMapper extends AbstractOIDCProtocolMapper
    implements OIDCAccessTokenMapper, OIDCIDTokenMapper, UserInfoTokenMapper {

    public static final String PROVIDER_ID = "oidc-access-information-point-projects-mapper";
    private static final String TOKEN_MAPPER_CATEGORY = "Access Information Point Projects Mapper";

    private static final List<ProviderConfigProperty> configProperties = new ArrayList<>();

    static {
        OIDCAttributeMapperHelper.addTokenClaimNameConfig(configProperties);
        OIDCAttributeMapperHelper.addIncludeInTokensConfig(configProperties, AccessInformationPointProjectsMapper.class);
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
        return "Access Information Point Projects Mapper";
    }

    @Override
    public String getHelpText() {
        return "Fetch projects and roles the user is in from an external service and map them to token claims.";
    }

    @Override
    public List<ProviderConfigProperty> getConfigProperties() {
        return configProperties;
    }

    @Override
    protected void setClaim(IDToken token, ProtocolMapperModel mappingModel, UserSessionModel userSession, KeycloakSession keycloakSession, ClientSessionContext clientSessionCtx) {
        String userId = userSession.getUser().getId();
        String serviceUrl = "http://aii-service.services.svc.cluster.local:8080/aii/users/" + userId + "/projects"; //TODO: Should come from configmap

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

                List<Map<String, Object>> projects = new ArrayList<>();

                for (JsonNode node : jsonNode) {
                    Map<String, Object> project = new HashMap<>();
                    project.put("id", node.get("id").asInt());
                    project.put("name", node.get("name").asText());
                    project.put("description", node.get("description").asText());
                    project.put("role_id", node.get("role_id").asInt());
                    project.put("role_name", node.get("role_name").asText());
                    projects.add(project);
                }

                // Set projects claim
                token.getOtherClaims().put("projects", projects);
            } else {
                // Just log non-200 response keep the login flow going
                System.out.println("Error fetching projects: " + status);
            }

            con.disconnect();
        } catch (Exception e) {
            // Just log any exception to keep the login flow going (e.g. if the service is down and admin wants to login)
            e.printStackTrace();
        }
    }
}
