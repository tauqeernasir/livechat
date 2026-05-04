import React, { useEffect, useState } from 'react';
import { useAuth } from '../lib/auth';
import { Bot, MessageSquare, Users, BookOpen, Plug } from 'lucide-react';
import Layout from '../components/Layout';
import api from '../lib/api';

interface OverviewStats {
  total_chats: number;
  leads_captured: number;
  knowledge_docs: number;
  integrations: number;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user?.workspace_id) return;
    const fetchStats = async () => {
      try {
        const response = await api.get(`/stats/overview?workspace_id=${user.workspace_id}`);
        setStats(response.data);
      } catch (error) {
        console.error('Failed to fetch overview stats:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [user?.workspace_id]);

  return (
    <Layout>
      <header className="mb-10">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Welcome back, {user?.username}</h1>
        <p className="text-gray-500 dark:text-slate-400">Here's what's happening with your AI agents today.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <StatCard title="Total Chats" value={loading ? '—' : String(stats?.total_chats ?? 0)} icon={<MessageSquare className="w-5 h-5 text-indigo-500" />} />
        <StatCard title="Leads Captured" value={loading ? '—' : String(stats?.leads_captured ?? 0)} icon={<Users className="w-5 h-5 text-emerald-500" />} />
        <StatCard title="Knowledge Docs" value={loading ? '—' : String(stats?.knowledge_docs ?? 0)} icon={<BookOpen className="w-5 h-5 text-amber-500" />} />
        <StatCard title="Integrations" value={loading ? '—' : String(stats?.integrations ?? 0)} icon={<Plug className="w-5 h-5 text-blue-500" />} />
      </div>

      <div className="bg-white dark:bg-slate-900/50 border border-gray-200 dark:border-slate-800 rounded-3xl p-16 flex flex-col items-center text-center backdrop-blur-sm">
        <div className="w-20 h-20 bg-indigo-600/10 rounded-2xl flex items-center justify-center mb-8 ring-1 ring-indigo-500/20">
          <Bot className="w-10 h-10 text-indigo-500" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Create your first chatbot</h2>
        <p className="text-gray-500 dark:text-slate-400 max-w-sm mb-10 text-lg">
          Train a custom AI on your data and embed it on your website in minutes.
        </p>
        <button className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-10 py-4 rounded-2xl shadow-xl shadow-indigo-600/20 transition-all hover:-translate-y-0.5 active:translate-y-0">
          Build New Agent
        </button>
      </div>
    </Layout>
  );
}

function StatCard({ title, value, icon }: { title: string, value: string, icon: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-slate-900/50 border border-gray-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <p className="text-gray-500 dark:text-slate-400 text-sm font-medium">{title}</p>
      </div>
      <h3 className="text-3xl font-bold text-gray-900 dark:text-white">{value}</h3>
    </div>
  );
}
