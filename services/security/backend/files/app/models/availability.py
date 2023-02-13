from enum import Enum
from typing import List

from pydantic import BaseModel, PrivateAttr
from models.provider import InternalProviderRegistration, ProviderType

class AvailabilityStatus(Enum):
    AVAILABLE = 1
    NOT_AVAILABLE = 2
    NOT_CHECKED = 3
    UNKNOWN = 999

class ProviderAvailabilityWrapper(BaseModel):
    provider: InternalProviderRegistration = None
    __type: ProviderType = PrivateAttr(default=ProviderType.UNKNOWN)
    __status: AvailabilityStatus = PrivateAttr(default=AvailabilityStatus.NOT_CHECKED) 
    __not_available_count: int = PrivateAttr(default=0)

    def __get_type(self, provider: InternalProviderRegistration):
        if provider.name.upper() == "WAZUH":
            return ProviderType.WAZUH
        elif provider.name.upper() == "STACKROX":
            return ProviderType.STACKROX

        assert False

    def set_available(self) -> None:
        self.__status = AvailabilityStatus.AVAILABLE
        self.__not_available_count = 0

    def set_unavailable(self) -> None:
        if not self.__status == AvailabilityStatus.NOT_CHECKED:
            self.__status = AvailabilityStatus.NOT_AVAILABLE
        self.__not_available_count += 1
        
    def get_type(self) -> ProviderType:
        if self.__type is ProviderType.UNKNOWN:
            self.__type = self.__get_type(self.provider)            

        return self.__type

    def get_status(self) -> AvailabilityStatus:
        return self.__status

    def get_not_available_count(self) -> int:
        return self.__not_available_count

# basically just a helper for easier json serialization of list of pydantic classes
class ProviderAvailabilityWrapperList(BaseModel):
    __root__: List[ProviderAvailabilityWrapper] = []

    def get_provider_wrappers(self):
        return self.__root__

    def add(self, wrapper: ProviderAvailabilityWrapper):
        self.__root__ += [wrapper]

    def remove(self, wrapper: ProviderAvailabilityWrapper):
        self.__root__ = [w for w in self.__root__ if not w.provider.name == wrapper.provider.name]