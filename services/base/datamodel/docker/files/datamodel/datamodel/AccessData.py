## Connection to Keycloak to request User Group Models
#from datamodel.database.permission_model import Permission
from datamodel.globals import KEYCLOAK_URI
class AccessData:
    def __init__(self):
        keycloak_uri = KEYCLOAK_URI



    @staticmethod
    def GetKeycloakGroupModels(store_aet):
        #return "Not implemented yet"
        #TODo: validate against keycloak if this is a group, otherwise set to a specific default group
        return store_aet


    # def GetPermission(self, type):
    #     ## TODO
    #     return Permission.READ
    #
    #     if type =="...":
    #         return None


