from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def test_large_library_grid_is_not_rendered_twice_on_initial_load():
    source = read("static/js/main.js")
    load_library = source[source.index("async function loadLibrary()"):source.index("async function init()")]
    assert "renderGrid(videos);" not in load_library
    assert "Promise.all([" in load_library
    assert "favoritesService.loadFavorites()," in load_library
    assert "applyFilters();" in load_library


def test_search_filtering_is_debounced():
    source = read("static/js/grid.js")
    assert "searchFilterTimeout" in source
    assert "setTimeout(() =>" in source
    assert "applyFilters(...args);" in source


def test_category_counts_are_built_in_one_pass():
    source = read("static/js/filter_service.js")
    assert "const categoryCounts = new Map();" in source
    assert "categoryCounts.set(c, (categoryCounts.get(c) || 0) + 1);" in source
    assert "state.allVideos.filter(v => v.categories?.includes(val)).length" not in source


def test_playlist_is_windowed_instead_of_rendering_entire_library():
    source = read("static/js/player.js")
    assert "const PLAYLIST_WINDOW_RADIUS = 40;" in source
    assert "state.currentGridVideos.slice(start, end)" in source
    assert "window.pagePlaylist" in source
    assert "Nạp phim trước" in source
    assert "Nạp phim tiếp" in source
    assert "state.currentGridVideos.map((v, i)" not in source


def test_swipe_seek_commits_once_on_gesture_end():
    source = read("static/js/gestures.js")
    move_start = source.index("const moveAction")
    end_start = source.index("const endAction")
    move_block = source[move_start:end_start]
    end_block = source[end_start:source.index("window.addEventListener('mousedown'")]

    assert "pendingSeekTime =" in move_block
    assert "state.player.currentTime =" not in move_block
    assert "const seekTarget = pendingSeekTime;" in end_block
    assert "state.player.currentTime = seekTarget;" in end_block


def test_timeline_is_not_rebuilt_for_each_infinite_scroll_page():
    source = read("static/js/render_service.js")
    assert "if (!append) {\n        renderTimeline(videos);\n    }" in source


def test_movie_cards_enable_offscreen_render_skipping():
    source = read("static/css/style.css")
    assert "content-visibility: auto;" in source
    assert "contain-intrinsic-size:" in source


def test_empty_search_skips_expensive_text_normalization():
    source = read("static/js/filter_service.js")
    assert "if (search) {" in source
    assert "let matchesSearch = true;" in source


def test_dynamic_categories_are_memoized_for_same_library():
    source = read("static/js/filter_service.js")
    assert "let categorySource = null;" in source
    assert "categorySource === state.allVideos" in source


def test_favorites_use_set_membership():
    source = read("static/js/favorites_service.js")
    assert "favoritePaths: new Set()" in source
    assert "this.favoritePaths.has(path)" in source


def test_hover_preview_is_delayed_and_single_active():
    source = read("static/js/manage_service.js")
    assert "const previewTimers = new WeakMap();" in source
    assert "let activePreviewCard = null;" in source
    assert "}, 450);" in source
    assert "window.matchMedia('(hover: hover)')" in source


def test_thumbnails_decode_asynchronously():
    grid = read("static/js/render_service.js")
    player = read("static/js/player.js")
    assert 'decoding="async"' in grid
    assert 'decoding="async"' in player


def test_manage_mode_does_not_rebuild_loaded_grid():
    source = read("static/js/selection_service.js")
    assert "manage-mode-active" in source
    assert "renderGrid(state.currentGridVideos, false, false)" not in source


def test_favorite_toggle_updates_card_without_grid_rerender():
    grid = read("static/js/grid.js")
    player = read("static/js/player.js")
    assert "renderGrid(state.currentGridVideos, false, false)" not in grid
    assert "import('./render_service.js')" not in player
    assert "CSS.escape(video.full_path)" in player


def test_player_only_forces_layout_when_modal_is_initially_opened():
    source = read("static/js/player.js")
    assert "const isOpeningModal = modal.classList.contains('hidden');" in source
    assert "if (isOpeningModal) {" in source
    assert "void modal.offsetWidth;" in source


def test_fast_swipes_delay_history_writes():
    source = read("static/js/player.js")
    assert "const HISTORY_RECORD_DELAY_MS = 1500;" in source
    assert "scheduleHistoryRecord(v);" in source
    assert "clearTimeout(historyRecordTimer);" in source


def test_startup_defers_background_sort_work():
    source = read("static/js/main.js")
    assert "requestIdleCallback" in source
    assert "scheduleBackgroundSort" in source


def test_movie_cards_avoid_per_item_backdrop_blur():
    source = read("static/js/render_service.js")
    assert "bg-black/40 backdrop-blur-md" not in source
    assert "font-bold backdrop-blur-sm" not in source


def test_preview_generation_is_low_contention_and_faststart():
    source = read("ffmpeg_service.py")
    preview_start = source.index("def generate_preview")
    preview_end = source.index("def check_ffmpeg_presence")
    preview_block = source[preview_start:preview_end]
    assert "'-threads', '1'" in preview_block
    assert "'-movflags', '+faststart'" in preview_block


def test_cinema_ui_requests_compact_catalog():
    source = read("static/js/api.js")
    assert "fetch('/api/videos?compact=1')" in source


def test_scroll_state_uses_grid_container_not_window():
    grid = read("static/js/grid.js")
    state = read("static/js/state.js")
    renderer = read("static/js/render_service.js")
    back_to_top = read("templates/components/back_to_top.html")

    assert "gridScrollEl?.addEventListener('scroll'" in grid
    assert "window.addEventListener('scroll'" not in grid
    assert "scrollPos: state.scrollPos || 0" in state
    assert "getElementById('video-grid')?.scrollTo" in renderer
    assert "getElementById('video-grid')?.scrollTo" in back_to_top


def test_history_service_does_not_refetch_after_each_record():
    source = read("static/js/history_service.js")
    assert "this.loadHistory()" not in source


def test_playlist_previous_page_keeps_windows_contiguous():
    source = read("static/js/player.js")
    assert "boundaryIndex - PLAYLIST_WINDOW_RADIUS - 1" in source
    assert "boundaryIndex - jump" not in source


def test_security_client_initialization_is_idempotent():
    source = read("static/js/security_client.js")
    assert "let securityClientInitialized = false;" in source
    assert "if (securityClientInitialized) return;" in source


def test_selection_toolbar_is_rendered_once():
    source = read("templates/cinema_home.html")
    assert source.count("{% include 'components/selection_toolbar.html' %}") == 1


def test_queue_polling_does_not_rerender_grid_for_internal_state_only():
    source = read("static/js/queue_service.js")
    assert "applyFilters" not in source
