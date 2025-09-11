from pathlib import Path

import prompt_automation.cli.__init__ as cli_mod
import prompt_automation.cli.controller as controller
from prompt_automation.services import hierarchy
from prompt_automation.services.hierarchy import HierarchyNode
from pathlib import Path


def test_cli_list_filter_flat(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    monkeypatch.setattr(controller, 'list_styles', lambda: ['A', 'B'])

    def _list_prompts(style: str):
        if style == 'A':
            return [Path('A/one.json'), Path('A/two.json')]
        return [Path('B/other.json')]

    monkeypatch.setattr(controller, 'list_prompts', _list_prompts)
    cli = cli_mod.PromptCLI()
    cli.main(['--list', '--flat', '--filter', 'two'])
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ['A', '  two.json']


def test_cli_list_filter_tree(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)

    class DummyScanner:
        def scan(self):
            return HierarchyNode(
                type='folder',
                name='',
                relpath='',
                children=[
                    HierarchyNode(type='template', name='alpha.json', relpath='alpha.json'),
                    HierarchyNode(type='template', name='beta.json', relpath='beta.json'),
                ],
            )

    monkeypatch.setattr(hierarchy, 'TemplateHierarchyScanner', lambda: DummyScanner())
    cli = cli_mod.PromptCLI()
    cli.main(['--list', '--tree', '--filter', 'beta'])
    out = capsys.readouterr().out.splitlines()
    assert out == ['  beta.json']


def test_cli_list_filter_case_insensitive(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    monkeypatch.setattr(controller, 'list_styles', lambda: ['A'])

    def _list_prompts(style: str):
        return [Path('A/Alpha.json'), Path('A/Beta.json')]

    monkeypatch.setattr(controller, 'list_prompts', _list_prompts)
    cli = cli_mod.PromptCLI()
    cli.main(['--list', '--flat', '--filter', 'ALPHA'])
    out = capsys.readouterr().out.splitlines()
    assert out == ['A', '  Alpha.json']


def test_cli_list_filter_no_match(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    monkeypatch.setattr(controller, 'list_styles', lambda: ['A'])
    monkeypatch.setattr(controller, 'list_prompts', lambda style: [Path('A/one.json')])
    cli = cli_mod.PromptCLI()
    cli.main(['--list', '--flat', '--filter', 'zzz'])
    out = capsys.readouterr().out.strip().splitlines()
    assert out == []


def test_cli_list_filter_tree_folder(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)

    class DummyScanner:
        def scan(self):
            return HierarchyNode(
                type='folder',
                name='',
                relpath='',
                children=[
                    HierarchyNode(type='folder', name='Docs', relpath='Docs', children=[
                        HierarchyNode(type='template', name='readme.json', relpath='Docs/readme.json'),
                        HierarchyNode(type='template', name='guide.json', relpath='Docs/guide.json'),
                    ]),
                    HierarchyNode(type='template', name='misc.json', relpath='misc.json'),
                ],
            )

    monkeypatch.setattr(hierarchy, 'TemplateHierarchyScanner', lambda: DummyScanner())
    cli = cli_mod.PromptCLI()
    cli.main(['--list', '--tree', '--filter', 'docs'])
    out = capsys.readouterr().out.splitlines()
    assert out == ['  Docs/', '    readme.json', '    guide.json']
