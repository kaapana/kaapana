from fastapi import APIRouter, Request
from ..proxy_request import proxy_request
# import json

router = APIRouter()


@router.post("/studies", tags=["STOW-RS"])
async def store_instances(request: Request):
    
    # TODO: Dynamic project assignment
    # # Extract the 'clinical_trial_protocol_info' query parameter
    # clinical_trial_protocol_info = request.query_params.get(
    #     "clinical_trial_protocol_info"
    # )

    # # Convert the JSON-encoded string to a dictionary
    # if clinical_trial_protocol_info:
    #     try:
    #         clinical_trial_protocol_info_dict = json.loads(clinical_trial_protocol_info)
    #         # Print the dictionary
    #         print(clinical_trial_protocol_info_dict)
    #     except json.JSONDecodeError:
    #         print("Error decoding JSON from clinical_trial_protocol_info")

    return await proxy_request(request, "/studies", "POST")


@router.post("/studies/{study}", tags=["STOW-RS"])
async def store_instances_in_study(study: str, request: Request):

    # TODO: Dynamic project assignment
    # # Extract the 'clinical_trial_protocol_info' query parameter
    # clinical_trial_protocol_info = request.query_params.get(
    #     "clinical_trial_protocol_info"
    # )

    # # Convert the JSON-encoded string to a dictionary
    # if clinical_trial_protocol_info:
    #     try:
    #         clinical_trial_protocol_info_dict = json.loads(clinical_trial_protocol_info)
    #         # Print the dictionary
    #         print(clinical_trial_protocol_info_dict)
    #     except json.JSONDecodeError:
    #         print("Error decoding JSON from clinical_trial_protocol_info")

    return await proxy_request(request, f"/studies/{study}", "POST")
