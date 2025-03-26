from app.dependencies import get_minio, get_project
from fastapi import APIRouter, Depends, HTTPException
from minio.error import S3Error

router = APIRouter(tags=["storage"])


@router.get("/projectbucket")
def projectbucket(prefix: str = "", minio=Depends(get_minio), project=Depends(get_project)):
    
    if project and "s3_bucket" in project:
        bucket_name = project.get("s3_bucket")
    else:
        raise HTTPException(
            status_code=404,
            detail="Bucket name not found or don't have access to the bucket",
        )
    
    # Ensure prefix ends with a slash if it's not empty
    if prefix and not prefix.endswith('/'):
        prefix = prefix + '/'
    
    try:
        # Get all objects at the current level
        objects_list = list(minio.list_objects(bucket_name, prefix=prefix, recursive=False))
        print(objects_list)
        # Process the results into a tree structure
        result = []
        directories = set()
        
        # First pass: collect directories
        for obj in objects_list:
            object_name = obj.object_name
            
            # Skip the directory itself
            if object_name == prefix:
                continue
                
            # Get the relative path from the prefix
            rel_path = object_name[len(prefix):]
            
            # Check if this path contains a directory
            if '/' in rel_path:
                # Extract directory name (first level only)
                dir_name = rel_path.split('/')[0]
                if dir_name and dir_name not in directories:
                    directories.add(dir_name)
                    result.append({
                        "name": dir_name,
                        "path": prefix + dir_name + '/',
                        "file": False,
                        "children": [],
                        "hasChildren": True
                    })
            else:
                # This is a file at the current level
                result.append({
                    "name": rel_path,
                    "path": object_name,
                    "file": True,
                    "hasChildren": False
                })
        
        return result
        
    except S3Error as e:
        raise HTTPException(
            status_code=404,
            detail=f"Error accessing bucket: {str(e)}",
        )
