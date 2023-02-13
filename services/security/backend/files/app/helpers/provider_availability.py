from typing import List
import os.path
import httpx
import asyncio
from models.provider import ProviderRegistration, InternalProviderRegistration
from models.availability import AvailabilityStatus, ProviderAvailabilityWrapper, ProviderAvailabilityWrapperList
import logging
from helpers.resources import LOGGER_NAME
from helpers.logger import get_logger

logger = get_logger(f"{LOGGER_NAME}.provider_availability", logging.INFO)

class RegisteredProviders:
    __provider_persistence_path = "/data/providers.json"
    __providers: ProviderAvailabilityWrapperList = ProviderAvailabilityWrapperList()
    __availability_task = None

    def __init__(self):
        self.__read_json()
        self.__availability_task = asyncio.create_task(self.__check_all_provider_availability())

    def __read_json(self):
        if not os.path.isfile(self.__provider_persistence_path):
            return

        self.__providers = ProviderAvailabilityWrapperList.parse_file(self.__provider_persistence_path, encoding="utf-8", content_type="application/json")

    def __write_json(self):
        with open(self.__provider_persistence_path, 'w', encoding='utf-8') as f:
            f.write(self.__providers.json(ensure_ascii=False, indent=4))

    async def __check_all_provider_availability(self) -> None:
        while True:
            logger.debug("checking availability")
            for wrapper in self.__providers.get_provider_wrappers():
                if await self.__check_provider_availability(wrapper.provider):
                    logger.debug("setting provider to: available")
                    wrapper.set_available()
                else:
                    logger.debug("setting provider to: NOT available")
                    wrapper.set_unavailable()

            for wrapper in self.__providers.get_provider_wrappers():
                any_removed = False
                if self.__should_provider_be_removed(wrapper):
                    self.__providers.remove(wrapper)
                    any_removed = True

                if any_removed:
                    self.__write_json() # make sure persistance data is up-to-date

            await asyncio.sleep(15)


    async def __check_provider_availability(self, provider: InternalProviderRegistration) -> bool:
        async def check_url(url: str):
            try:
                _ = httpx.get(url, verify=False)
                return True # we don't care about response (status), only that url is available and does not time out
            except Exception as e:
                logger.info(f"Expected exception while checking connection: {e}")
                return False

        result = await asyncio.gather(*[check_url(endp.endpoint) for endp in provider.api_endpoints])
        logger.debug(f"availability result list: {result}")

        return any(result)

    def __should_provider_be_removed(self, provider: ProviderAvailabilityWrapper) -> bool:
        return (provider.get_status() == AvailabilityStatus.NOT_CHECKED and provider.get_not_available_count() >= 15) or ((not provider.get_status() == AvailabilityStatus.NOT_CHECKED) and provider.get_not_available_count() >= 5)

    def get_names(self) -> List[str]:
        return list(map(lambda wrapper: wrapper.provider.name, self.__providers.get_provider_wrappers()))

    def get_overview(self) -> List[str]:
        return list(map(lambda wrapper: wrapper.provider.get_overview(), self.__providers.get_provider_wrappers()))

    def add(self, provider: ProviderRegistration) -> bool:
        # check if provider with given name is already registered -> we do not allow double registrations
        new_provider_id = provider.name.lower()

        if any([wrapper.provider.id == new_provider_id for wrapper in self.__providers.get_provider_wrappers()]):
            return False

        wrapped_provider = ProviderAvailabilityWrapper(provider=InternalProviderRegistration(id=new_provider_id, name=provider.name, url=provider.url, api_endpoints=provider.api_endpoints))
        self.__providers.add(wrapped_provider)

        self.__write_json() # make sure persistance data is up-to-date

        return True


registered_providers = RegisteredProviders()
