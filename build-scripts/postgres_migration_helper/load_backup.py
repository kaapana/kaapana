#!/usr/bin/env python3
import os
import yaml
import logging
from kubernetes import client, config
import datetime
from getpass import getpass

# Create a custom logger
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)

c_format = logging.Formatter("%(levelname)s - %(message)s")
c_handler.setFormatter(c_format)

# Add handlers to the logger
logger.addHandler(c_handler)

# Load Kubernetes configuration
config.load_kube_config()

# Create the Kubernetes API clients
core_v1 = client.CoreV1Api()

# Replace this with the path to your desired hostPath
host_path = "/home/kaapana/"

# Get the current timestamp
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S").replace("_", "-")

def restore_database(username, password, host, timestamp, database, namespace, foldername, version_tag, registry):
    backup_file = os.path.join(host_path, "backups", timestamp, f"{host}-backup.sql")
    if not os.path.isfile(backup_file):
        logger.info(f"No backup found for {host} at {timestamp}. Skipping restore.")
        return

    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S").replace("_", "-")

    # Create the restore Pod
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(name=f"{host}-restore-{timestamp}-current-time-is-{current_timestamp}"),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="restore-container",
                    image=f"{registry}/postgres-15.2-alpine:{version_tag}",
                    command=[
                        "sh", 
                        "-c",
                        # Switch to the postgres user
                        f"su - postgres <<'EOF'",
                        # Start the PostgreSQL server in the background
                        f"pg_ctl -D /var/lib/postgresql/data start && "
                        # Add a loop to wait for the postgres-server to be up
                        f"until pg_isready -U {username}; do echo 'Waiting for postgres-server to be up...'; sleep 2; done && "
                        f"psql -U {username} -W -d {database} -f /backup/{timestamp}/{host}-backup.sql",
                        f"EOF",
                    ],
                    env=[
                        client.V1EnvVar(
                            name="POSTGRES_USER",
                            value=username,
                        ),
                        client.V1EnvVar(
                            name="POSTGRES_PASSWORD",
                            value=password,
                        ),
                        client.V1EnvVar(
                            name="POSTGRES_DB",
                            value=database,
                        ),
                        client.V1EnvVar(
                            name="PGPASSWORD",
                            value=f"{password}",
                        ),
                    ],
                    volume_mounts=[
                        client.V1VolumeMount(
                            name="restore-volume",
                            mount_path=f"/backup/{timestamp}",
                        ),
                        client.V1VolumeMount(
                            name="data-volume",
                            mount_path=f"/var/lib/postgresql/data",
                        ),
                    ],
                ),
            ],
            volumes=[
                client.V1Volume(
                    name="restore-volume",
                    host_path=client.V1HostPathVolumeSource(
                        path=os.path.join(host_path, "backups", timestamp)
                    ),
                ),
                client.V1Volume(
                    name="data-volume",
                    host_path=client.V1HostPathVolumeSource(
                        path=os.path.join(host_path, foldername)
                    ),
                ),
            ],
            restart_policy="OnFailure",
        ),
    )

    core_v1.create_namespaced_pod(namespace=namespace, body=pod)

if __name__ == "__main__":

    # get current dir
    current_dir = os.path.dirname(os.path.realpath(__file__))

    # read backup list with credentials as relative path
    backup_list_path = os.path.join(current_dir, "backup_list.yaml")

    # read backup list with credentials
    with open(backup_list_path) as f:
        backup_list = yaml.load(f, Loader=yaml.FullLoader)

    # Check if multiple backups exist
    if len(os.listdir(os.path.join(host_path, "backups"))) > 1:
        # Ask user for the timestamp of the backup they want to restore
        timestamp = input("Enter the timestamp of the backup you want to restore: ")
    else:
        timestamp = os.listdir(os.path.join(host_path, "backups"))[0]

    # Ask for version tag
    version_tag = input("Enter the platform version tag:")

    # Read build-config.yaml
    build_config_path = os.path.join(current_dir, "..", "build-config.yaml")

    with open(build_config_path) as f:
        build_config = yaml.load(f, Loader=yaml.FullLoader)

    # Ask for registry if not found in build-config.yaml
    if "default_registry" not in build_config:
        registry = input("Enter the registry to use: ")
    else:
        registry = build_config["default_registry"]

    # Ask for registry username if not found in build-config.yaml
    if "registry_username" not in build_config:
        registry_username = input("Enter the registry username: ")
    else:
        registry_username = build_config["registry_username"]

    # Ask for registry password if not found in build-config.yaml
    if "registry_password" not in build_config:
        registry_password = getpass("Enter the registry password: ")
    else:
        registry_password = build_config["registry_password"]

    # docker login to registry
    os.system(f"docker login {registry} -u {registry_username} -p {registry_password}")

    # Get list of backups
    existing_backups = os.listdir(os.path.join(host_path, "backups", timestamp))

    # Get 
    for backup in backup_list:

        if backup["service"] + "-backup.sql" in existing_backups:
            logger.info(f"Backup found for {backup['service']}. Restoring...")
            # restore the database from the backup
            restore_database(backup["username"], backup["password"], backup["service"], timestamp, backup["database"], "default", backup["hostpath"], version_tag, registry)
