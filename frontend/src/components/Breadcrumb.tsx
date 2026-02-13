interface BreadcrumbProps {
  items: { label: string; onClick: () => void }[];
  current: string;
}

export function Breadcrumb({ items, current }: BreadcrumbProps) {
  return (
    <div className="breadcrumb-bar">
      {items.map((item, i) => (
        <span key={i} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {i > 0 && <span className="breadcrumb-separator">/</span>}
          <button className="breadcrumb-item" onClick={item.onClick}>
            {item.label}
          </button>
        </span>
      ))}
      {items.length > 0 && <span className="breadcrumb-separator">/</span>}
      <span className="breadcrumb-item active">{current}</span>
    </div>
  );
}
