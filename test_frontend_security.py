from pathlib import Path


def read(path):
    return Path(path).read_text(encoding='utf-8')


def test_security_helpers_are_used_by_dynamic_renderers():
    for path in [
        'static/js/render_service.js',
        'static/js/player.js',
        'static/js/main.js',
        'static/js/mgmt_ui_service.js',
        'static/js/discovery_service.js',
        'static/js/filter_service.js',
        'static/js/queue_service.js',
        'static/js/ai_search_service.js',
    ]:
        assert "./security.js" in read(path), path


def test_known_unescaped_dynamic_html_patterns_are_absent():
    checks = {
        'static/js/render_service.js': [
            "filterByFolder('${f}')",
            '${(f || \'GỐC\').toUpperCase()}',
            'data-preview-url="${getPreviewUrl(v.full_path)}"',
        ],
        'static/js/player.js': [
            '<b>${v.name}</b>',
            "playExternal('${v.full_path.replace",
        ],
        'static/js/queue_service.js': ['>${activeItem.name}</span>'],
        'static/js/ai_search_service.js': ['>${intentMsg}</p>', '"${query}"</p>'],
    }
    for path, forbidden in checks.items():
        source = read(path)
        for pattern in forbidden:
            assert pattern not in source, f'{path} still contains unsafe pattern: {pattern}'


def test_legacy_frontend_pin_gate_is_not_wired_into_app():
    main = read('static/js/main.js')
    home = read('templates/cinema_home.html')
    state = read('static/js/state.js')

    assert "./auth.js" not in main
    assert "sessionStorage.getItem('cinema_authenticated')" not in main
    assert "pin_overlay.html" not in home
    assert "correctPin" not in state
    assert "currentPinInput" not in state


def test_security_client_is_initialized():
    main = read('static/js/main.js')
    home = read('templates/cinema_home.html')

    assert "./security_client.js" in main
    assert "initSecurityClient()" in main
    assert "security_modal.html" in home
