import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bot, Shield, Zap, LayoutDashboard, Settings, User, LogOut, Sun, Moon } from 'lucide-react';
import api from './lib/api';

function App() {
  const [isDarkMode, setIsDarkMode] = useState(true);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  // Check backend health
  const { data: health, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await api.get('/health');
      return response.data;
    },
    retry: 1,
  });

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-300">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 p-6 flex flex-col gap-8">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600 rounded-lg">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">Antigravity</h1>
        </div>

        <nav className="flex flex-col gap-2 flex-grow">
          <NavItem icon={<LayoutDashboard size={20} />} label="Dashboard" active />
          <NavItem icon={<Bot size={20} />} label="My Agents" />
          <NavItem icon={<Shield size={20} />} label="Security" />
          <NavItem icon={<Settings size={20} />} label="Settings" />
        </nav>

        <div className="flex flex-col gap-4">
          <button 
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="flex items-center gap-3 px-4 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors w-full text-left"
          >
            {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            <span>{isDarkMode ? 'Light Mode' : 'Dark Mode'}</span>
          </button>
          
          <div className="border-t border-slate-200 dark:border-slate-800 pt-4">
            <div className="flex items-center gap-3 px-4 py-2">
              <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center">
                <User size={16} className="text-indigo-600 dark:text-indigo-400" />
              </div>
              <div className="flex flex-col overflow-hidden">
                <span className="text-sm font-medium truncate">User Account</span>
                <span className="text-xs text-slate-500 truncate">user@example.com</span>
              </div>
              <LogOut size={16} className="ml-auto text-slate-400 cursor-pointer hover:text-red-500" />
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-10">
        <header className="flex justify-between items-center mb-10">
          <div>
            <h2 className="text-3xl font-bold mb-2">Welcome Back!</h2>
            <p className="text-slate-500 dark:text-slate-400">Monitor and manage your AI agents in real-time.</p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className={`px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2 ${
              isLoading ? 'bg-slate-100 text-slate-500' : 
              health ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 
              'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                isLoading ? 'bg-slate-400' : 
                health ? 'bg-emerald-500' : 
                'bg-red-500'
              } animate-pulse`} />
              {isLoading ? 'Checking system...' : health ? 'System Online' : 'System Offline'}
            </div>
            <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg font-medium transition-colors shadow-lg shadow-indigo-500/20 flex items-center gap-2">
              <Zap size={18} />
              New Agent
            </button>
          </div>
        </header>

        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <StatCard title="Active Agents" value="12" delta="+3 this week" />
          <StatCard title="Total Requests" value="45.2k" delta="+12% from yesterday" />
          <StatCard title="Avg Response Time" value="450ms" delta="-50ms improvement" />
        </section>

        <div className="mt-12 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-8 shadow-sm">
          <h3 className="text-xl font-bold mb-6">Recent Activity</h3>
          <div className="space-y-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-4 p-4 rounded-xl border border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                <div className="p-3 bg-indigo-50 dark:bg-indigo-900/50 rounded-full">
                  <Bot size={24} className="text-indigo-600 dark:text-indigo-400" />
                </div>
                <div className="flex-grow">
                  <h4 className="font-semibold text-slate-900 dark:text-slate-100">Customer Support Bot #{i}</h4>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Successfully resolved a ticket in 4 minutes</p>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-400">2 hours ago</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

function NavItem({ icon, label, active = false }: { icon: React.ReactNode, label: string, active?: boolean }) {
  return (
    <a href="#" className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all duration-200 ${
      active 
        ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 font-semibold shadow-sm' 
        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100'
    }`}>
      {icon}
      <span>{label}</span>
    </a>
  );
}

function StatCard({ title, value, delta }: { title: string, value: string, delta: string }) {
  return (
    <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
      <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">{title}</h4>
      <div className="text-3xl font-bold mb-2">{value}</div>
      <p className="text-xs font-medium text-emerald-500">{delta}</p>
    </div>
  );
}

export default App;
