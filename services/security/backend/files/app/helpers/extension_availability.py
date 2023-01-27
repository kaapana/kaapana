from typing import List
import httpx
import asyncio
from models.extension import ExtensionRegistration
from models.availability import AvailabilityStatus, ExtensionAvailabilityWrapper


class RegisteredExtensions:
    __extensions: List[ExtensionAvailabilityWrapper] = []
    __availability_task = None

    def __init__(self):
        self.__availability_task = asyncio.create_task(self.__check_all_extensions_availability())

    async def __check_all_extensions_availability(self) -> None:
        while True:
            print("checking availability")
            for extension in self.__extensions:
                if await self.__check_extension_availability(extension.extension_registration):
                    print("setting extension available")
                    extension.set_available()
                else:
                    print("setting extension NOT available")
                    extension.set_unavailable()
            
            print("extensions before:")
            for ext in self.__extensions:
                print(f"{ext.extension_registration.name}, {ext.get_not_available_count()}, {ext.get_status()}")
            self.__extensions = [ext for ext in self.__extensions if not self.__remove_extension(extension)]
            print("extensions after:")
            for ext in self.__extensions:
                print(f"{ext.extension_registration.name}, {ext.get_not_available_count()}, {ext.get_status()}")

            await asyncio.sleep(15)


    async def __check_extension_availability(self, extension: ExtensionRegistration) -> bool:
        async def check_url(url: str):
            try:
                _ = httpx.get(url, verify=False)
                return True # we don't care about response (status), only that url is available and does not time out 
            except Exception as e:
                print(f"Exception while checking connection: {e}")
                return False

        result = await asyncio.gather(*[check_url(endp.endpoint) for endp in extension.api_endpoints])
        print(f"availability result list: {result}")

        return any(result)

    def __remove_extension(self, extension: ExtensionRegistration) -> bool:
        return (extension.get_status() == AvailabilityStatus.NOT_CHECKED and extension.get_not_available_count() >= 15) or ((not extension.get_status() == AvailabilityStatus.NOT_CHECKED) and extension.get_not_available_count() >= 5)

    def get_names(self) -> List[str]:
        return list(map(lambda ext: ext.extension_registration.name, self.__extensions))

    def add(self, extension: ExtensionRegistration) -> bool:
        # check if extension with given name is already registered -> we do not allow double registrations
        if any([ext.extension_registration.name == extension.name for ext in self.__extensions]):
            return False

        wrapped_extension = ExtensionAvailabilityWrapper(extension)
        self.__extensions += [wrapped_extension]

        return True


registered_extensions = RegisteredExtensions()
