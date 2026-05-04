import React from 'react';
import { useAuth } from '../lib/auth';
import { Bot } from 'lucide-react';
import Layout from '../components/Layout';

export default function Dashboard() {
  const { user } = useAuth();

  return (
    <Layout>
      <header className="mb-10">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Welcome back, {user?.username}</h1>
        <p className="text-gray-500 dark:text-slate-400">Here's what's happening with your AI agents today.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <StatCard title="Total Chats" value="1,284" change="+12%" />
        <StatCard title="Leads Captured" value="48" change="+5%" />
        <StatCard title="Response Rate" value="99.2%" change="stable" />
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

function StatCard({ title, value, change }: { title: string, value: string, change: string }) {
  return (
    <div className="bg-white dark:bg-slate-900/50 border border-gray-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
      <p className="text-gray-500 dark:text-slate-400 text-sm mb-2 font-medium">{title}</p>
      <div className="flex items-end justify-between">
        <h3 className="text-3xl font-bold text-gray-900 dark:text-white">{value}</h3>
        <span className={`text-[11px] font-bold px-2.5 py-1 rounded-lg ${change.startsWith('+') ? 'bg-emerald-500/10 text-emerald-500 dark:text-emerald-400 border border-emerald-500/10' : 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-slate-400'
          }`}>
          {change}
        </span>
      </div>
    </div>
  );
}
