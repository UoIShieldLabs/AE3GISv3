// Drag-and-drop from the palette onto the canvas. The palette sets a JSON
// payload on the drag; the canvas reads it on drop.

export const DND_MIME = 'application/x-ae3gis-palette';

export type PaletteItem =
  | { kind: 'site' }
  | { kind: 'subnet' }
  | { kind: 'device'; type: string; image?: string };

export function setDragPayload(e: React.DragEvent, item: PaletteItem) {
  e.dataTransfer.setData(DND_MIME, JSON.stringify(item));
  e.dataTransfer.effectAllowed = 'copy';
}

export function readDragPayload(e: React.DragEvent): PaletteItem | null {
  const raw = e.dataTransfer.getData(DND_MIME);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PaletteItem;
  } catch {
    return null;
  }
}
