from .content import Content, ContentInstaller


class Dispatcher:
    def __init__(self, installers: list[ContentInstaller]):
        self.installers = installers

    async def install_content(self, content: Content):
        content_installer = self._find_installer(content)
        return await content_installer.install(content)

    async def uninstall_content(self, content: Content):
        content_installer = self._find_installer(content)
        if not content.location:
            raise Exception(
                f"Content {content.name} does not have a location for uninstallation"
            )
        await content_installer.uninstall(content.location)

    def _find_installer(self, content: Content) -> ContentInstaller | None:
        for installer in self.installers:
            if installer.can_install(content):
                return installer
        raise Exception(f"No installer found for content type {content.content_type}")
