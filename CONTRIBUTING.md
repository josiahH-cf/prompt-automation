# Contributing

Thanks for wanting to contribute!

## Development Setup

Install the package locally for development:

```bash
pip install -e .
```

## Submitting Pull Requests

1. Fork the repository and create a feature branch.
2. Run `python -m build` to ensure the package builds.
3. Open a pull request describing the changes and reference any related issues.

Happy hacking!

## File Size and Refactoring Policy

- Avoid committing files larger than 500 KB. Use compression or external hosting for sizable assets.
- Keep individual source modules focused and roughly under 400 lines; split functionality across packages when they grow.
- Discuss major refactors in an issue before starting and land them in small, reviewable commits.

## Espanso Snippets

- Edit snippets only under `espanso-package/match/*.yml`.
- Keep triggers namespaced (e.g., `:pa.*`) and free of spaces; tests enforce basic hygiene and duplicate detection.
- Bump version in `espanso-package/_manifest.yml` when changing snippets (SemVer).
- Validate locally: `pytest -q tests/espanso`.
- Mirror to the distribution layout and install/update via the runbook:

```bash
bash scripts/espanso-package-runbook.sh    # set BUMP_VERSION=true to bump patch automatically
```
