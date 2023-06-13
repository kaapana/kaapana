import asyncio
import itertools
from typing import Any, Coroutine, Dict, Optional, List
import httpx
import logging
from helpers.resources import LOGGER_NAME
from helpers.logger import get_logger, function_logger_factory, trimContent
from models.JWTToken import JWTToken
from models.wazuh_models import (
    FileIntegrityAlertRule,
    WazuhAgent,
    WazuhAgentFileIntegrityAlert,
    WazuhAgentVulnerability,
    WazuhSCAPolicy,
    WazuhSCAPolicyCheck,
)
import jwt
from datetime import datetime, timezone
import base64
import os
from functools import wraps
from models.provider import ProviderAPIEndpoints
import inspect
from models.misc import SecurityNotification

logger = get_logger(f"{LOGGER_NAME}.wazuh_api", logging.INFO)

WAZUH_API_ITEM_LIMIT = 500  # 500 is default


class WazuhAPIAuthentication:
    __jwt_token: JWTToken = None
    __api_username: str = ""
    __api_pw: str = ""
    __api_endpoint: Optional[str] = None

    def __init__(self):
        self.__read_credentials()

    def __read_credentials(self):
        user_file = "/api_credentials/wazuh_username"
        pw_file = "/api_credentials/wazuh_password"

        if os.path.isfile(user_file) and self.__api_username == "":
            with open(user_file, "r") as file:
                self.__api_username = file.read().rstrip()

        if os.path.isfile(pw_file) and self.__api_pw == "":
            with open(pw_file, "r") as file:
                self.__api_pw = file.read().rstrip()

        logger.debug(f"wazuh user: {self.__api_username}, pw: {self.__api_pw}")

    @function_logger_factory(logger)
    def __retrieve_token(self, retry=True) -> bool:
        self.__read_credentials()
        auth_bytes = base64.b64encode(
            bytes(f"{self.__api_username}:{self.__api_pw}", "utf-8")
        )
        auth_base64 = auth_bytes.decode("utf-8")

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {auth_base64}",
            }
            result = httpx.get(
                f"{self.__api_endpoint}/security/user/authenticate",
                verify=False,
                headers=headers,
            )
            logger.debug(
                f"result from '/security/user/authenticate': {result} - {trimContent(result.content)}"
            )

            if result.status_code == 401 and retry:
                return self.__retrieve_token(False)

            result.raise_for_status()

            jwt_token = result.json()["data"]["token"]
            decoded_token = jwt.decode(
                jwt_token, verify=False, options={"verify_signature": False}
            )
            expiration_date = datetime.fromtimestamp(
                float(decoded_token["exp"]), tz=timezone.utc
            )
            self.__jwt_token = JWTToken(
                token=jwt_token, expiration_date=expiration_date
            )

            return True
        except Exception as e:
            logger.info(f"exception while retrieving token: {e}")
            return False

    @function_logger_factory(logger)
    def get_bearer_token(self) -> Optional[str]:
        if (
            self.__jwt_token is None
            or self.__jwt_token.expired_or_expires_soon(expires_soon_seconds=30)
        ) and not self.__retrieve_token():
            logger.error("Could not retrieve Wazuh jwt token")
            return None

        logger.debug(f"Wazuh jwt token available")
        return f"Bearer {self.__jwt_token.token}"

    @function_logger_factory(logger)
    def reset(self):
        self.__jwt_token = None
        self.__api_username = ""
        self.__api_pw = ""

    def set_api_endpoint(self, api_endpoint: str):
        self.__api_endpoint = api_endpoint


