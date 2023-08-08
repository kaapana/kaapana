import requests

from fastapi import (
    APIRouter,
    Depends,
    Request,
    HTTPException,
    UploadFile,
    Response,
    File,
    Header,
)
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from opensearchpy import OpenSearch
from sqlalchemy.orm import Session

import uuid
from app.workflows.utils import (
    HelperMinio,
    raise_kaapana_connection_error,
    requests_retry_session,
)
from app.config import settings

router = APIRouter()


@router.get("/")
async def root(request: Request):
    return {
        "message": "Welcome to the backend",
        "root_path": request.scope.get("root_path"),
    }


@router.get("/health-check")
def health_check():
    return {f"SPE backend is up and running!"}


@router.get("/get-static-website-results")
def get_static_website_results():
    def build_tree(item, filepath, org_filepath):
        # Adapted from https://stackoverflow.com/questions/8484943/construct-a-tree-from-list-os-file-paths-python-performance-dependent
        splits = filepath.split("/", 1)
        if len(splits) == 1:
            item["vuetifyFiles"].append(
                {
                    "name": splits[0],
                    "file": "html",
                    "path": f"/static-website-browser/{org_filepath}",
                }
            )
        else:
            parent_folder, filepath = splits
            if parent_folder not in item:
                item[parent_folder] = {"vuetifyFiles": []}
            build_tree(item[parent_folder], filepath, org_filepath)

    def _get_vuetify_tree_structure(tree):
        subtree = []
        for parent, children in tree.items():
            print(parent, children)
            if parent == "vuetifyFiles":
                subtree = children
            else:
                subtree.append(
                    {
                        "name": parent,
                        "path": str(uuid.uuid4()),
                        "children": _get_vuetify_tree_structure(children),
                    }
                )
        return subtree

    tree = {"vuetifyFiles": []}
    objects = HelperMinio.minioClient.list_objects(
        "staticwebsiteresults", prefix=None, recursive=True
    )
    for obj in objects:
        if obj.object_name.endswith("html") and obj.object_name != "index.html":
            build_tree(tree, obj.object_name, obj.object_name)
    return _get_vuetify_tree_structure(tree)


@router.get("/get-os-dashboards")
def get_os_dashboards():
    try:
        res = OpenSearch(
            hosts=f"opensearch-service.{settings.services_namespace}.svc:9200"
        ).search(
            body={
                "query": {"exists": {"field": "dashboard"}},
                "_source": ["dashboard.title"],
            },
            size=10000,
            from_=0,
        )
    except Exception as e:
        print("ERROR in OpenSearch search!")
        return {"Error message": str(e)}, 500

    hits = res["hits"]["hits"]
    dashboards = list(sorted([hit["_source"]["dashboard"]["title"] for hit in hits]))
    return {"dashboards": dashboards}


@router.get("/get-traefik-routes")
def get_traefik_routes():
    try:
        with requests.Session() as s:
            r = requests_retry_session(session=s).get(
                f"{settings.traefik_url}/api/http/routers"
            )
        raise_kaapana_connection_error(r)
        return r.json()
    except Exception as e:
        print("ERROR in getting traefik routes!")
        return {"Error message": str(e)}, 500
