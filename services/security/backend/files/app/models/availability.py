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
    _type: ProviderType = PrivateAttr(default=ProviderType.UNKNOWN)
    _status: AvailabilityStatus = PrivateAttr(default=AvailabilityStatus.NOT_CHECKED)
    _not_available_count: int = PrivateAttr(default=0)

    def __get_type(self, provider: InternalProviderRegistration):
        if provider.name.upper() == "WAZUH":
            return ProviderType.WAZUH
        elif provider.name.upper() == "STACKROX":
            return ProviderType.STACKROX

        assert False

    def set_available(self) -> None:
        self._status = AvailabilityStatus.AVAILABLE
        self._not_available_count = 0

    def set_unavailable(self) -> None:
        if not self._status == AvailabilityStatus.NOT_CHECKED:
            self._status = AvailabilityStatus.NOT_AVAILABLE
        self._not_available_count += 1

    def get_type(self) -> ProviderType:
        if self._type is ProviderType.UNKNOWN:
            self._type = self.__get_type(self.provider)

        return self._type

    def get_status(self) -> AvailabilityStatus:
        return self._status

    def get_not_available_count(self) -> int:
        return self._not_available_count


# basically just a helper for easier json serialization of list of pydantic classes
class ProviderAvailabilityWrapperList(BaseModel):
    __root__: List[ProviderAvailabilityWrapper] = []

    def get_provider_wrappers(self):
        return self.__root__

    def add(self, wrapper: ProviderAvailabilityWrapper):
        self.__root__ += [wrapper]

    def remove(self, wrapper: ProviderAvailabilityWrapper):
        self.__root__ = [
            w for w in self.__root__ if not w.provider.name == wrapper.provider.name
        ]
