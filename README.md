# Hashmark Scout Card Guide

This repo renders each modular “card” inside `app/static/vue-app.js` and `app/templates/partials/vue-templates.html`. Use this guide to add a custom card or tweak how cards behave:

1. **Define metadata** – open `app/static/vue-app.js` around the `defaultCards` array (lines ~205-245). Each entry is a card object with at least:
   * `id` (unique string used when saving reorder state),
   * `type` (`player`, `radar`, `list`, `stat`, etc.),
   * `title`, optional `badge`, and data specific to `type` (see existing examples for `player` and `list`).
   Adding a new card is as simple as appending another object to `defaultCards` or calling the exported `addCard()` helper inside `setup()`.

2. **Hook into the template** – the card rendering lives in `app/templates/partials/vue-templates.html` inside the `tpl-card-grid` template. The new `type` must have a matching block (e.g., `v-if="card.type === 'leaderboard'"`). If you add a new card type, add a conditional rendering branch and the markup/partials it needs.

3. **Cards are draggable** – the grid exposes drag events from `CardGrid` (`app/static/vue-app.js` around line 107). It emits `reorder`, which `App` handles with `moveCard()` plus `localStorage` persistence (`hashmark-card-order`). No backend changes are needed; the browser remembers the order automatically.

4. **Styling helpers** – use `app/static/styles.css` to add classes such as `.player-profile` or `.card-drag-handle`. The new card’s markup can rely on existing utility classes (e.g., `.radar-card`, `.card-grid`) or introduce new ones there.

5. **Example workflow**:
   - Add the object to `defaultCards`.
   - Extend the template with a `v-if` block that consumes `card.xxx`.
   - Add any needed styles.
   - Run `python run.py` and refresh to see the new card appear at the end of the grid; drag-and-drop will persist the order.

6. **Advanced helpers** – call the `addCard(card)` helper from `setup()` if you want to create cards dynamically at runtime (e.g., from fetched data); the helper appends the card, re-renders, and persists the order as well.

Follow these steps whenever you need new dashboards or stats so each scout can tailor their board.

# How to set up the dev environment

1. **Create a virtual environment** (if you do not already have one):
   ```bash
   python -m venv .venv
   ```
2. **Activate the venv** (Windows example shown):
   ```powershell
   .venv\\Scripts\\activate
   ```
3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the Flask app**:
   ```bash
   python run.py
   ```
5. **Visit the dashboard** at `http://127.0.0.1:5000/` and interact with the Vue cards. Drag-and-drop order is stored in `localStorage`, so each browser maintains its layout automatically.
