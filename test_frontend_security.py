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
