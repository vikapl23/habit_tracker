import React from 'react';
import { NavLink } from 'react-router-dom';
import { CalendarCheck, BarChart3, Archive, User } from 'lucide-react';

export const BottomNavigation: React.FC = () => {
  const navItems = [
    {
      label: 'Today',
      path: '/',
      icon: CalendarCheck,
    },
    {
      label: 'Stats',
      path: '/stats',
      icon: BarChart3,
    },
    {
      label: 'Archive',
      path: '/archived',
      icon: Archive,
    },
    {
      label: 'Profile',
      path: '/profile',
      icon: User,
    },
  ];

  return (
    <nav
      aria-label="Bottom Navigation"
      className="fixed bottom-0 left-0 right-0 max-w-[420px] mx-auto bg-white/95 backdrop-blur-md border-t border-slate-200 z-30 h-16 pb-[env(safe-area-inset-bottom,0px)] flex items-center justify-around px-2 shadow-sm"
    >
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center flex-1 h-full py-1 text-xs font-medium transition-colors ${
                isActive
                  ? 'text-blue-600 font-bold'
                  : 'text-slate-500 hover:text-slate-800'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={`w-5 h-5 mb-1 ${isActive ? 'stroke-[2.5]' : 'stroke-2'}`} />
                <span>{item.label}</span>
              </>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
};
