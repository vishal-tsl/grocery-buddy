# SIGE — Refined MVP Architecture & Gap-Fill Plan

**Spatial Intelligence Grid Engine** — React + Konva (frontend), FastAPI (backend).  
This document refines the system for a **production-ready MVP**: frontend-first compute, derived grid, undo/redo, circulation without mandatory doors, and persistence without full grid JSON.

---

## 1. Refined architecture

### Principles

| Layer | Responsibility |
|--------|------------------|
| **Frontend** | Authoritative for: layout editing, grid derivation, metrics (incremental), BFS/circulation, collision, snap math, undo/redo, Konva rendering. |
| **Backend** | Persistence (versioned documents), auth, optional **heavy** jobs later (batch layout scoring, export PDF at scale). **No grid recomputation on server for MVP.** |

### What runs where

**Frontend (always)**

- Parse/load **saved document** → `GeometryState` + `FurnitureState` + `ProjectConfig`.
- Compute **DerivedGrid** from geometry + config (cell size, bounds, walls/obstacles).
- Furniture placement: logical footprint → cell occupancy; visual transform for Konva.
- **Circulation graph**: adjacency from walkable cells; BFS / multi-source / largest-component fallback.
- **Metrics**: recompute deltas from dirty regions (see §6, §9).
- **History**: action log → patch previous `GeometryState` / `FurnitureState`.

**Backend (MVP)**

- `POST/GET /projects/:id` — JSON body = **persisted model only** (§7).
- Optional: `POST /projects/:id/export` — stub for future PDF/render queue.
- No per-frame or per-drag API calls.

### Derived Grid Model (computed, not stored)

- **Logical grid**: `widthCells × heightCells` of typed cells (`void`, `wall`, `door`, `furniture`, `walkable`, `outside`).
- **Source of truth**: polygon room outline(s), wall segments, door segments, furniture AABBs (rotated → grid cells).
- **DerivedGrid** is a pure function:  
  `(geometry, furniture[], config) => { cells: TypedArray | sparse map, index: GridIndex, version }`  
  Bump `version` on any change that affects topology or occupancy; consumers subscribe to `version`.

---

## 2. State management (Zustand) — critical

### Store slices (single store, optional `zustand/middleware` combine)

```ts
// --- Persisted / user-editable ---
type GeometryState = {
  rooms: RoomPolygon[];       // closed polys in world units (mm or px)
  walls: WallSegment[];
  doors: DoorSegment[];       // optional; may be empty
  worldBounds: { minX, minY, maxX, maxY };
};

type FurniturePiece = {
  id: string;
  typeId: string;
  x: number; y: number;      // world anchor (e.g. center or corner — pick one convention)
  rotationDeg: number;      // 0,90,180,270 for MVP
  footprintW: number;       // world units along local X before rotation
  footprintH: number;
  meta?: Record<string, unknown>;
};

type FurnitureState = {
  items: Map<string, FurniturePiece>; // or Record — Map avoids key churn in hot paths
};

type ProjectConfig = {
  cellSizeWorld: number;     // e.g. 100mm → one cell
  gridOrigin: { x: number; y: number };
  showVisualGrid: boolean;
};

// --- Derived (never persisted, never in history patches directly) ---
type DerivedGrid = {
  version: number;
  cols: number;
  rows: number;
  // Uint8 enum per cell OR sparse: only non-walkable + boundaries
  cellKind: Uint8Array;      // 0=walkable, 1=wall, 2=furniture, 3=door, 4=outside
  furnitureCellMask: Uint32Array | null; // optional: furniture id per cell (0 = none)
};

// --- History ---
type HistoryEntry = {
  id: string;
  timestamp: number;
  patch: Partial<{ geometry: GeometryState; furniture: FurnitureState }>; // inverse patch for undo
  forwardPatch: Partial<{ geometry: GeometryState; furniture: FurnitureState }>;
  label: string;
};

type HistoryState = {
  past: HistoryEntry[];
  future: HistoryEntry[];
  maxEntries: number;        // e.g. 100
};
```

### Root store shape

```ts
type SigeStore = {
  geometry: GeometryState;
  furniture: FurnitureState;
  config: ProjectConfig;
  derived: DerivedGrid | null;
  derivedError: string | null;
  history: HistoryState;

  // actions (examples)
  applyGeometry: (updater: (g: GeometryState) => GeometryState) => void;
  applyFurniture: (updater: (f: FurnitureState) => FurnitureState) => void;
  setConfig: (partial: Partial<ProjectConfig>) => void;
  recomputeDerived: () => void;
  undo: () => void;
  redo: () => void;
  commitHistory: (label: string, forward: Patch, inverse: Patch) => void;
};
```

### Update flow

