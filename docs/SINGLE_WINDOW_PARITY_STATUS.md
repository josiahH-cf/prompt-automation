# Single-Window GUI Parity Status

This document tracks feature parity between the legacy multi‑window GUI and the new single‑window workflow. It also maps each capability to the primary test coverage and highlights remaining improvement opportunities.

Legend:
- SW = Single‑Window implementation status.
- Tests = Representative (not exhaustive) test files exercising the feature.
- Gaps / Enhancements = Recommended additional assertions or scenarios.

| Feature / Capability | Legacy | SW | Implementation Notes | Tests | Gaps / Enhancements |
| -------------------- | :----: | :-: | -------------------- | ------ | ------------------- |
| Template search & recursive toggle | Yes | Yes | Reuses `template_search.list_templates` | `tests/gui/single_window/test_select_frame.py`, `tests/services/test_template_search.py` | Add search input filtering assertion in headless stub (explicit query update round‑trip). |
| Numeric / custom shortcuts | Yes | Yes | Digit keys & `resolve_shortcut` advance | `test_select_frame.py`, `z_single_window/test_controller.py`, `z_single_window/test_enhancements.py::test_digit_shortcut_advances` | Covered. |
| Multi‑select & combine | Yes | Yes | `multi_select_service.merge_templates` | `tests/services/test_multi_select.py`, `z_single_window/test_enhancements.py::test_combine_propagates` | Covered. |
| Template preview panel | Yes | Yes | Preview text area / headless preview string | `test_select_frame.py::test_preview_updates`, `test_select_frame.py::test_preview_clears_when_selection_empty` | Covered. |
| Options / Settings menu | Yes | Yes | `options_menu.configure_options_menu` + dynamic stage items | `z_single_window/test_stage_menu_and_clipboard.py`, `z_single_window/test_enhancements.py::test_stage_menu_labels_change` | Covered. |
| Placeholder label display | Yes | Yes | Uses `label` key precedence | `test_collect_frame.py::test_label_precedence_over_name` | Covered. |
| Variable input types | Yes | Yes | `variable_form.build_widget` | `tests/services/test_variable_form.py`, `test_collect_frame.py` | Add explicit single‑window instantiation of multiline & file in one template (already partially). |
| Remembered context values | Yes | Yes | `remember_var` persistence | `test_collect_frame.py::test_multiline_remember` | Covered. |
| Skip flag for file placeholders | Yes | Yes | `skip_var` logic | `test_collect_frame.py::test_file_picker_skip_and_persistence` | Covered. |
| File view button for paths | Yes | Yes | `view_btn` when `view` provided | `tests/gui/collector/test_file_viewer.py` (legacy), `test_collect_frame` indirectly | Add single‑window explicit view callback invocation test. |
| Per‑template exclusions editor | Yes | Yes | Button triggers `app.edit_exclusions` | `test_collect_frame.py::test_exclusions_access`, `test_controller.py::test_edit_exclusions_delegates` | Covered. |
| Global reference file viewer | Yes | Yes | Inline manager + persistence | `test_collect_frame.py::test_global_reference_memory`, `test_collect_frame.py::test_view_callback_invocation_headless` | Covered. |
| Shortcut / quick command hints | Yes | Yes | Legend strings in constants module | `test_shortcut_legends.py` | Covered. |
| Override reset controls | Yes | Yes | Adds `reset` binding & button | `test_collect_frame.py::test_file_picker_skip_and_persistence` | Covered. |
| Review text editing | Yes | Yes | Editable `tk.Text` (headless stub returns namespace) | `test_review_frame.py`, `z_single_window/test_enhancements.py::test_instruction_mutation_after_copy` | Covered. |
| Copy to clipboard button | Yes | Yes | `do_copy` path | `test_review_frame.py::test_finish_copies_to_clipboard`, `z_single_window/test_enhancements.py::test_instruction_mutation_after_copy` | Covered. |
| Copy paths button | Yes | Yes | Conditional button & handler | `test_review_frame.py::test_copy_paths_visibility`, `z_single_window/test_enhancements.py::test_copy_paths_status_updates` | Covered. |
| Auto‑copy on finish (Ctrl+Enter) | Yes | Yes | Finish includes copy & log usage | `test_review_frame.py::test_finish_copies_to_clipboard`, `test_ctrl_enter_copies.py` | Covered. |
| Append rendered text to files | Yes | Yes | `_append_to_files` behind confirmation | `test_review_frame.py::test_append_confirmation_flow` | Covered. |
| Usage logging | Yes | Yes | `log_usage` call | `test_review_frame.py::test_usage_logging_invocation` | Covered. |
| Geometry persistence | Yes | Yes | `load_geometry`/`save_geometry` on swaps | `test_geometry.py`, `test_controller.py::test_stage_swap_persists_geometry` | Covered. |
| Error dialogs on failure | Yes | Yes | `show_error` wrappers, safe copy | `test_controller.py::test_service_exception_triggers_dialog_and_log`, `test_stage_menu_and_clipboard.py::test_safe_copy_to_clipboard_failure`, `z_single_window/test_enhancements.py::test_select_failure_error` , `z_single_window/test_enhancements.py::test_error_dialog_on_review_failure` | Covered. |
| Hotkeys / accelerator legend | Yes | Yes | Legends per stage | `test_shortcut_legends.py` | Covered. |
| Keyboard shortcut bindings | Yes | Yes | Ctrl+Enter, Esc, etc. | `test_review_frame.py::test_shortcut_keys`, `test_ctrl_enter_copies.py`, `z_single_window/test_enhancements.py::test_instruction_mutation_after_copy` | Covered. |

## Current Status

All previously identified practical parity gaps now have direct single‑window test coverage (see Covered items in the table). Remaining optional ideas (not required for parity) are limited to minor niceties like additional preview refresh assertions or view callback invocation in headless mode; these are intentionally deferred to keep the suite lean.
