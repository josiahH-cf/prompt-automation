def test_search_delegates(monkeypatch):
    from prompt_automation.gui.selector import service

    marker = object()

    def fake_search(q, recursive=True):
        return [marker, q, recursive]

    monkeypatch.setattr(service.template_search_service, "search", fake_search)
    assert service.search("hi", recursive=False) == [marker, "hi", False]


def test_overrides_delegate(monkeypatch):
    from prompt_automation.gui.selector import service

    marker = [(1, "name", {})]
    monkeypatch.setattr(
        service.overrides_service, "list_file_overrides", lambda: marker
    )
    assert service.list_file_overrides() is marker


def test_exclusions_delegate(monkeypatch):
    from prompt_automation.gui.selector import service

    marker = ["a"]
    monkeypatch.setattr(service.exclusions_service, "load_exclusions", lambda tid: marker)
    assert service.load_exclusions(5) is marker

