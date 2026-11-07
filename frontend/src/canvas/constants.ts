// Geometry shared by the projection, layout engine, and node components.
// Sizes are the rendered box sizes of each node kind (keep in sync with the
// node components' fixed widths/heights).

export const NODE_SIZE = {
  site: { width: 184, height: 92 },
  subnet: { width: 208, height: 84 },
  device: { width: 188, height: 60 },
} as const;

export type NodeKind = keyof typeof NODE_SIZE;

/** Snap grid in canvas units. */
export const GRID = 16;

/** Padding inside an expanded (group) node around its children. */
export const GROUP_PADDING = 24;
/** Header height of an expanded (group) node. */
export const GROUP_HEADER = 36;
/** Groups never get narrower than this so the header stays readable. */
export const MIN_GROUP_WIDTH = 300;

/** Spacing used when auto-placing a new node next to existing ones. */
export const PLACEMENT_GAP = 32;

/** Gaps between nodes in a row and between rows, per scope level, for the
 *  layered layouts (Tree, Purdue). */
export const LAYOUT_SPACING = {
  subnet: { nodeSpacing: 40, rankSpacing: 72 },
  site: { nodeSpacing: 72, rankSpacing: 110 },
  root: { nodeSpacing: 96, rankSpacing: 140 },
} as const;
