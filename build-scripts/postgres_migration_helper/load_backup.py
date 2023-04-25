#!/usr/bin/env python3
import os
import yaml
import logging
from kubernetes import client, config
import datetime

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
host_path = "/home/kaapana/backups"

# Get the current timestamp
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S").replace("_", "-")

def restore_database(username, password, host, timestamp, database):
    backup_file = os.path.join(host_path, timestamp, f"{host}-backup.sql")
    if not os.path.isfile(backup_file):
        logger.info(f"No backup found for {host} at {timestamp}. Skipping restore.")
        return

    # Create the restore Pod
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(name=f"{host}-restore-{timestamp}-current-time-is-{timestamp}"),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="restore-container",
                    image="postgres:latest",
                    command=[
                        "sh",
                        "-c",
                        f"psql -U {username} -W -h {host} -d {database} -f /backup/{timestamp}/{host}-backup.sql",
                    ],
                    env=[
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
                    ],
                ),
            ],
            volumes=[
                client.V1Volume(
                    name="restore-volume",
                    host_path=client.V1HostPathVolumeSource(
                        path=os.path.join(host_path, timestamp)
                    ),
                ),
            ],
            restart_policy="OnFailure",
        ),
    )

    core_v1.create_namespaced_pod(namespace="services", body=pod)

if __name__ == "__main__":

    # get current dir
    current_dir = os.path.dirname(os.path.realpath(__file__))

    # read backup list with credentials as relative path
    backup_list_path = os.path.join(current_dir, "backup_list.yaml")

    # read backup list with credentials
    with open(backup_list_path) as f:
        backup_list = yaml.load(f, Loader=yaml.FullLoader)

    # Ask user for the timestamp of the backup they want to restore
    timestamp = input("Enter the timestamp of the backup you want to restore: ")

    for backup in backup_list:

        # check if service is up
        try:
            core_v1.read_namespaced_service(name=backup["service"], namespace="services")
        except client.rest.ApiException as e:
            logger.info(f"Service {backup['service']} not found. Skipping restore.")
            continue

        # restore the database from the backup
        restore_database(backup["username"], backup["password"], backup["service"], timestamp, backup["database"])
