// Category → type → variant tree built from the catalog. The one grouping used
// by the palette, the type picker and the add menus, so they always agree on
// order and on what is hidden.
import { categoryLabel, type Catalog, type NodeTypeSpec, type Stability } from './catalog';

export interface CatalogVariant {
  ref: string;
  name: string;
  description: string;
  stability: Stability;
  /** Built by AE3GIS from a Dockerfile (vs pulled from a registry). */
  built: boolean;
  isDefault: boolean;
}

export interface CatalogTypeNode {
  type: string;
  spec: NodeTypeSpec;
  name: string;
  /** Visible variants (hidden images left out), default first. */
  variants: CatalogVariant[];
  /** The search matched variants rather than the type itself; show them. */
  matchedVariants: boolean;
}

export interface CatalogCategoryNode {
  id: string;
  label: string;
  types: CatalogTypeNode[];
}

function variantsOf(catalog: Catalog, spec: NodeTypeSpec): CatalogVariant[] {
  const refs = spec.images?.length ? spec.images : [spec.defaultImage];
  const out: CatalogVariant[] = [];
  for (const ref of refs) {
    const img = catalog.images?.[ref];
    const stability = img?.stability ?? 'stable';
    if (stability === 'hidden' && ref !== spec.defaultImage) continue;
    out.push({
      ref,
      name: img?.displayName ?? ref,
      description: img?.description ?? '',
      stability,
      built: img?.source?.kind === 'build',
      isDefault: ref === spec.defaultImage,
    });
  }
  // Default first, the rest in catalog order.
  return out.sort((a, b) => Number(b.isDefault) - Number(a.isDefault));
}

const has = (hay: (string | undefined | null)[], q: string) => hay.some((h) => h?.toLowerCase().includes(q));

/** Build the tree, optionally filtered by a search query (type or variant names). */
export function buildCatalogTree(catalog: Catalog | null, query = ''): CatalogCategoryNode[] {
  if (!catalog) return [];
  const q = query.trim().toLowerCase();
  const byCategory = new Map<string, CatalogTypeNode[]>();

  for (const [type, spec] of Object.entries(catalog.types)) {
    let variants = variantsOf(catalog, spec);
    const name = spec.displayName || type;
    let matchedVariants = false;
    if (q) {
      const typeHit = has([name, type, spec.label, spec.description, spec.category, categoryLabel(spec.category, catalog)], q);
      if (!typeHit) {
        variants = variants.filter((v) => has([v.name, v.ref, v.description], q));
        if (!variants.length) continue;
        matchedVariants = true;
      }
    }
    const list = byCategory.get(spec.category) ?? [];
    list.push({ type, spec, name, variants, matchedVariants });
    byCategory.set(spec.category, list);
  }

  const declared = (catalog.categories ?? []).map((c) => c.id);
  const order = [...declared, ...[...byCategory.keys()].filter((id) => !declared.includes(id))];
  return order
    .filter((id) => byCategory.has(id))
    .map((id) => ({ id, label: categoryLabel(id, catalog), types: byCategory.get(id)! }));
}
