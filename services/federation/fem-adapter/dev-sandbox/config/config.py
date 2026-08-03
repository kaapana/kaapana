# Local dev-sandbox config.py for the real FEM-client, standing in for the
# restricted, per-federation {project}-fem-client-config repo EUCAIM has not
# handed us yet. Every value below is a locally-fabricated placeholder for
# the docker-compose sandbox in this directory -- none of it is a real
# EUCAIM credential, and ssl_active=False (plain, non-TLS AMQP) only makes
# sense against the local RabbitMQ container defined in docker-compose.yaml.

node_name = "kaapana-dev-node"

# guest/guest against the sandbox's own local RabbitMQ -- not a real broker.
node_user = "guest"
node_password = "guest"

central_server_ip = "rabbitmq"
ssl_central_server_port = 5672
central_rabbitmq_vhost = "/"

# Plain AMQP for local testing. A real FEM-orchestrator connection always
# uses ssl_active=True (AMQPS); see eucaim-fem-chart's config.py template
# for the production shape.
ssl_active = False
ssl_cafile_path = None
ssl_client_cert_path = None
ssl_client_keys_path = None

sandbox_path = "/sandbox"
data_path = "/data"

# fem-adapter's docker-compose service name/port, reachable from fem-client
# over the sandbox's shared docker network.
api_base_url = "http://fem-adapter:8090"

json_launcher = "/app/config/json_launcher.json"

# No extra %%PLACEHOLDER%% resolution beyond what run_tool.py already
# builds into argument_values (task_id, execution_id, user_id, ...).
task_info_vars = {}
