# Client State + Infinite Paging

Tags: `frontend`, `javascript`, `state`, `ux`

## Concept
Keep lightweight UI state in `localStorage`; render paged chunks and load more with `IntersectionObserver`.

## When to use
- Large card grids
- No framework frontend

## When NOT to use
- Server-side pagination/search is mandatory
- Very complex state transitions (prefer React/Vue state tools)

## Example
```javascript
const state = { currentPage: 1, pageSize: 40 };
scrollObserver = new IntersectionObserver(() => {
  state.currentPage++;
  renderGrid(state.currentGridVideos, true);
});
```

