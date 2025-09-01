from contextlib import contextmanager
from typing import Any, List

from build_helper_v2.utils.logger import get_logger
from InquirerPy import inquirer
from InquirerPy.base.list import BaseListPrompt
from InquirerPy.prompts import fuzzy
from rich.console import Console, Group
from rich.live import Live
from rich.progress import BarColumn, Progress, TimeElapsedColumn
from rich.table import Table
from rich.text import Text


def patch_inquirerpy_safely():
    """
    Safely patch InquirerPy to prevent index errors when no filtered choices exist.
    Works for fuzzy multiselect and list prompts.
    """

    # --- FuzzyPrompt: toggle ---
    original_fuzzy_toggle = fuzzy.FuzzyPrompt._handle_toggle_choice

    def safe_fuzzy_toggle(self: fuzzy.FuzzyPrompt, event: Any):
        if self.content_control.choice_count == 0:
            self._set_error("No matches found")
            self._application.invalidate()
            return

        return original_fuzzy_toggle(self, event)

    fuzzy.FuzzyPrompt._handle_toggle_choice = safe_fuzzy_toggle

    # --- BaseListPrompt: handle up ---
    original_list_up = BaseListPrompt._handle_up

    def safe_list_up(self: BaseListPrompt, event: Any):
        if self.content_control.choice_count == 0:
            self._set_error("No matches found")
            self._application.invalidate()
            return False
        return original_list_up(self, event)

    BaseListPrompt._handle_up = safe_list_up

    # --- BaseListPrompt: handle down ---
    original_list_down = BaseListPrompt._handle_down

    def safe_list_down(self: BaseListPrompt, event: Any):
        if self.content_control.choice_count == 0:
            self._set_error("No matches found")
            self._application.invalidate()
            return False
        return original_list_down(self, event)

    BaseListPrompt._handle_down = safe_list_down


logger = get_logger()
patch_inquirerpy_safely()


def interactive_select(options: List[str], obj_type: str) -> List[str]:
    """Fuzzy searchable multiselect with scrollable list."""
    choices = ["ALL"] + options
    selected: List[str] = []

    selected = inquirer.fuzzy(
        message=f"Search & select {obj_type}s (TAB=toggle, ENTER=confirm):",
        choices=choices,
        multiselect=True,
        instruction=f"Use arrows to scroll. TAB to toggle selection. ENTER to confirm.",
        validate=lambda result: len(result) > 0,
        invalid_message=f"Select at least 1 {obj_type}",
        info=True,
        cycle=True,
        max_height="70%",
    ).execute()

    if "ALL" in selected:
        selected = options.copy()

    return selected
