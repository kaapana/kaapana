from v1.services.logger import get_logger

from .content import Content, ContentInstaller

logger = get_logger(__name__)


class Dispatcher:
    def __init__(self, installers: list[ContentInstaller]):
        self.installers = installers

    async def install_content(self, content: Content):
        content_installer = self.find_installer(content)
        return await content_installer.install(content)

    async def uninstall_content(self, content: Content):
        content_installer = self.find_installer(content)
        if not content.location:
            logger.warning(
                f"Content {content.name} does not have a location for uninstallation"
            )
            return None
        await content_installer.uninstall(content)

    def find_installer(self, content: Content) -> ContentInstaller:
        for installer in self.installers:
            if installer.can_install(content):
                return installer
        raise Exception(f"No installer found for content type {content.content_type}")
