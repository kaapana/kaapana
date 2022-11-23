import openstack
from openstack import connection
import logging

logging.getLogger().setLevel(logging.INFO)
# openstack.enable_logging(debug=True)

def delete_unused_volumes(conn_params, detect_only=True):
    conn = connection.Connection(
        region_name="regionOne",
        auth=dict(
            auth_url=conn_params["auth_url"],
            username=conn_params["username"],
            password=conn_params["password"],
            project_id=conn_params["project_id"],
            user_domain_id=conn_params["user_domain_id"]
        ),
        compute_api_version="2",
        identity_interface="public"
        )

    volumes = conn.list_volumes()
    snapshots = conn.list_volume_snapshots()
    snapshot_volume_ids = [x["volume_id"] for x in snapshots]
    ## A volume that's not in use and also not attached to any snapshot can be deleted
    delete_volumes_ids = [x["id"] for x in volumes if x["id"] not in snapshot_volume_ids and x["status"] != "in-use"]
    
    if not delete_volumes_ids:
        logging.info(f"There are currently no unused volumes under the {conn_params['project_name']} project!!!")
        return
    elif detect_only:
        print(f"Following is a list of currently unused volumes under {conn_params['project_name']} OpenStack project:\n{delete_volumes_ids}")
        return
    
    for volume_id in delete_volumes_ids:
        logging.debug(f"Deleting volume with ID - {volume_id} since it is not in use and not attached to any snapshot...")
        conn.delete_volume(volume_id)
    logging.info(f"Total of {len(delete_volume_ids)} unused volumes were deleted...")


if __name__ == "__main__":
    conn_params = {
        "region_name": "regionOne",
        "auth_url": "",
        "username": "",
        "password": "",
        "project_id": "",
        "user_domain_id": "", # you can get this from OpenStack UI Dashboard
        "project_name": ""
        # "user_domain": ""
    }
    delete_unused_volumes(conn_params, detect_only=True)

print("The end...")

