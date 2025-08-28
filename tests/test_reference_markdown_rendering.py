import json
from pathlib import Path

from prompt_automation.menus import render_template


def _make_template(tmp_path: Path, lines):
    tfile = tmp_path / 'tmpl.json'
    tfile.write_text(json.dumps({
        'schema': 1,
        'id': 101,
        'title': 'md-ref-mid',
        'style': 'unit',
        'template': lines,
        'placeholders': [
            {'name': 'reference_file', 'type': 'file', 'label': 'Ref', 'render': 'markdown'}
        ],
        'metadata': {'path': 'unit/md-ref-mid.json'}
    }))
    return tfile


def test_reference_markdown_midsequence_collapsible(tmp_path, monkeypatch):
    # Prepare a markdown file to act as reference
    md = tmp_path / 'ref.md'
    md.write_text('# Heading\n\nSome **bold** text\n\n```\ncode\n```\n')

    # Build a template where reference appears mid-sequence
    tf = _make_template(tmp_path, [
        'Intro section',
        '{{reference_file}}',
        'Outro section',
    ])

    # Wire PROMPTS_DIR to temp so loader can resolve metadata.path if needed
    from prompt_automation import config as cfg
    monkeypatch.setattr(cfg, 'PROMPTS_DIR', tmp_path)

    # Provide raw vars indicating the selected file path
    rendered, _ = render_template(
        json.loads(tf.read_text()),
        values={'reference_file': str(md)},
        return_vars=True,
    )

    # Expected new behavior (red first): mid-sequence reference renders as a collapsible block.
    # We assert presence of a marker or details wrapper; current implementation returns raw markdown only.
    assert '<details' in rendered or 'BEGIN_REFERENCE(collapsed)' in rendered


def test_reference_markdown_end_expanded(tmp_path, monkeypatch):
    md = tmp_path / 'ref.md'
    md.write_text('## Subheading\nContent')

    tf = _make_template(tmp_path, [
        'Intro',
        '{{reference_file}}',
    ])

    from prompt_automation import config as cfg
    monkeypatch.setattr(cfg, 'PROMPTS_DIR', tmp_path)

    rendered, _ = render_template(
        json.loads(tf.read_text()),
        values={'reference_file': str(md)},
        return_vars=True,
    )

    # End-of-sequence: should be expanded (no collapsible wrapper marker)
    assert '<details' not in rendered and 'BEGIN_REFERENCE(collapsed)' not in rendered

