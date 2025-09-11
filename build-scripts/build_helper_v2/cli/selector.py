from typing import Any, List

from build_helper_v2.utils.logger import get_logger
from InquirerPy import inquirer
from InquirerPy.base.list import BaseListPrompt
from InquirerPy.prompts import fuzzy


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
    """Launch an interactive fuzzy multi-select prompt.

    Provides a fuzzy-searchable, scrollable list of options using
    InquirerPy. The prompt allows multiple selections, supports
    keyboard navigation, and requires at least one choice.

    Args:
        options (List[str]): List of available option strings.
        obj_type (str): Descriptive name of the object type (used in
            prompt messages and validation errors).

    Returns:
        List[str]: The list of selected options. If "ALL" is chosen,
        returns all items from ``options``.

    Example:
        >>> interactive_select(["fastsurfer", "nnunet"], "extension")
        # User selects "ALL"
        ['fastsurfer', 'nnunet']
    """
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
