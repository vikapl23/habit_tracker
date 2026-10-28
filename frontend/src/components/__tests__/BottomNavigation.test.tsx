import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BottomNavigation } from '../BottomNavigation';

describe('BottomNavigation', () => {
  it('renders all navigation items including Coach', () => {
    render(
      <MemoryRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <BottomNavigation />
      </MemoryRouter>
    );

    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('Stats')).toBeInTheDocument();
    expect(screen.getByText('Coach')).toBeInTheDocument();
    expect(screen.getByText('Archive')).toBeInTheDocument();
    expect(screen.getByText('Profile')).toBeInTheDocument();

    const coachLink = screen.getByRole('link', { name: /Coach/i });
    expect(coachLink).toHaveAttribute('href', '/coach');
  });
});
