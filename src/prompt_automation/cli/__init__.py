"""CLI package providing the :class:`PromptCLI` entry point."""
from __future__ import annotations

import argparse
import json
import logging
import os
import platform
from pathlib import Path
from typing import Any

from .. import logger, menus, paste, update as manifest_update, updater
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
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "cli.log"
        self._log = logging.getLogger("prompt_automation.cli")
        if not self._log.handlers:
            self._log.setLevel(logging.INFO)
            self._log.addHandler(logging.FileHandler(self.log_file))

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
            "--prompt-dir", type=Path, help="Directory containing prompt templates"
        )
        parser.add_argument(
            "--list", action="store_true", help="List available prompt styles and templates"
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
            "--update", "-u", action="store_true", help="Check for and apply updates"
        )
        parser.add_argument(
            "--self-test",
            action="store_true",
            help="Run dependency and template health checks and exit",
        )
        parser.add_argument(
            "--assign-hotkey",
            action="store_true",
            help="Interactively set or change the global GUI hotkey",
        )
        args = parser.parse_args(argv)

        if args.prompt_dir:
            path = args.prompt_dir.expanduser().resolve()
            os.environ["PROMPT_AUTOMATION_PROMPTS"] = str(path)
            self._log.info("using custom prompt directory %s", path)

        if args.assign_hotkey:
            from .. import hotkeys

            hotkeys.assign_hotkey()
            return

        if args.update:
            perform_update(args)
            return

        try:
            menus.ensure_unique_ids(menus.PROMPTS_DIR)
        except ValueError as e:
            print(f"[prompt-automation] {e}")
            return

        if args.self_test:
            styles = menus.list_styles()
            template_files: list[Path] = []
            for s in styles:
                for p in menus.list_prompts(s):
                    try:
                        data = menus.load_template(p)
                        if isinstance(data, dict) and "template" in data:
                            template_files.append(p)
                    except Exception:
                        pass
            gui_mode = not args.terminal and (
                args.gui or os.environ.get("PROMPT_AUTOMATION_GUI") != "0"
            )
            dep_status = dependency_status(gui_mode)
            missing_critical = [
                k for k, v in dep_status.items() if v["status"] == "missing"
            ]
            print("=== Self Test Report ===")
            print(f"Styles: {len(styles)} | Templates: {len(template_files)}")
            print("Dependencies:")
            for name, info in sorted(dep_status.items()):
                detail = info["detail"]
                print(
                    f"  - {name}: {info['status']} {('- ' + detail) if detail else ''}"
                )
            if missing_critical:
                print("Critical missing dependencies:", ", ".join(missing_critical))
                print("Self test: FAIL")
            else:
                print("Self test: PASS")
            return

        if args.reset_log:
            logger.clear_usage_log()
            print("[prompt-automation] usage log cleared")
            return
        if args.reset_file_overrides:
            if reset_file_overrides():
                print("[prompt-automation] reference file overrides cleared")
            else:
                print("[prompt-automation] no overrides to clear")
            return
        if args.reset_one_override:
            tid, name = args.reset_one_override
            if not tid.isdigit():
                print("[prompt-automation] TEMPLATE_ID must be an integer")
                return
            removed = reset_single_file_override(int(tid), name)
            if removed:
                print(
                    f"[prompt-automation] override removed for template {tid} placeholder '{name}'"
                )
            else:
                print(
                    f"[prompt-automation] no override found for template {tid} placeholder '{name}'"
                )
            return
        if args.list_overrides:
            rows = list_file_overrides()
            if not rows:
                print("[prompt-automation] no overrides present")
            else:
                print("TemplateID | Placeholder | Data")
                for tid, name, info in rows:
                    print(f"{tid:>9} | {name:<12} | {json.dumps(info)}")
            return

        if args.list:
            for style in menus.list_styles():
                print(style)
                for tmpl_path in menus.list_prompts(style):
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
            args.gui or os.environ.get("PROMPT_AUTOMATION_GUI") != "0"
        )

        self._log.info("running on %s", platform.platform())
        if not check_dependencies(require_fzf=not gui_mode):
            return
        try:  # never block startup
            updater.check_for_update()
        except Exception:
            pass
        manifest_update.check_and_prompt()

        if gui_mode:
            from .. import gui

            gui.run()
            return

        banner = Path(__file__).resolve().parent.parent / "resources" / "banner.txt"
        print(banner.read_text())

        tmpl: dict[str, Any] | None = select_template_cli()
        if not tmpl:
            return

        res = render_template_cli(tmpl)
        if res:
            text, var_map = res
            print("\n" + "=" * 60)
            print("RENDERED OUTPUT:")
            print("=" * 60)
            print(text)
            print("=" * 60)

            if input("\nProceed with clipboard copy? [Y/n]: ").lower() not in {"n", "no"}:
                paste.copy_to_clipboard(text)
                print(
                    "\n[prompt-automation] Text copied to clipboard. Press Ctrl+V to paste where needed."
                )
                _append_to_files(var_map, text)
                logger.log_usage(tmpl, len(text))


__all__ = ["PromptCLI"]

