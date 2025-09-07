from __future__ import annotations

import pathlib


def test_manifest_name_matches_external_layout_and_ci():
    repo = pathlib.Path(__file__).resolve().parents[2]
    src_manifest = repo / 'espanso-package' / '_manifest.yml'
    assert src_manifest.exists(), 'missing espanso-package/_manifest.yml'
    import yaml
    name = yaml.safe_load(src_manifest.read_text()).get('name')
    assert name == 'prompt-automation', 'manifest name should be prompt-automation'

    # External layout should exist at packages/<name>
    ext_base = repo / 'packages' / name
    assert ext_base.exists(), f"external layout packages/{name} missing"

    # CI workflow should reference the same path
    wf = (repo / '.github' / 'workflows' / 'espanso-package.yml').read_text()
    assert f'packages/{name}' in wf
    assert 'packages/your-pa' not in wf

