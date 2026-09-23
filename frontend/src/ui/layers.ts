// One z-index scale for portalled layers.
//
// Everything below portals to <body>, so paint order is decided by z-index
// alone, not by where it sits in the React tree. The rule that matters: a
// layer that can open from *inside* a dialog or sheet (a menu, a popover, a
// combobox list, a tooltip) must sit above it, or it renders behind the modal
// and cannot be clicked.
export const LAYER = {
  /** Dialog / sheet backdrop. */
  overlay: 'z-[80]',
  /** Dialog / sheet content. */
  modal: 'z-[81]',
  /** Command palette (over modals). */
  palette: 'z-[86]',
  /** Menus, popovers, selects — openable from inside a modal. */
  floating: 'z-[90]',
  /** Tooltips sit above everything, including menu items. */
  tooltip: 'z-[95]',
} as const;
