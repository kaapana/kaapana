from fastapi import APIRouter, Depends
from .services import ExtensionService
from .schemas import Installation
from app.dependencies import get_extension_service

router = APIRouter(tags = ["extensions"])

@router.get('/environment')
async def get_helm_environment(service: ExtensionService = Depends(get_extension_service)):
    """ Return extension environment
    """
    return service.get_environment()

@router.get('/installed')
async def get_installed_extensions(service: ExtensionService = Depends(get_extension_service)):
    """Return List of Installed Helm Charts
    To List Installed Helm Charts
    """
    return service.installed()

@router.get('/{name}/status')
async def get_extension_status(name: str, service: ExtensionService = Depends(get_extension_service)):
    """ To List  Chart Status
    """
    return service.status(name)

@router.get('/')
async def list_extensions(service: ExtensionService = Depends(get_extension_service)):
    """Return list of available Charts
    """
    return service.all()

@router.delete('/installed/{name}/{version}')
async def delete_extension(name: str, version: str, service: ExtensionService = Depends(get_extension_service)):
    """ Deletes an installed extensions
    """ 
    return service.delete(name, version)

@router.post('/installed/')
async def install_extension(installation: Installation, service: ExtensionService = Depends(get_extension_service)):
    """ To Install a  Chart (Recommended to call /list-available-charts/ first, to get the available charts to Install. The release_name parameter is only for multi-installer charts.  The release_name must follow this format. Chartname-<ustomname>. For example if chart name is mitk-workbench-chart, then the release_name  could be mitk-workbench-chart-customname)
    """ 
    return service.install(
        installation.name,
        installation.version,
        installation.release_name,
        installation.keywords,
        installation.parameters
    )

@router.get('/health')
async def get_health(service: ExtensionService = Depends(get_extension_service)):
    """ Status of the underlying api """
    return service.health()

@router.get('/reload')
async def reload_extesions_list(service: ExtensionService = Depends(get_extension_service)):
    """ Reloads the local extensions """
    return service.reload()

@router.get('/update')
async def update_extesions_list(service: ExtensionService = Depends(get_extension_service)):
    """ Download new extensions from registry """
    return service.update()

@router.get('/pending')
async def pending(service: ExtensionService = Depends(get_extension_service)):
    return service.pending()

# TODO: Start/Stop/Get running applications @router.post/delete/get('/running')