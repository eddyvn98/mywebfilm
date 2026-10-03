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


def test_player_reexports_navigation_and_modal_contract():
    player = read('static/js/player.js')
    for symbol in [
        'playNext',
        'playPrev',
        'openMediaAtIndex',
        'openImageModal',
        'closeImageModal',
    ]:
        assert symbol in player, f'player.js missing export {symbol}'


def test_filter_service_imports_history_service():
    filter_service = read('static/js/filter_service.js')
    assert "import { historyService } from './history_service.js';" in filter_service


def test_all_js_module_named_imports_resolve():
    import glob
    import re

    js_files = glob.glob('static/js/*.js')
    exports_by_file = {}

    for path in js_files:
        fname = path.replace('\\', '/').split('/')[-1]
        content = read(path)
        exports = set()
        for m in re.finditer(r'export\s+(?:async\s+)?(?:function\*?|class)\s+([a-zA-Z0-9_$]+)', content):
            exports.add(m.group(1))
        for m in re.finditer(r'export\s+(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=', content):
            exports.add(m.group(1))
        for m in re.finditer(r'export\s+(?:const|let|var)\s*\{([^}]+)\}\s*=', content):
            for item in m.group(1).split(','):
                sym = item.strip().split(':')[0].strip()
                if sym:
                    exports.add(sym)
        for m in re.finditer(r'export\s*\{([^}]+)\}', content):
            for item in m.group(1).split(','):
                parts = item.strip().split()
                if not parts:
                    continue
                if len(parts) == 1:
                    exports.add(parts[0])
                elif len(parts) >= 3 and parts[-2] == 'as':
                    exports.add(parts[-1])
        exports_by_file[fname] = exports

    for path in js_files:
        fname = path.replace('\\', '/').split('/')[-1]
        content = read(path)
        for m in re.finditer(r'import\s*\{([^}]+)\}\s*from\s*[\'"]\./([a-zA-Z0-9_.-]+\.js)[\'"]', content):
            imported_symbols = [s.strip().split()[0] for s in m.group(1).split(',') if s.strip()]
            target_file = m.group(2)
            assert target_file in exports_by_file, f'{fname} imports missing module {target_file}'
            for sym in imported_symbols:
                assert sym in exports_by_file[target_file], f'{fname} imports "{sym}" from {target_file}, but {target_file} only exports {exports_by_file[target_file]}'

