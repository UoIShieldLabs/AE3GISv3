import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Button } from '../Button';

describe('Button', () => {
  it('exposes its variant for themes (default secondary)', () => {
    render(<><Button>Save</Button><Button variant="primary">Deploy</Button></>);
    expect(screen.getByRole('button', { name: 'Save' })).toHaveAttribute('data-variant', 'secondary');
    expect(screen.getByRole('button', { name: 'Deploy' })).toHaveAttribute('data-variant', 'primary');
  });
});
