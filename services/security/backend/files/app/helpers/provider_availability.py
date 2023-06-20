from typing import Callable, List, Tuple
import os.path
import httpx
import asyncio
from models.provider import (
    ProviderRegistration,
    InternalProviderRegistration,
    ProviderRegistrationOverview,
    ProviderType,
)
from models.availability import (
    AvailabilityStatus,
    ProviderAvailabilityWrapper,
    ProviderAvailabilityWrapperList,
)
import logging
from helpers.resources import LOGGER_NAME
from helpers.logger import get_logger

logger = get_logger(f"{LOGGER_NAME}.provider_availability", logging.INFO)


class RegisteredProviders:
    __provider_persistence_path = "/data/providers.json"
    __providers: ProviderAvailabilityWrapperList = ProviderAvailabilityWrapperList()
    __availability_task = None

    def __init__(
        self,
        fn_on_provider_added: Callable[[ProviderType, ProviderRegistration], None],
        fn_on_provider_available: Callable[[ProviderType], None],
        fn_on_provider_unavailable: Callable[[ProviderType], None],
    ):
        self.on_provider_added = fn_on_provider_added
        self.on_provider_available = fn_on_provider_available
        self.on_provider_unavailable = fn_on_provider_unavailable

        self.__read_json()
        self.__availability_task = asyncio.create_task(self.__check_all_provider_availability())

    def __read_json(self):
        logger.debug("reading providers from json")
        if not os.path.isfile(self.__provider_persistence_path):
            return

        self.__providers = ProviderAvailabilityWrapperList.parse_file(
            self.__provider_persistence_path,
            encoding="utf-8",
            content_type="application/json",
        )
        for wrapper in self.__providers.get_provider_wrappers():
            self.on_provider_added(wrapper.get_type(), wrapper.provider)

    def __write_json(self):
        json = self.__providers.json(ensure_ascii=False, indent=4)
        logger.debug(f"writing providers to json: {json}")
        with open(self.__provider_persistence_path, "w", encoding="utf-8") as f:
            f.write(json)

    async def __check_all_provider_availability(self) -> None:
        while True:
            logger.debug("checking availability")
            for wrapper in self.__providers.get_provider_wrappers():
                if await self.__check_provider_availability(wrapper.provider):
                    logger.debug("setting provider to: available")
                    wrapper.set_available()
                    self.on_provider_available(wrapper.get_type())
                else:
                    logger.debug("setting provider to: NOT available")
                    wrapper.set_unavailable()
                    self.on_provider_unavailable(wrapper.get_type())

            wrappers_to_remove = []
            for wrapper in self.__providers.get_provider_wrappers():
                if self.__should_provider_be_removed(wrapper):
                    wrappers_to_remove += [wrapper]

            for wrapper in wrappers_to_remove:
                self.__providers.remove(wrapper)

            if len(wrappers_to_remove) > 0:
                self.__write_json()  # make sure persistance data is up-to-date

            await asyncio.sleep(15)

    async def __check_provider_availability(self, provider: InternalProviderRegistration) -> bool:
        logger.debug(f"availability check for provider: {provider.id}")

        async def check_url(url: str):
            try:
                logger.debug(f"checking url: {url}")
                _ = httpx.get(url, verify=False)
                return True  # we don't care about response (status), only that url is available and does not time out
            except Exception as e:
                logger.info(f"Expected exception while checking connection: {e}")
                return False

        result = await asyncio.gather(
            *[check_url(endp.endpoint) for endp in provider.api_endpoints]
        )
        logger.debug(f"availability result list: {result}")

        return any(result)

    def __should_provider_be_removed(self, provider: ProviderAvailabilityWrapper) -> bool:
        return (
            provider.get_status() == AvailabilityStatus.NOT_CHECKED
            and provider.get_not_available_count() >= 15
        ) or (
            (not provider.get_status() == AvailabilityStatus.NOT_CHECKED)
            and provider.get_not_available_count() >= 5
        )

    def get_names(self) -> List[str]:
        return list(
            map(
                lambda wrapper: wrapper.provider.name,
                self.__providers.get_provider_wrappers(),
            )
        )

    def get_overview(self) -> List[ProviderRegistrationOverview]:
        return list(
            map(
                lambda wrapper: wrapper.provider.get_overview(),
                self.__providers.get_provider_wrappers(),
            )
        )

    def add(self, provider: ProviderRegistration) -> Tuple[bool, ProviderType]:
        # check if provider with given name is already registered -> we do not allow double registrations
        new_provider_id = provider.name.lower()

        if any(
            [
                wrapper.provider.id == new_provider_id
                for wrapper in self.__providers.get_provider_wrappers()
            ]
        ):
            return False, None

        wrapped_provider = ProviderAvailabilityWrapper(
            provider=InternalProviderRegistration(
                id=new_provider_id,
                name=provider.name,
                url=provider.url,
                api_endpoints=provider.api_endpoints,
            )
        )
        self.__providers.add(wrapped_provider)

        self.__write_json()  # make sure persistance data is up-to-date

        self.on_provider_added(wrapped_provider.get_type(), wrapped_provider.provider)
        return True, wrapped_provider.get_type()
