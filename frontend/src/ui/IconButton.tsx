import { Button, type ButtonProps } from './Button';
import { Tooltip } from './Tooltip';

export interface IconButtonProps extends Omit<ButtonProps, 'size'> {
  /** Accessible name; also shown as the tooltip unless `tooltip` is given. */
  label: string;
  tooltip?: React.ReactNode | false;
  shortcut?: string;
  size?: 'icon' | 'icon-sm' | 'icon-xs';
  side?: 'top' | 'right' | 'bottom' | 'left';
}

export function IconButton({ label, tooltip, shortcut, size = 'icon', variant = 'ghost', side, ...props }: IconButtonProps) {
  const button = <Button aria-label={label} size={size} variant={variant} {...props} />;
  if (tooltip === false) return button;
  return (
    <Tooltip content={tooltip ?? label} shortcut={shortcut} side={side}>
      {button}
    </Tooltip>
  );
}