1. User action → `commitHistory` receives **forward** and **inverse** patches (minimal JSON patches or immer patches on `geometry` + `furniture` only).
2. Apply forward patch → `geometry` / `furniture` update.
3. Mark **dirty rect** in world space (expanded by cell size).
4. `recomputeDerived()`:
   - If dirty rect covers &lt; ~30% of grid → **partial** recompute (§3).
   - Else full rasterize polys + furniture into `cellKind`.
5. Subscribers (metrics, circulation) read `derived.version`; recompute only if version changed.

### Efficient derived recompute

- **Full recompute**: O(cols × rows) fill + poly raster (even-odd or scanline).
- **Partial**: clear dirty AABB expanded to cell bounds; re-raster only walls/doors/furniture intersecting AABB; copy untouched regions from previous buffer **if** topology unchanged (same cols/rows). If `cellSize` or `worldBounds` change → full recompute.
- Use **requestAnimationFrame** coalescing: multiple edits in one frame → one recompute.

---

## 3. Grid engine refactor

### Logical vs visual

| Concept | Purpose |
|---------|---------|
| **Logical grid** | `cellKind`, adjacency, BFS, metrics, collision. Integer indices only. |
| **Visual grid** | Konva `Layer`: lines, room fill, optional dots; **snapped** to `cellSizeWorld`; may show sub-pixel strokes; **does not** drive logic. |

### Indexing (avoid string keys)

- **Cell id**: `cellId = row * cols + col` (number).
- **2D access**: `idx = r * cols + c`; bounds check `0 <= idx < cols*rows`.
- **Neighbor iteration**: 4-connectivity: `idx ± 1`, `idx ± cols` with edge checks.
- **Spatial hash (optional)**: `Map<number, Set<FurnitureId>>` for “which furniture touches cell id” — keyed by number.

### Memory (5000+ cells)

- 100×50 = 5,000 cells → `Uint8Array` 5 KB + masks negligible.
- 200×200 = 40,000 → still fine. Cap **cols × rows** in config (e.g. max 250_000) for safety.
- **Sparse** alternative: only store non-walkable cells in `Map<cellId, kind>` if &gt;80% walkable **and** profiling shows win — MVP default: dense `Uint8Array` simpler.

### Partial recomputation

- Maintain `lastDerived: DerivedGrid` + `dirtyWorldRect`.
- Convert rect to `[c0,r0,c1,r1]` inclusive cell range.
- For each furniture/wall intersecting rect, repaint those cells.
- **Furniture move**: old footprint cells cleared to walkable/wall (from base layer cache) — keep a **static base mask** (room+walls without furniture) updated only when geometry changes, then XOR furniture on top.

---

## 4. Furniture system — snap vs “free”

### Internal rule

- **All logic uses grid cells.** Footprint → rotated OBB → **voxelize** to set of `cellId`s.
- **Single source of truth**: furniture anchor in world units, but **valid positions** are those where voxelized cells ⊆ walkable ∧ no collision.

### UI illusion of free placement

- While dragging: Konva follows pointer (sub-cell smooth motion).
- On **pointerup**: snap anchor to nearest **legal** cell-aligned position:
  - `snapX = round((x - origin.x) / cellSize) * cellSize + origin.x` (then collision resolve: small spiral search in cell units if overlap).
- Optional **hold Alt** for true free **display** only — still commit to nearest legal grid on release (MVP: always snap on commit to avoid inconsistent saves).

### Rotation

- MVP: **90° steps** only → footprint cells computed by rotating width/height and taking axis-aligned bounding box in grid space, or exact rect rotation + cell intersection tests.
- Store `rotationDeg`; `getOccupiedCells(piece, config) => cellId[]`.

### Bounding box → grid

1. Transform 4 corners by rotation around anchor.
2. Axis-aligned bbox in world space → convert min/max to cell range.
3. For each cell in range, test center or polygon intersection with rotated rect; mark occupied.

---

## 5. Circulation & dead space (BFS fixed)

### Problems addressed

- No door → still find reachable “living” area.
- Multiple doors → multi-source BFS.
- Fallback → largest open walkable component as implicit entry.

### Algorithm

1. Build **walkable mask**: `cellKind === walkable` (and optionally “room interior” from polygon test).
2. **Seed set** `S`:
   - All cells tagged `door` adjacent to walkable **outside** or **entry zone** (if defined).
   - If `S` empty: compute connected components on walkable cells (4-neighbor). Take component with **maximum area**. Pick arbitrary cell in that component (e.g. top-left) as **virtual entry**; `S = { that cell }`.
   - If multiple doors: `S = all door-adjacent walkable cells`.
3. **Multi-source BFS** from `S` on walkable graph.
4. **Reachable** = visited; **dead** = walkable ∧ ¬visited.
5. **Distance field** optional: BFS level = steps from nearest seed (for heatmap metrics).

### Edge cases

- **Disconnected rooms** (no door): each room’s largest component gets its own virtual entry if you want per-room metrics; or mark unreachable inner rooms as dead.
- **Furniture blocking all paths**: BFS from seeds may leave regions dead — intended.
- **Geometry change**: invalidate BFS cache when `derived.version` changes.

