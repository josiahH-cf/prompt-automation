from prompt_automation import menus, renderer


def test_consolidation():
    assert menus.PROMPTS_DIR.exists()
    styles = menus.list_styles()
    assert styles
    prompts = menus.list_prompts(styles[0])
    if prompts:
        data = renderer.load_template(prompts[0])
        assert renderer.validate_template(data)
