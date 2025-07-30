from prompt_automation import menus


def test_freq_sorted():
    names = ["b", "a", "c"]
    freq = {"a": 2, "c": 5}
    ordered = menus._freq_sorted(names, freq)
    assert ordered == ["c", "a", "b"]