---

## 6. Metrics engine

### Global metrics

| Metric | Formula / rule |
|--------|----------------|
| **Total walkable cells** | `count(cellKind === walkable)` |
| **Reachable ratio** | `reachableWalkable / totalWalkable` |
| **Dead space ratio** | `deadWalkable / totalWalkable` |
| **Furniture coverage** | `occupiedByFurniture / totalInterior` |
| **Mean distance to entry** | average BFS depth over reachable cells (normalize by `sqrt(area)` for comparability) |

### Room-level metrics

- **Room definition**: each closed polygon in `GeometryState.rooms` with `roomId`.
- For each room polygon, raster **room mask**; intersect with walkable/reachable.
- **Per room**:  
  - `area_cells`, `reachable_cells`, `dead_cells`, `furniture_cells`  
  - `circulation_score = reachable_cells / max(1, area_cells - furniture_cells)`

### Normalization

- Store **raw cell counts** + **percentages** (0–1) for UI.
- Compare across projects: normalize by `sqrt(interior_cells)` or fixed reference area (e.g. 100 m² equivalent).

### Recompute strategy

- On `derived.version` change: if only furniture moved inside one room, recompute **that room’s** bbox + global reachable mask diff (incremental BFS from changed cells — advanced); **MVP**: re-run full BFS (O(N) acceptable for N ≤ 250k with TypedArray queue).

---

## 7. Persistence strategy

### Stored document (no full grid JSON)

```json
{
  "version": 1,
  "config": { "cellSizeWorld": 100, "gridOrigin": { "x": 0, "y": 0 }, "showVisualGrid": true },
  "geometry": { "rooms": [], "walls": [], "doors": [], "worldBounds": {} },
  "furniture": { "items": { "uuid-1": { "id", "typeId", "x", "y", "rotationDeg", "footprintW", "footprintH" } } },
  "meta": { "name": "", "updatedAt": "" }
}
```

### Load path

1. `GET` document → hydrate Zustand.
2. `recomputeDerived()` once (or debounced).
3. Run BFS + metrics.

### Performance

- Payload size O(furniture + vertices) — small.
- Cold load: one full raster + BFS — acceptable for MVP.

---

## 8. Undo / redo

- **Action-based**: each user-visible operation pushes `{ label, forwardPatch, inversePatch }` onto `past`; clear `future` on new action.
- **Patches** only on `geometry` and `furniture` — never on `derived`.
- **Coalescing**: drag single furniture → one history entry on pointerup (not per frame).
- **Memory cap**: `maxEntries` + drop oldest; patches should be **minimal** (e.g. `{ furniture: { items: { id: prevPiece } } }`).
- **Zustand**: `temporal` middleware optional; manual stack is fine for MVP.

---

## 9. Performance strategy

| Target | Approach |
|--------|----------|
| **Max grid** | e.g. 500×500 cells soft cap; warn in UI above 250k cells. |
| **Memoization** | `useMemo(() => computeMetrics(derived), [derived.version])`; Konva `Layer` listening off where static. |
| **Selective recompute** | Dirty rect partial raster (§3); full BFS only when topology changes. |
| **Rendering** | Konva: separate layers (static room, grid lines, furniture, UI); **clip** to viewport; consider `react-konva` `Group` caching for static geometry. |
| **Virtualization** | For **list** UIs only; Konva uses viewport culling manually — don’t draw cells as 40k `Rect`s; draw **chunk textures** or single image for base grid. |

---

## 10. Future AI hooks (placeholders only)

| Hook | Contract (future) |
|------|-------------------|
| **Layout optimization** | `suggestLayout(geometry, furniture[], constraints) => FurniturePiece[]` — pure function; callable Web Worker or backend job. |
| **Furniture suggestions** | `rankFurniture(roomType, metrics) => CatalogItem[]` |
| **Constraint validation** | `validate(state) => { ok: boolean, issues: Issue[] }` — plug rules engine before commit |

Expose stable TypeScript interfaces in `sige/ai/contracts.ts`; no implementation in MVP.

---

## MVP checklist (implementation order)

1. Persisted model + load/save + full `recomputeDerived`.
2. Dense grid + indexing + furniture voxelization + snap-on-commit.
3. BFS with multi-source + largest-component fallback.
4. Metrics global + per-room.
5. History stack + undo/redo.
6. Partial recompute + perf pass.
7. AI contract stubs.

---

## Constraints honored

- Backend stays thin (persistence + future heavy jobs).
- No microservices.
- No assumption of perfect floor-plan CV — geometry is user/authored or imported as polys.
- Usability over mm-precision: grid snap and clear dead-space visualization first.

---

*Document version: 1.0 — gap-fill aligned with original SIGE refinement prompt.*
