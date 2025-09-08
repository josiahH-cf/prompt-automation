"""CLI controller extracted from package init to keep files small.

Provides the PromptCLI class used by console entrypoints.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import platform
from pathlib import Path
from typing import Any

from .. import logger, paste, update as manifest_update, updater
from ..menus import (
    ensure_unique_ids,
    list_styles,
    list_prompts,
    load_template,
    PROMPTS_DIR,
)
from ..variables import (
    reset_file_overrides,
    reset_single_file_override,
    list_file_overrides,
)

from .dependencies import check_dependencies, dependency_status
from .template_select import select_template_cli, pick_prompt_cli
from .render import render_template_cli
from ..gui.file_append import _append_to_files
from .update import perform_update


class PromptCLI:
    """High level command line interface controller."""

    def __init__(self) -> None:
        self.log_dir = Path.home() / ".prompt-automation" / "logs"
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.log_file = self.log_dir / "cli.log"
        self._log = logging.getLogger("prompt_automation.cli")
        if not self._log.handlers:
            # Elevate to DEBUG when troubleshooting is enabled via env var
            level = logging.DEBUG if os.environ.get("PROMPT_AUTOMATION_DEBUG") else logging.INFO
            self._log.setLevel(level)
            try:
                self._log.addHandler(logging.FileHandler(self.log_file))
            except Exception:
                self._log.addHandler(logging.StreamHandler())

    # Expose helper functions as methods for convenience
    check_dependencies = staticmethod(check_dependencies)
    dependency_status = staticmethod(dependency_status)
    select_template_cli = staticmethod(select_template_cli)
    pick_prompt_cli = staticmethod(pick_prompt_cli)
    render_template_cli = staticmethod(render_template_cli)
    _append_to_files = staticmethod(_append_to_files)

    def main(self, argv: list[str] | None = None) -> None:
        """Program entry point."""
        # Load environment from config file if it exists
        config_dir = Path.home() / ".prompt-automation"
        env_file = config_dir / "environment"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

        parser = argparse.ArgumentParser(prog="prompt-automation")
        parser.add_argument(
            "--troubleshoot", action="store_true", help="Show troubleshooting help and paths"
        )
        parser.add_argument(
            "--version", action="store_true", help="Print version and exit"
        )
        parser.add_argument(
            "--prompt-dir", type=Path, help="Directory containing prompt templates"
        )
        parser.add_argument(
            "--list", action="store_true", help="List available prompt styles and templates"
        )
        parser.add_argument(
            "--tree",
            action="store_true",
            help="Render hierarchical tree when used with --list (opt-in)",
        )
        parser.add_argument(
            "--flat",
            action="store_true",
            help="Force flat listing (overrides feature flag)",
        )
        parser.add_argument(
            "--reset-log", action="store_true", help="Clear usage log database"
        )
        parser.add_argument(
            "--reset-file-overrides",
            action="store_true",
            help="Clear stored reference file paths & skip flags",
        )
        parser.add_argument(
            "--reset-one-override",
            nargs=2,
            metavar=("TEMPLATE_ID", "NAME"),
            help="Reset a single placeholder override",
        )
        parser.add_argument(
            "--list-overrides", action="store_true", help="List current file/skip overrides"
        )
        parser.add_argument("--gui", action="store_true", help="Launch GUI (default)")
        parser.add_argument(
            "--terminal", action="store_true", help="Force terminal mode instead of GUI"
        )
        parser.add_argument(
            "--focus", action="store_true", help="Focus existing GUI instance if running (no new window)"
        )
        parser.add_argument(
            "--update", "-u", action="store_true", help="Check for and apply updates"
        )
        parser.add_argument(
            "--self-test",
            action="store_true",
            help="Run dependency and template health checks and exit",
        )
        parser.add_argument(
            "--espanso-sync",
            action="store_true",
            help="Validate, mirror, and update the espanso package, then restart",
        )
        parser.add_argument(
            "--espanso-skip-install",
            action="store_true",
            help="Skip espanso install/update (validate+mirror only)",
        )
        parser.add_argument(
            "--espanso-auto-bump",
            choices=("off", "patch"),
            default=None,
            help="Auto-bump patch version before mirroring",
        )
        parser.add_argument(
            "--espanso-clean",
            action="store_true",
            help="Backup and remove local espanso match files and uninstall legacy/conflicting packages",
        )
        parser.add_argument(
            "--espanso-clean-deep",
            action="store_true",
            help="Deep clean: backup and remove ALL local match/*.yml (not just base.yml)",
        )
        parser.add_argument(
            "--espanso-clean-list",
            action="store_true",
            help="List local match files and installed packages (no changes)",
        )
        parser.add_argument(
            "--espanso-reset",
            action="store_true",
            help="One-shot: deep clean local matches + uninstall legacy packages, then sync",
        )
        parser.add_argument(
            "--assign-hotkey",
            action="store_true",
            help="Interactively set or change the global GUI hotkey",
        )
        parser.add_argument(
            "--hotkey-status",
            action="store_true",
            help="Show current hotkey and platform integration status",
        )
        parser.add_argument(
            "--hotkey-repair",
            action="store_true",
            help="Re-write hotkey integration files and verify (safe)",
        )
        parser.add_argument(
            "--theme",
            choices=["light", "dark", "system"],
            help="Override theme for this run (does not persist)",
        )
        parser.add_argument(
            "--persist-theme",
            action="store_true",
            help="Persist the provided --theme value to settings.json",
        )
        parser.add_argument(
            "--hierarchy",
            choices=["on", "off"],
            help="Enable or disable hierarchical templates for this run (mimics theme toggle)",
        )
        parser.add_argument(
            "--persist-hierarchy",
            action="store_true",
            help="Persist the provided --hierarchy value to settings.json",
        )
        parser.add_argument(
            "--show-reminders",
            action="store_true",
            help="Print reminders for a selected template and exit (no prompting)",
        )
        args = parser.parse_args(argv)

        if args.version:
            try:
                from importlib.metadata import version as _dist_version
                print(f"prompt-automation { _dist_version('prompt-automation') }")
            except Exception:
                print("prompt-automation (version unknown)")
            return

        if args.prompt_dir:
            path = args.prompt_dir.expanduser().resolve()
            os.environ["PROMPT_AUTOMATION_PROMPTS"] = str(path)
            self._log.info("using custom prompt directory %s", path)

        if args.assign_hotkey:
            from .. import hotkeys

            hotkeys.assign_hotkey()
            return

        if args.hotkey_status:
            from .hotkey_cmds import show_hotkey_status
            show_hotkey_status()
            return

        if args.hotkey_repair:
            from .hotkey_cmds import repair_hotkey
            repair_hotkey()
            return

        if args.update:
            perform_update(args)
            return

        if args.espanso_sync:
            # Delegate to module to keep concerns isolated
            from .. import espanso_sync as _esp
            argv: list[str] = []
            if args.espanso_skip_install:
                argv.append("--skip-install")
            if args.espanso_auto_bump:
                argv.extend(["--auto-bump", args.espanso_auto_bump])
            _esp.main(argv)
            return

        if args.espanso_clean or args.espanso_clean_list or args.espanso_clean_deep:
            from .espanso_cmds import clean_env
            clean_env(list_only=args.espanso_clean_list, deep=args.espanso_clean_deep)
            return

        if args.espanso_reset:
            # Deep clean and then run sync using the same orchestrator entry
            from .espanso_cmds import clean_env
            from .. import espanso_sync as _esp
            clean_env(list_only=False, deep=True)
            _esp.main([])
            return

        try:
            # Use importlib to load package module for stable patching/import behavior
            import importlib
            _cli_pkg = importlib.import_module('prompt_automation.cli')
            _cli_pkg.ensure_unique_ids(PROMPTS_DIR)
        except ValueError as e:
            print(f"[prompt-automation] {e}")
            return

        if args.self_test:
            from .self_test import run_self_test
            gui_mode = not args.terminal and (
                args.gui or os.environ.get("PROMPT_AUTOMATION_GUI") != "0"
            )
            run_self_test(gui_mode)
            return

        if args.reset_log:
            from .overrides import clear_usage_log
            clear_usage_log()
            return
        if args.reset_file_overrides:
            from .overrides import clear_all_overrides
            clear_all_overrides()
            return
        if args.reset_one_override:
            from .overrides import clear_one_override
            tid, name = args.reset_one_override
            clear_one_override(tid, name)
            return
        if args.list_overrides:
            from .overrides import show_overrides
            show_overrides()
            return

        if args.list:
            # If --tree provided (or feature flag enabled and not overridden by --flat) use hierarchical view
            try:
                from ..features import is_hierarchy_enabled
                use_tree = (args.tree or is_hierarchy_enabled()) and not args.flat
            except Exception:
                use_tree = args.tree and not args.flat
            if use_tree:
                from ..services.hierarchy import TemplateHierarchyScanner, HierarchyNode
                scanner = TemplateHierarchyScanner()
                tree = scanner.scan()

                def _print(node: HierarchyNode, indent: int = 0) -> None:
                    prefix = "  " * indent
                    if node.type == "folder" and node.name:
                        print(f"{prefix}{node.name}/")
                    for ch in node.children:
                        if ch.type == "folder":
                            _print(ch, indent + 1)
                        else:
                            print(f"{prefix}  {Path(ch.relpath).name}")

                _print(tree)
            else:
                for style in list_styles():
                    print(style)
                    for tmpl_path in list_prompts(style):
                        print("  ", tmpl_path.name)
            return

        if args.troubleshoot:
            print(
                "Troubleshooting tips:\n- Ensure dependencies are installed.\n- Logs stored at",
                self.log_dir,
                "\n- Usage DB:",
                logger.DB_PATH,
            )
            return

        gui_mode = not args.terminal and (
            args.gui or os.environ.get("PROMPT_AUTOMATION_GUI") != "0" or args.focus
        )

        # Observability: log the incoming event and intended mode
        try:
            self._log.debug(
                "hotkey_event_received source=CLI focus=%s gui=%s terminal=%s",
                bool(args.focus), bool(args.gui), bool(args.terminal),
            )
        except Exception:
            pass

        self._log.info("running on %s", platform.platform())

        # Fast path: try to focus existing GUI instance before any dependency checks
        if gui_mode:
            try:
                from ..gui.single_window import singleton as _sw_singleton
                self._log.debug("hotkey_handler_invoked action=focus_app_attempt")
                if _sw_singleton.connect_and_focus_if_running():
                    try:
                        self._log.debug("hotkey_handler_invoked action=focus_app")
                    except Exception:
                        pass
                    return
            except Exception:
                pass

        import importlib
        _cli_pkg = importlib.import_module('prompt_automation.cli')
        if not _cli_pkg.check_dependencies(require_fzf=not gui_mode):
            return
        from ..dev import is_dev_mode
        if not is_dev_mode():
            try:  # never block startup
                updater.check_for_update()
            except Exception:
                pass
            manifest_update.check_and_prompt()
        # Theme resolution: allow CLI override and optional persistence
        try:
            if args.theme:
                if args.persist_theme:
                    from ..theme import resolve as _tres
                    _tres.set_user_theme_preference(args.theme)
                else:
                    os.environ['PROMPT_AUTOMATION_THEME'] = args.theme
            if args.hierarchy:
                # Map to boolean
                enabled = args.hierarchy == "on"
                if args.persist_hierarchy:
                    from ..features import set_user_hierarchy_preference as _set_h
                    _set_h(enabled)
                else:
                    os.environ['PROMPT_AUTOMATION_HIERARCHICAL_TEMPLATES'] = "1" if enabled else "0"
        except Exception:
            pass

        if gui_mode:
            from .. import gui
            try:
                self._log.debug("hotkey_handler_invoked action=show_app")
            except Exception:
                pass
            gui.run()
            return

        banner = Path(__file__).resolve().parent.parent / "resources" / "banner.txt"
        print(banner.read_text())

        try:
            self._log.debug("hotkey_handler_invoked action=terminal")
        except Exception:
            pass

        tmpl: dict[str, Any] | None = select_template_cli()
        if not tmpl:
            return

        # Fast inspection path: print reminders and exit
        if args.show_reminders:
            try:
                from ..reminders import extract_template_reminders, partition_placeholder_reminders
                tlist = extract_template_reminders(tmpl)
                phs = tmpl.get("placeholders") or []
                pmap = partition_placeholder_reminders(phs, tlist)
                if tlist:
                    print("Reminders:")
                    for s in tlist:
                        print(f" - {s}")
                else:
                    print("Reminders: (none)")
                if pmap:
                    print("\nPlaceholder Reminders:")
                    for name, items in pmap.items():
                        print(f" [{name}]")
                        for s in items:
                            print(f"  - {s}")
                return
            except Exception as e:
                print(f"[prompt-automation] Failed to print reminders: {e}")
                return

        res = render_template_cli(tmpl)
        if res:
            text, var_map = res
            print("\n" + "=" * 60)
            try:
                from ..theme import resolve as _tres, model as _tmodel, apply as _tapply
                _name = _tres.ThemeResolver(_tres.get_registry()).resolve()
                _theme = _tmodel.get_theme(_name)
                heading = _tapply.format_heading("RENDERED OUTPUT:", _theme)
            except Exception:
                heading = "RENDERED OUTPUT:"
            print(heading)
            print("=" * 60)
            print(text)
            print("=" * 60)

            # Append to recent history (non-intrusive; ignore failures)
            try:
                from ..history import record_history
                record_history(tmpl, rendered_text=text, final_output=text)
            except Exception:
                pass

            if input("\nProceed with clipboard copy? [Y/n]: ").lower() not in {"n", "no"}:
                paste.copy_to_clipboard(text)
                print(
                    "\n[prompt-automation] Text copied to clipboard. Press Ctrl+V to paste where needed."
                )
                _append_to_files(var_map, text)
                logger.log_usage(tmpl, len(text))


__all__ = ["PromptCLI"]
