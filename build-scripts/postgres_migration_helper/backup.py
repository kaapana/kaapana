from kubernetes import client, config
import datetime
import os
import yaml
import logging

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
storage_v1 = client.StorageV1Api()

# Get the current timestamp
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S").replace("_", "-")

# Replace this with the path to your desired hostPath
host_path = f"/home/kaapana/backups/{timestamp}"

def create_persistent_volume():
    exists = True

    # Check if PersistentVolume already exists
    try:
        core_v1.read_persistent_volume(name=f"postgres-backup-pv-{timestamp}")
    except client.rest.ApiException as e:
        exists = False

    if not exists:
        # Create the PersistentVolume
        pv = client.V1PersistentVolume(
            metadata=client.V1ObjectMeta(name=f"postgres-backup-pv-{timestamp}", labels={"type": "local"}),
            spec=client.V1PersistentVolumeSpec(
                capacity={"storage": "1Gi"},
                access_modes=["ReadWriteOnce"],
                persistent_volume_reclaim_policy="Retain",
                storage_class_name="host-dir",
                host_path=client.V1HostPathVolumeSource(path=host_path),
            ),
        )

        core_v1.create_persistent_volume(body=pv)

def create_persistent_volume_claim():
    exists = True
    # Check if PersistentVolumeClaim already exists
    try:
        core_v1.read_namespaced_persistent_volume_claim(
            name=f"postgres-backup-pvc-{timestamp}", namespace="services"
        )
    except client.rest.ApiException as e:
        exists = False

    if not exists:
        # Create the PersistentVolumeClaim
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=f"postgres-backup-pvc-{timestamp}"),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(requests={"storage": "1Gi"}),
                storage_class_name="host-dir",
                volume_name=f"postgres-backup-pv-{timestamp}",
            ),
        )

        core_v1.create_namespaced_persistent_volume_claim(namespace="services", body=pvc)

def create_backup_pod(username, password, host):
    # Create the backup Pod
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(name=f"{host}-backup-{timestamp}"),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="backup-container",
                    image="postgres:latest",
                    command=[
                        "sh",
                        "-c",
                        f"pg_dumpall -U {username} -W -h {host} --file=/backup/{timestamp}/{host}-backup.sql",
                    ],
                    env=[
                        client.V1EnvVar(
                            name="PGPASSWORD",
                            value=f"{password}",
                        ),
                    ],
                    volume_mounts=[
                        client.V1VolumeMount(
                            name="backup-volume",
                            mount_path=f"/backup/{timestamp}",
                        ),
                    ],
                ),
            ],
            volumes=[
                client.V1Volume(
                    name="backup-volume",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=f"postgres-backup-pvc-{timestamp}",
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

    create_persistent_volume()
    create_persistent_volume_claim()

    for backup in backup_list:

        # check if service is up
        try:
            core_v1.read_namespaced_service(name=backup["service"], namespace="services")
        except client.rest.ApiException as e:
            logger.info(f"Service {backup['service']} not found. Skipping backup.")
            continue

        # create backup pod
        create_backup_pod(backup["username"], backup["password"], backup["service"])
    
