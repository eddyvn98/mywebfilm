---
name: js
description: "Skill for the Js area of CinemaProject. 104 symbols across 19 files."
---

# Js

104 symbols | 19 files | Cohesion: 83%

## When to Use

- Working with code in `static/`
- Understanding how play, openVideoModal, playNext work
- Modifying js-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `static/js/player.js` | openVideoModal, injectPlaylistUI, updatePlaylistActiveItem, updateShuffleBtn, loadVideoSource (+10) |
| `static/js/api.js` | getStreamUrl, deleteFile, apiRename, apiMkdir, apiMove (+8) |
| `static/js/selection_service.js` | bulkDelete, toggleManageMode, cancelSelection, bulkMove, handleMouseEnter (+4) |
| `static/js/filter_service.js` | applyFilters, renderDynamicCategories, filterByFavorites, filterByHistory, closeDropdowns (+4) |
| `static/js/mgmt_ui_service.js` | openAiLab, renderMgmtSidebars, toggleGenreTag, renderActorQuickSelect, toggleActorTag (+4) |
| `static/js/render_service.js` | formatDuration, renderGrid, renderTimeline, setupInfiniteScroll, renderFolders (+1) |
| `static/js/clauwbot.js` | constructor, init, toggle, addMessage, showThinking (+1) |
| `static/js/manage_service.js` | closeRenameModal, confirmRename, deleteItem, filterByFolder, finalizeMetadata |
| `static/js/queue_service.js` | processHighlight, processConvert, startQueuePolling, updateQueueUI, clearCompletedQueue |
| `static/js/discovery_service.js` | closeDiscovery, openDiscovery, renderDiscoveryContent, renderSection, toggleDiscoverySection |

## Entry Points

Start here when exploring this area:

- **`play`** (Function) — `routes/api_video.py:59`
- **`openVideoModal`** (Function) — `static/js/player.js:10`
- **`playNext`** (Function) — `static/js/player.js:373`
- **`playPrev`** (Function) — `static/js/player.js:401`
- **`openImageModal`** (Function) — `static/js/player.js:445`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `play` | Function | `routes/api_video.py` | 59 |
| `openVideoModal` | Function | `static/js/player.js` | 10 |
| `playNext` | Function | `static/js/player.js` | 373 |
| `playPrev` | Function | `static/js/player.js` | 401 |
| `openImageModal` | Function | `static/js/player.js` | 445 |
| `endAction` | Function | `static/js/gestures.js` | 67 |
| `getStreamUrl` | Function | `static/js/api.js` | 19 |
| `saveState` | Function | `static/js/state.js` | 46 |
| `bulkDelete` | Function | `static/js/selection_service.js` | 104 |
| `closeRenameModal` | Function | `static/js/manage_service.js` | 20 |
| `confirmRename` | Function | `static/js/manage_service.js` | 22 |
| `deleteItem` | Function | `static/js/manage_service.js` | 52 |
| `applyFilters` | Function | `static/js/filter_service.js` | 9 |
| `renderDynamicCategories` | Function | `static/js/filter_service.js` | 77 |
| `filterByFavorites` | Function | `static/js/filter_service.js` | 186 |
| `filterByHistory` | Function | `static/js/filter_service.js` | 196 |
| `deleteFile` | Function | `static/js/api.js` | 55 |
| `apiRename` | Function | `static/js/api.js` | 71 |
| `toggleManageMode` | Function | `static/js/selection_service.js` | 7 |
| `cancelSelection` | Function | `static/js/selection_service.js` | 98 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `ProcessHighlight → GetPreviewUrl` | cross_community | 6 |
| `ProcessHighlight → GetThumbnailUrl` | cross_community | 6 |
| `ProcessHighlight → FormatDuration` | cross_community | 6 |
| `ProcessHighlight → IsFavorite` | cross_community | 6 |
| `ProcessConvert → GetPreviewUrl` | cross_community | 6 |
| `ProcessConvert → GetThumbnailUrl` | cross_community | 6 |
| `ProcessConvert → FormatDuration` | cross_community | 6 |
| `ProcessConvert → IsFavorite` | cross_community | 6 |
| `ProcessHighlight → GetHistoryPaths` | cross_community | 5 |
| `ProcessHighlight → SaveState` | cross_community | 5 |

## How to Explore

1. `gitnexus_context({name: "play"})` — see callers and callees
2. `gitnexus_query({query: "js"})` — find related execution flows
3. Read key files listed above for implementation details