class WazuhAPIWrapper:
    # https://documentation.wazuh.com/current/user-manual/api/reference.html
    __wazuh_authentication: WazuhAPIAuthentication

    def __init__(
        self,
        wazuh_authentication: WazuhAPIAuthentication,
        api_endpoints: List[ProviderAPIEndpoints],
    ):
        self.__wazuh_authentication = wazuh_authentication

        logger.debug(f"wazuh api given endpoints: {api_endpoints}")
        api = list(filter(lambda endpoint: endpoint.identifier == "api", api_endpoints))
        elastic_api = list(
            filter(lambda endpoint: endpoint.identifier == "elastic_api", api_endpoints)
        )
        self.__api_endpoint = (
            api[0].endpoint.removesuffix("/")
            if len(api) > 0
            else "https://security-wazuh-service.services.svc:55000"
        )
        self.__elastic_api_endpoint = (
            elastic_api[0].endpoint.removesuffix("/")
            if len(elastic_api) > 0
            else "https://security-wazuh-service.services.svc:9200"
        )
        self.__wazuh_authentication.set_api_endpoint(self.__api_endpoint)
        logger.debug(
            f"setting wazuh api wrapper endpoints, api: {self.__api_endpoint}, elastic api: {self.__elastic_api_endpoint}"
        )

    # TODO: same method here and in stackrox_api.py -> extract & combine
    def retry_on_unauthorized(fn):
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def wrapper(self, *args, **kwargs):
                try:
                    logger.debug("retry_wrapper calling function")
                    return await fn(self, *args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        logger.debug("retry_wrapper 401, retrying")
                        # retry once with newly read credentials
                        self.__wazuh_authentication.reset()
                        return await fn(self, *args, **kwargs)

            return wrapper
        else:

            @wraps(fn)
            def wrapper(self, *args, **kwargs):
                try:
                    logger.debug("retry_wrapper calling function")
                    return fn(self, *args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        logger.debug("retry_wrapper 401, retrying")
                        # retry once with newly read credentials
                        self.__wazuh_authentication.reset()
                        return fn(self, *args, **kwargs)

            return wrapper

    # https://documentation.wazuh.com/current/user-manual/api/reference.html#operation/api.controllers.agent_controller.get_agent_summary_status
    @retry_on_unauthorized
    @function_logger_factory(logger)
    def is_agent_installed(self) -> bool:
        result = httpx.get(
            f"{self.__api_endpoint}/agents/summary/status",
            verify=False,
            headers={"Authorization": self.__wazuh_authentication.get_bearer_token()},
        )
        logger.debug(
            f"result from '/agents/summary/status': {result} - {trimContent(result.content)}"
        )

        result.raise_for_status()

        data = result.json()["data"]
        total_agents = int(data["total"])
        return total_agents > 0

    # https://documentation.wazuh.com/current/user-manual/api/reference.html#operation/api.controllers.agent_controller.get_agents
    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_all_agents(self) -> List[WazuhAgent]:
        params = {"q": "id!=000"}
        result = httpx.get(
            f"{self.__api_endpoint}/agents",
            params=params,
            verify=False,
            headers={"Authorization": self.__wazuh_authentication.get_bearer_token()},
        )
        logger.debug(f"result from '/agents': {result} - {trimContent(result.content)}")

        result.raise_for_status()

        affected_items = result.json()["data"]["affected_items"]
        agent_list: List[WazuhAgent] = []
        for item in affected_items:
            agent = WazuhAgent(
                id=item["id"], ip=item["ip"], name=item["name"], status=item["status"]
            )
            agent_list += [agent]

        return agent_list

    # https://documentation.wazuh.com/current/user-manual/api/reference.html#operation/api.controllers.sca_controller.get_sca_agent
    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_agent_sca_policies(self, agent_id: str) -> List[WazuhSCAPolicy]:
        policy_list: List[WazuhSCAPolicy] = []
        iteration = 0

        while True:
            params = {
                "limit": WAZUH_API_ITEM_LIMIT,
                "offset": iteration * WAZUH_API_ITEM_LIMIT,
            }

            result = httpx.get(
                f"{self.__api_endpoint}/sca/{agent_id}",
                params=params,
                verify=False,
                headers={
                    "Authorization": self.__wazuh_authentication.get_bearer_token()
                },
            )
            logger.debug(
                f"result from '/sca/{agent_id}': {result} - {trimContent(result.content)}"
            )

            result.raise_for_status()

            data = result.json()["data"]
            affected_items = data["affected_items"]

            for item in affected_items:
                policy = WazuhSCAPolicy(
                    id=item["policy_id"],
                    name=item["name"],
                    passed=item["pass"],
                    failed=item["fail"],
                    unapplicable=item["invalid"],
                )
                policy_list += [policy]

            iteration += 1

            # if we have WAZUH_API_ITEM_LIMIT items, there could potentially be more -> query once more
            if len(affected_items) < WAZUH_API_ITEM_LIMIT:
                break

        return policy_list

    # https://documentation.wazuh.com/current/user-manual/api/reference.html#operation/api.controllers.sca_controller.get_sca_checks
    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_agent_sca_policy_checks(
        self, agent_id: str, policy_id: str
    ) -> List[WazuhSCAPolicyCheck]:
        policy_data_list: List[WazuhSCAPolicyCheck] = []
        iteration = 0

        while True:
            params = {
                "limit": WAZUH_API_ITEM_LIMIT,
                "offset": iteration * WAZUH_API_ITEM_LIMIT,
            }

            result = httpx.get(
                f"{self.__api_endpoint}/sca/{agent_id}/checks/{policy_id}",
                params=params,
                verify=False,
                headers={
                    "Authorization": self.__wazuh_authentication.get_bearer_token()
                },
            )
            logger.debug(
                f"result from '/sca/{agent_id}/checks/{policy_id}': {result} - {trimContent(result.content)}"
            )

            result.raise_for_status()

            data = result.json()["data"]
            affected_items = data["affected_items"]

            for item in affected_items:
                policy_data = WazuhSCAPolicyCheck(
                    description=item["description"],
                    directory=item["directory"] if "directory" in item else None,
                    file=item["file"] if "file" in item else None,
                    command=item["command"] if "command" in item else None,
                    rationale=item["rationale"],
                    references=item["references"] if "references" in item else None,
                    remediation=item["remediation"] if "remediation" in item else None,
                    result=item["result"],
                    title=item["title"],
                )
                policy_data_list += [policy_data]

            iteration += 1

            # if we have WAZUH_API_ITEM_LIMIT items, there could potentially be more -> query once more
            if len(affected_items) < WAZUH_API_ITEM_LIMIT:
                break

        return policy_data_list

    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_agent_file_integrity_alerts(
        self, agent_id: str
    ) -> List[WazuhAgentFileIntegrityAlert]:
        fim_alerts: List[WazuhAgentFileIntegrityAlert] = []
        iteration = 0

        def generate_payload(offset: int, limit: int):
            return {
                "from": offset,
                "size": limit,
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"agent.id": agent_id}},
                            {"match": {"rule.groups": "syscheck"}},
                        ]
                    }
                },
                "sort": [{"@timestamp": {"order": "desc"}}],
            }

        while True:
            result = httpx.post(
                f"{self.__elastic_api_endpoint}/wazuh-alerts*/_search",
                json=generate_payload(
                    iteration * WAZUH_API_ITEM_LIMIT, WAZUH_API_ITEM_LIMIT
                ),
                verify=False,
                # Auth is default 'admin:SecretPassword', TODO: remove once SSO works
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Basic YWRtaW46U2VjcmV0UGFzc3dvcmQ=",
                },
            )
            logger.debug(
                f"result from '/_wazuh-alerts*/_search' with agent '{agent_id}' and rule.group 'syscheck': {result} - {trimContent(result.content)}"
            )

            result.raise_for_status()

            hits = result.json()["hits"]
            alert_list = hits["hits"]

            for alert in alert_list:
                alert_source = alert["_source"]
                rule = FileIntegrityAlertRule(
                    level=alert_source["rule"]["level"],
                    description=alert_source["rule"]["description"],
                )
                fim_alert = WazuhAgentFileIntegrityAlert(
                    id=alert["_id"],
                    path=alert_source["syscheck"]["path"],
                    rule=rule,
                    full_log=alert_source["full_log"],
                )
                fim_alerts += [fim_alert]

            iteration += 1

            # if we have WAZUH_API_ITEM_LIMIT items, there could potentially be more -> query once more
            if len(alert_list) < WAZUH_API_ITEM_LIMIT:
                break

        return fim_alerts

    @retry_on_unauthorized
    @function_logger_factory(logger)
    async def __get_agent_vulnerabilities_for_severity(
        self, agent_id: str, severity: str, additional_params: Dict[str, str]
    ) -> List[WazuhAgentVulnerability]:
        vulnerabilities: List[WazuhAgentVulnerability] = []
        iteration = 0

        async with httpx.AsyncClient(verify=False) as session:
            while True:
                params = {
                    "severity": severity,
                    "limit": WAZUH_API_ITEM_LIMIT,
                    "offset": iteration * WAZUH_API_ITEM_LIMIT,
                }

                result = await session.get(
                    f"{self.__api_endpoint}/vulnerability/{agent_id}",
                    params=params | additional_params,
                    headers={
                        "Authorization": self.__wazuh_authentication.get_bearer_token()
                    },
                )
                logger.debug(
                    f"result from '/vulnerability/{agent_id}' with severity '{severity}' and additional params '{additional_params}': {result} - {trimContent(result.content)}"
                )

                result.raise_for_status()

                data = result.json()["data"]
                affected_items = data["affected_items"]

                for item in affected_items:
                    vulnerability = WazuhAgentVulnerability(
                        severity=item["severity"],
                        version=item["version"],
                        type=item["type"],
                        name=item["name"],
                        external_references=item["external_references"],
                        condition=item["condition"],
                        detection_time=item["detection_time"],
                        cvss3_score=item["cvss3_score"],
                        cvss2_score=item["cvss2_score"],
                        published=item["published"],
                        architecture=item["architecture"],
                        cve=item["cve"],
                        status=item["status"],
                        title=item["title"],
                    )
                    vulnerabilities += [vulnerability]

                iteration += 1

                # if we have WAZUH_API_ITEM_LIMIT items, there could potentially be more -> query once more
                if len(affected_items) < WAZUH_API_ITEM_LIMIT:
                    break

        return vulnerabilities

    # https://documentation.wazuh.com/current/user-manual/api/reference.html#operation/api.controllers.vulnerability_controller.get_vulnerability_agent
    @retry_on_unauthorized
    @function_logger_factory(logger)
    async def get_agent_vulnerabilities(
        self, agent_id: str
    ) -> List[WazuhAgentVulnerability]:
        vulnerability_results: Coroutine[Any, Any, List[WazuhAgentVulnerability]] = []

        # first get fixable vulnerabilities
        for severity in ["critical", "high", "medium", "low"]:
            vulnerability_results += [
                self.__get_agent_vulnerabilities_for_severity(
                    agent_id, severity, {"q": "condition!=Package unfixed"}
                )
            ]

        # then the unfixable ones
        for severity in ["critical", "high", "medium", "low"]:
            vulnerability_results += [
                self.__get_agent_vulnerabilities_for_severity(
                    agent_id, severity, {"q": "condition=Package unfixed"}
                )
            ]

        # we get a list of 4 lists (each containing all vulnerabilities of one severity, in the same order that we put them in the loop above)
        result = await asyncio.gather(*vulnerability_results)

        # flatten the 4 lists above to have all vulnerabilities in sequence (still ordered from critical > ... > low)
        return list(itertools.chain.from_iterable(result))

    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_new_events(self, base_url: str, events_of_last_n_seconds: int):
        wazuh_events: List[SecurityNotification] = []

        payload = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "timestamp": {"gte": f"now-{events_of_last_n_seconds}s"}
                            }
                        }
                    ],
                    "must_not": [{"match": {"agent.id": "000"}}],
                }
            },
            "sort": [{"timestamp": {"order": "desc"}}],
        }
        result = httpx.post(
            f"{self.__elastic_api_endpoint}/wazuh-alerts*/_search",
            json=payload,
            verify=False,
            # Auth is default 'admin:SecretPassword', TODO: remove once SSO works
            headers={
                "Content-Type": "application/json",
                "Authorization": "Basic YWRtaW46U2VjcmV0UGFzc3dvcmQ=",
            },
        )

        logger.info(
            f"result from '/_wazuh-alerts*/_search': {result} - {trimContent(result.content)}"
        )

        result.raise_for_status()
        hits = result.json()["hits"]
        event_list = hits["hits"]

        for event in event_list:
            event_source = event["_source"]
            notification = SecurityNotification(
                title=event_source["rule"]["description"],
                description=event_source["full_log"],
                link=f"{base_url}/app/wazuh#/overview/?tab=general",
                timestamp=datetime.now(timezone.utc),
            )

            wazuh_events += [notification]

        return wazuh_events
