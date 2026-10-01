from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def test_large_library_grid_is_not_rendered_twice_on_initial_load():
    source = read("static/js/main.js")
    load_library = source[source.index("async function loadLibrary()"):source.index("async function init()")]
    assert "renderGrid(videos);" not in load_library
    assert "await favoritesService.loadFavorites();" in load_library
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
