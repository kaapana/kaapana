from enum import Enum

from models.extension import ExtensionRegistration, ExtensionType

class AvailabilityStatus(Enum):
    AVAILABLE = 1
    NOT_AVAILABLE = 2
    NOT_CHECKED = 3 # todo: maybe find another way, its for determining if extension was never available before (this means it can take longer for it to become available -> don't remove as eagerly)
    UNKNOWN = 999

class ExtensionAvailabilityWrapper():
    extension_registration: ExtensionRegistration = None
    __type: ExtensionType = ExtensionType.UNKNOWN
    __status: AvailabilityStatus = AvailabilityStatus.NOT_CHECKED
    __not_available_count: int = 0

    def __init__(self, extension: ExtensionRegistration):
        self.extension_registration = extension
        self.__type = self.__get_type(extension)

    def __get_type(self, extension: ExtensionRegistration):
        if extension.name.upper() == "WAZUH":
            return ExtensionType.WAZUH
        elif extension.name.upper() == "STACKROX":
            return ExtensionType.STACKROX

        assert False

    def set_available(self) -> None:
        self.__status = AvailabilityStatus.AVAILABLE
        self.__not_available_count = 0

    def set_unavailable(self) -> None:
        if not self.__status == AvailabilityStatus.NOT_CHECKED:
            self.__status = AvailabilityStatus.NOT_AVAILABLE
        self.__not_available_count += 1
        
    def get_type(self) -> ExtensionType:
        return self.__type

    def get_status(self) -> AvailabilityStatus:
        return self.__status

    def get_not_available_count(self) -> int:
        return self.__not_available_count