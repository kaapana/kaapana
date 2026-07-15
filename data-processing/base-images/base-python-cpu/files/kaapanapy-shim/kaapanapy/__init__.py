# kaapanapy/__init__.py
import importlib
import importlib.abc
import importlib.machinery
import sys
import warnings

import kaapana_client

warnings.warn(
    "kaapanapy is deprecated and will be removed in a future release. "
    "Use kaapana_client instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.modules["kaapanapy"] = kaapana_client


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, real_mod):
        self._real_mod = real_mod

    def create_module(self, spec):
        return self._real_mod

    def exec_module(self, module):
        pass


class _KaapanaPyFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if not fullname.startswith("kaapanapy."):
            return None
        real_name = fullname.replace("kaapanapy.", "kaapana_client.", 1)
        try:
            real_mod = importlib.import_module(real_name)
        except ImportError:
            return None
        return importlib.machinery.ModuleSpec(fullname, _AliasLoader(real_mod))


sys.meta_path.append(_KaapanaPyFinder())
