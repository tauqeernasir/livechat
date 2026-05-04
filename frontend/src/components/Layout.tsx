import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { useTheme } from '../lib/theme';
import {
  Bot,
  LogOut,
  LayoutDashboard,
  Settings,
  MessageSquare,
  Users,
  Sun,
  Moon,
  Database,
  ChevronRight,
  ChevronUp,
  Terminal,
  Plug,
  Globe
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  fullWidth?: boolean;
}

export default function Layout({ children, fullWidth = false }: LayoutProps) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [userMenuOpen]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 flex text-gray-700 dark:text-slate-200">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 flex flex-col fixed h-full">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-10">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-600/20">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900 dark:text-white tracking-tight">Lagent</span>
          </div>

          <nav className="space-y-1.5">
            <SidebarLink
              to="/dashboard"
              icon={<LayoutDashboard className="w-5 h-5" />}
              label="Overview"
            />
            <SidebarLink
              to="/chatbot"
              icon={<MessageSquare className="w-5 h-5" />}
              label="Agents"
            />
            <SidebarLink
              to="/knowledge"
              icon={<Database className="w-5 h-5" />}
              label="Knowledge Base"
            />
            <SidebarLink
              to="/leads"
              icon={<Users className="w-5 h-5" />}
              label="Leads"
            />
          </nav>

          <div className="mt-10 mb-2 px-4">
            <span className="text-[10px] font-bold text-gray-400 dark:text-slate-500 uppercase tracking-widest">Settings</span>
          </div>

          <nav className="space-y-1.5">
            <SidebarLink
              to="/settings/agent"
              icon={<Settings className="w-5 h-5" />}
              label="Agent Training"
            />
            <SidebarLink
              to="/settings/integrations"
              icon={<Plug className="w-5 h-5" />}
              label="Integrations"
            />
            <SidebarLink
              to="/settings/widget"
              icon={<Globe className="w-5 h-5" />}
              label="Chat Widget"
            />
            <SidebarLink
              to="/playground"
              icon={<Terminal className="w-5 h-5" />}
              label="Playground"
            />
          </nav>
        </div>

        <div className="mt-auto p-6 border-t border-gray-200 dark:border-slate-800/50 relative">
          <div className="flex items-center gap-3 px-2">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow-md shrink-0">
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-grow min-w-0">
              <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{user?.username}</p>
              <p className="text-[11px] text-gray-400 dark:text-slate-500 truncate">{user?.email}</p>
            </div>
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="p-1 text-gray-400 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors shrink-0"
            >
              <ChevronUp className={`w-4 h-4 transition-transform ${userMenuOpen ? '' : 'rotate-180'}`} />
            </button>
          </div>

          {userMenuOpen && (
            <div
              ref={userMenuRef}
              className="absolute bottom-full left-6 right-6 mb-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl shadow-xl py-1 z-50"
            >
              <button
                onClick={() => { toggleTheme(); }}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-700/50 transition-all text-sm font-medium"
              >
                {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
              </button>
              <div className="border-t border-gray-200 dark:border-slate-700 my-1" />
              <button
                onClick={() => { setUserMenuOpen(false); handleLogout(); }}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-gray-500 dark:text-slate-400 hover:text-rose-500 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-400/10 transition-all text-sm font-medium group"
              >
                <LogOut className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-grow ml-64 min-h-screen">
        <div className={fullWidth ? 'h-screen' : 'max-w-7xl mx-auto px-8 py-10'}>
          {children}
        </div>
      </main>
    </div>
  );
}

function SidebarLink({ to, icon, label }: { to: string, icon: React.ReactNode, label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `
        flex items-center justify-between px-4 py-2.5 rounded-xl transition-all group
        ${isActive
          ? 'bg-indigo-600/10 text-indigo-600 dark:text-indigo-400 font-semibold border border-indigo-600/10'
          : 'text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-800/50'
        }
      `}
    >
      <div className="flex items-center gap-3">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all text-gray-300 dark:text-slate-600" />
    </NavLink>
  );
}
