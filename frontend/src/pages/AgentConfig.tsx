import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  ShieldAlert, 
  Save, 
  RotateCcw,
  CheckCircle2,
  Info
} from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../lib/auth';
import Layout from '../components/Layout';
import Editor from '../components/Editor';

export default function AgentConfig() {
  const { user, token } = useAuth();
  const [persona, setPersona] = useState('');
  const [fallbackRule, setFallbackRule] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const fetchConfig = React.useCallback(async () => {
    if (!user?.workspace_id) return;
    try {
      const response = await api.get(`/agent-config/${user.workspace_id}`);
      setPersona(response.data.persona || '');
      setFallbackRule(response.data.fallback_rule || '');
    } catch (error) {
      console.error('Failed to fetch config:', error);
    } finally {
      setIsLoading(false);
    }
  }, [user?.workspace_id]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleSave = async () => {
    if (!user?.workspace_id) return;
    setIsSaving(true);
    try {
      await api.patch(
        `/agent-config/${user.workspace_id}`,
        { persona, fallback_rule: fallbackRule }
      );
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save config:', error);
      alert('Failed to save configuration.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Layout>
      <div className="max-w-4xl flex flex-col gap-8">
        <header className="flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Agent Training</h1>
            <p className="text-gray-500 dark:text-slate-400">Configure your AI's personality and safety boundaries.</p>
          </div>
          <div className="flex gap-3">
            <button 
              onClick={handleSave}
              disabled={isSaving || isLoading}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-gray-900 dark:text-white px-8 py-3 rounded-2xl font-bold transition-all shadow-xl shadow-indigo-600/20 disabled:opacity-50"
            >
              {isSaving ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : showSuccess ? (
                <CheckCircle2 className="w-5 h-5" />
              ) : (
                <Save className="w-5 h-5" />
              )}
              {isSaving ? 'Saving...' : showSuccess ? 'Saved!' : 'Save Changes'}
            </button>
          </div>
        </header>

        {isLoading ? (
          <div className="py-20 flex flex-col items-center justify-center text-gray-400 dark:text-slate-500">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
            <p>Loading configuration...</p>
          </div>
        ) : (
          <div className="space-y-10">
            {/* AI Persona */}
            <section className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-600/10 rounded-lg">
                  <Sparkles className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900 dark:text-white">AI Persona</h2>
                  <p className="text-sm text-gray-400 dark:text-slate-500">How should your AI behave? Define its tone, role, and style.</p>
                </div>
              </div>
              <Editor 
                value={persona} 
                onChange={setPersona} 
                placeholder="e.g. You are a helpful support agent for a SaaS company. You are professional, concise, and friendly..."
              />
              <div className="bg-white dark:bg-slate-900/50 border border-gray-200 dark:border-gray-200 dark:border-slate-800/50 rounded-xl p-4 flex gap-3">
                <Info className="w-5 h-5 text-indigo-400 shrink-0" />
                <p className="text-xs text-gray-500 dark:text-slate-400 leading-relaxed">
                  <span className="font-bold text-gray-600 dark:text-slate-300">Tip:</span> Be specific. Instead of "be nice", try "maintain a warm, professional tone and use 'we' when referring to the company."
                </p>
              </div>
            </section>

            {/* Fallback Rules */}
            <section className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-rose-600/10 rounded-lg">
                  <ShieldAlert className="w-5 h-5 text-rose-400" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900 dark:text-white">Fallback & Safety</h2>
                  <p className="text-sm text-gray-400 dark:text-slate-500">What should the AI do when it doesn't know the answer?</p>
                </div>
              </div>
              <Editor 
                value={fallbackRule} 
                onChange={setFallbackRule} 
                placeholder="e.g. If you cannot find the answer in the knowledge base, politely ask for their email to follow up later..."
              />
            </section>
          </div>
        )}
      </div>
    </Layout>
  );
}
