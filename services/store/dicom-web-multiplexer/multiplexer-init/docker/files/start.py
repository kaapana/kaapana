from kaapanapy.settings import KaapanaSettings
from kubernetes import client, config
from pydantic_settings import BaseSettings

# Load the kubeconfig
config.load_incluster_config()  # Use config.load_incluster_config() if running inside a pod

    

SERVICES_NAMESPACE = KaapanaSettings.services_namespace

deployment_name = "airflow-scheduler"
env_var_name = "DICOM_WEB_SERVICE"
env_var_value = "dicom-web-multiplexer"

# Get the current deployment
apps_v1 = client.AppsV1Api()
deployment = apps_v1.read_namespaced_deployment(deployment_name, SERVICES_NAMESPACE)

# Update the environment variable
env_var_found = False
for container in deployment.spec.template.spec.containers:
    for env in container.env:
        if env.name == env_var_name:
            env.value = env_var_value  # Update the value
            env_var_found = True
            break

if not env_var_found:
    # If the env var doesn't exist, you can add it
    deployment.spec.template.spec.containers[0].env.append(client.V1EnvVar(name=env_var_name, value=env_var_value))

# Update the deployment
apps_v1.patch_namespaced_deployment(deployment_name, SERVICES_NAMESPACE, deployment)

print(f"Updated {env_var_name} to {env_var_value} in deployment {deployment_name}")
