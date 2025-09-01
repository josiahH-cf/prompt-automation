import tomllib


def test_no_conflicting_console_script_alias():
    # Ensure our console entry points do not shadow the package name
    # which can cause import issues on Windows.
    with open("pyproject.toml", "rb") as fh:
        data = tomllib.load(fh)

    scripts = data.get("project", {}).get("scripts", {})

    # Primary console script remains
    assert "prompt-automation" in scripts
    # Short alias remains
    assert "pa" in scripts

    # Critically, no alias using the package name with underscore
    # to avoid import shadowing like `import prompt_automation`.
    assert "prompt_automation" not in scripts

