import { describe, expect, it } from 'vitest';
import { buildCatalogTree } from '../tree';
import { CATALOG } from '@/test/catalogFixture';

describe('buildCatalogTree', () => {
  it('orders categories as declared, undeclared ones last', () => {
    const tree = buildCatalogTree(CATALOG);
    expect(tree.map((c) => c.id)).toEqual(['network', 'security', 'misc']);
    expect(tree.map((c) => c.label)).toEqual(['Network', 'Security', 'Misc']);
  });

  it('lists visible variants, default first, hidden ones left out', () => {
    const fw = buildCatalogTree(CATALOG).find((c) => c.id === 'security')!.types[0];
    expect(fw.variants.map((v) => v.ref)).toEqual(['kathara/frr', 'ae3gis.local/nftables', 'ae3gis.local/iptables']);
    expect(fw.variants[0].isDefault).toBe(true);
    expect(fw.variants[1]).toMatchObject({ name: 'nftables', stability: 'experimental', built: true });
    expect(fw.variants[0].built).toBe(false);
  });

  it('a type without images offers its default', () => {
    const gizmo = buildCatalogTree(CATALOG).find((c) => c.id === 'misc')!.types[0];
    expect(gizmo.variants.map((v) => v.ref)).toEqual(['kathara/base']);
  });

  it('search matches types, and variants by name or ref', () => {
    const byType = buildCatalogTree(CATALOG, 'fire');
    expect(byType.flatMap((c) => c.types.map((t) => t.type))).toEqual(['firewall']);
    expect(byType[0].types[0].matchedVariants).toBe(false);
    expect(byType[0].types[0].variants).toHaveLength(3);

    const byVariant = buildCatalogTree(CATALOG, 'nft');
    const fw = byVariant[0].types[0];
    expect(fw.matchedVariants).toBe(true);
    expect(fw.variants.map((v) => v.name)).toEqual(['nftables']);

    expect(buildCatalogTree(CATALOG, 'secret')).toEqual([]); // hidden stays hidden
    expect(buildCatalogTree(null)).toEqual([]);
  });
});
