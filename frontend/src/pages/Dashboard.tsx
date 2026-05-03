import React from 'react';
import { useAuth } from '../lib/auth';
import { Bot, LogOut, LayoutDashboard, Settings, MessageSquare, Users } from 'lucide-react';

export default function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-950 flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900/50 p-6 flex flex-col">
        <div className="flex items-center gap-3 mb-12">
          <Bot className="w-8 h-8 text-indigo-500" />
          <span className="text-xl font-bold text-white tracking-tight">Lagent AI</span>
        </div>

        <nav className="flex-grow space-y-2">
          <NavItem icon={<LayoutDashboard className="w-5 h-5" />} label="Overview" active />
          <NavItem icon={<MessageSquare className="w-5 h-5" />} label="Chatbots" />
          <NavItem icon={<Users className="w-5 h-5" />} label="Leads" />
          <NavItem icon={<Settings className="w-5 h-5" />} label="Settings" />
        </nav>

        <div className="pt-6 border-t border-slate-800">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold">
              {user?.username?.charAt(0) || 'U'}
            </div>
            <div className="flex-grow min-w-0">
              <p className="text-sm font-semibold text-white truncate">{user?.username}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors text-sm font-medium"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-grow p-12">
        <header className="mb-12">
          <h1 className="text-3xl font-bold text-white mb-2">Welcome back, {user?.username}</h1>
          <p className="text-slate-400">Here's what's happening with your AI agents today.</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <StatCard title="Total Chats" value="1,284" change="+12%" />
          <StatCard title="Leads Captured" value="48" change="+5%" />
          <StatCard title="Response Rate" value="99.2%" change="stable" />
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 flex flex-col items-center text-center">
          <div className="w-16 h-16 bg-indigo-600/10 rounded-full flex items-center justify-center mb-6">
            <Bot className="w-8 h-8 text-indigo-500" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Create your first chatbot</h2>
          <p className="text-slate-400 max-w-sm mb-8">
            Train a custom AI on your data and embed it on your website in minutes.
          </p>
          <button className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-8 py-3 rounded-xl shadow-lg shadow-indigo-600/20 transition-all">
            Build New Agent
          </button>
        </div>
      </main>
    </div>
  );
}

function NavItem({ icon, label, active = false }: { icon: React.ReactNode, label: string, active?: boolean }) {
  return (
    <a href="#" className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${active ? 'bg-indigo-600/10 text-indigo-400 font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
      }`}>
      {icon}
      <span>{label}</span>
    </a>
  );
}

function StatCard({ title, value, change }: { title: string, value: string, change: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
      <p className="text-slate-400 text-sm mb-2">{title}</p>
      <div className="flex items-end justify-between">
        <h3 className="text-2xl font-bold text-white">{value}</h3>
        <span className={`text-xs font-semibold px-2 py-1 rounded-lg ${change.startsWith('+') ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-800 text-slate-400'
          }`}>
          {change}
        </span>
      </div>
    </div>
  );
}
