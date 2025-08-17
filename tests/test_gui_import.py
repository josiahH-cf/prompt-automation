import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

def test_gui_run_available():
    import prompt_automation.gui as gui
    assert hasattr(gui, 'run'), 'prompt_automation.gui.run missing'

def test_menus_nested_import():
    # Create a temporary nested prompt structure and ensure listing works
    import json, tempfile, shutil
    import prompt_automation.config as config
    from prompt_automation.menus import list_styles, list_prompts

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        styles_root = root / 'styles'
        style_dir = styles_root / 'TestStyle' / 'SubDir'
        style_dir.mkdir(parents=True)
        tmpl = {
            'id': 1,
            'title': 'Nested Template',
            'style': 'TestStyle',
            'template': ['Hello {{name}}'],
            'placeholders': [{'name': 'name'}],
        }
        (style_dir / '01_nested-template.json').write_text(json.dumps(tmpl))
        # Point PROMPTS_DIR to styles root (production layout)
        config.PROMPTS_SEARCH_PATHS[:] = [styles_root]  # type: ignore
        config.PROMPTS_DIR = styles_root  # type: ignore
        styles = list_styles()
        assert 'TestStyle' in styles
        prompts = list_prompts('TestStyle')
        assert any(p.name.endswith('nested-template.json') for p in prompts)
