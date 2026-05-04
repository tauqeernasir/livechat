import React, { useState, useEffect, useRef } from 'react';
import {
  Plus,
  FileText,
  Upload,
  Clock,
  CheckCircle2,
  AlertCircle,
  Search,
  MoreVertical,
  Trash2,
  ExternalLink,
  FileCode,
  Type,
  Database,
  Save
} from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../lib/auth';
import Layout from '../components/Layout';
import Editor from '../components/Editor';

interface KnowledgeSource {
  id: number;
  name: string;
  source_type: 'file' | 'manual';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  error_message?: string;
}

export default function KnowledgeBase() {
  const { user, token } = useAuth();
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [manualName, setManualName] = useState('');
  const [manualContent, setManualContent] = useState('');
  const [isSavingManual, setIsSavingManual] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchSources = React.useCallback(async () => {
    if (!user?.workspace_id) return;
    try {
      const response = await api.get(`/knowledge/sources/${user.workspace_id}`);
      if (Array.isArray(response.data)) {
        setSources(response.data);
      } else {
        console.error('Invalid response format for sources:', response.data);
        setSources([]);
      }
    } catch (error) {
      console.error('Failed to fetch sources:', error);
      setSources([]);
    } finally {
      setIsLoading(false);
    }
  }, [user?.workspace_id]);

  // Use a ref to always have the latest sources in the interval without re-running the effect
  const sourcesRef = useRef(sources);
  useEffect(() => {
    sourcesRef.current = sources;
  }, [sources]);

  useEffect(() => {
    if (!user?.workspace_id) return;

    // Initial fetch
    fetchSources();

    // Setup polling interval that stays stable
    const pollInterval = setInterval(() => {
      const hasActiveJobs = sourcesRef.current.some(
        s => s.status === 'pending' || s.status === 'processing'
      );
      if (hasActiveJobs) {
        fetchSources();
      }
    }, 5000);

    return () => clearInterval(pollInterval);
  }, [user?.workspace_id, fetchSources]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !user?.workspace_id) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post(
        `/knowledge/upload?workspace_id=${user.workspace_id}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      fetchSources();
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Failed to upload file. Please try again.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleSaveManual = async () => {
    if (!manualName || !manualContent || !user?.workspace_id) return;
    setIsSavingManual(true);
    try {
      await api.post(
        `/knowledge/manual?workspace_id=${user.workspace_id}`,
        { name: manualName, content: manualContent }
      );
      setIsManualModalOpen(false);
      setManualName('');
      setManualContent('');
      fetchSources();
    } catch (error) {
      console.error('Failed to save manual knowledge:', error);
      alert('Failed to save. Please try again.');
    } finally {
      setIsSavingManual(false);
    }
  };

  const filteredSources = sources.filter(source =>
    source.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Layout>
      <div className="flex flex-col gap-8">
        <header className="flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Knowledge Base</h1>
            <p className="text-gray-500 dark:text-slate-400">Manage the data your AI agents use to answer questions.</p>
          </div>
          <div className="flex gap-3">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="hidden"
              accept=".pdf,.docx,.txt"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="flex items-center gap-2 bg-gray-100 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 text-gray-900 dark:text-white px-5 py-2.5 rounded-xl font-medium transition-all border border-gray-300 dark:border-slate-700/50 disabled:opacity-50"
            >
              <Upload className="w-4 h-4" />
              {isUploading ? 'Uploading...' : 'Upload File'}
            </button>
            <button
              onClick={() => setIsManualModalOpen(true)}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-medium transition-all shadow-lg shadow-indigo-600/20"
            >
              <Plus className="w-4 h-4" />
              Add Manual Entry
            </button>
          </div>
        </header>

        {/* Search and Filters */}
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-slate-500" />
          <input
            type="text"
            placeholder="Search sources..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white dark:bg-slate-900/50 border border-gray-200 dark:border-slate-800 rounded-2xl py-3 pl-12 pr-4 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 transition-all"
          />
        </div>

        {/* Sources List */}
        <div className="bg-white dark:bg-slate-900/50 border border-gray-200 dark:border-slate-800 rounded-3xl overflow-hidden backdrop-blur-sm">
          {isLoading ? (
            <div className="p-20 flex flex-col items-center justify-center text-gray-400 dark:text-slate-500">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
              <p>Loading your knowledge base...</p>
            </div>
          ) : filteredSources.length > 0 ? (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-800/50 bg-gray-100 dark:bg-slate-800/20">
                  <th className="px-6 py-4 text-xs font-bold text-gray-400 dark:text-slate-500 uppercase tracking-widest">Source</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-400 dark:text-slate-500 uppercase tracking-widest">Type</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-400 dark:text-slate-500 uppercase tracking-widest">Status</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-400 dark:text-slate-500 uppercase tracking-widest">Added</th>
                  <th className="px-6 py-4"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-slate-800/50">
                {filteredSources.map((source) => (
                  <tr key={source.id} className="hover:bg-gray-100 dark:hover:bg-slate-800/30 transition-colors group">
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gray-100 dark:bg-slate-800 rounded-lg flex items-center justify-center border border-gray-300 dark:border-slate-700/50">
                          {source.source_type === 'file' ? (
                            <FileText className="w-5 h-5 text-indigo-400" />
                          ) : (
                            <Type className="w-5 h-5 text-purple-400" />
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">{source.name}</p>
                          {source.error_message && (
                            <p className="text-[11px] text-rose-500 mt-0.5 truncate max-w-[200px]">
                              {source.error_message}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <span className="text-xs font-medium text-gray-500 dark:text-slate-400 capitalize">{source.source_type}</span>
                    </td>
                    <td className="px-6 py-5">
                      <StatusBadge status={source.status} />
                    </td>
                    <td className="px-6 py-5">
                      <p className="text-xs text-gray-400 dark:text-slate-500">
                        {new Date(source.created_at).toLocaleDateString()}
                      </p>
                    </td>
                    <td className="px-6 py-5 text-right">
                      <button className="p-2 text-gray-400 dark:text-slate-500 hover:text-gray-900 dark:hover:text-white transition-colors">
                        <MoreVertical className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-20 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-gray-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center mb-6 text-gray-300 dark:text-slate-600">
                <Database className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">No data sources found</h3>
              <p className="text-gray-500 dark:text-slate-400 max-w-sm">
                Start by uploading a document or adding a manual entry to train your AI agents.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Manual Entry Slide-over */}
      {isManualModalOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div className="absolute inset-0 bg-gray-900/50 dark:bg-slate-950/80 backdrop-blur-sm transition-opacity" onClick={() => setIsManualModalOpen(false)} />
          <div className="absolute inset-y-0 right-0 max-w-full flex">
            <div className="w-screen max-w-2xl transform transition-all">
              <div className="h-full flex flex-col bg-white dark:bg-slate-900 border-l border-gray-200 dark:border-slate-800 shadow-2xl">
                <header className="p-6 border-b border-gray-200 dark:border-slate-800 flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">Add Manual Knowledge</h2>
                    <p className="text-sm text-gray-400 dark:text-slate-500">Create custom instructions or policies.</p>
                  </div>
                  <button onClick={() => setIsManualModalOpen(false)} className="p-2 text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:text-white transition-colors">
                    <Plus className="w-6 h-6 rotate-45" />
                  </button>
                </header>

                <div className="flex-grow overflow-y-auto p-6 space-y-6">
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-gray-600 dark:text-slate-300">Entry Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Refund Policy 2024"
                      value={manualName}
                      onChange={(e) => setManualName(e.target.value)}
                      className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-xl py-3 px-4 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 transition-all"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-gray-600 dark:text-slate-300">Content</label>
                    <Editor
                      value={manualContent}
                      onChange={setManualContent}
                    />
                  </div>
                </div>

                <footer className="p-6 border-t border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 flex gap-3">
                  <button
                    onClick={() => setIsManualModalOpen(false)}
                    className="flex-grow py-3 rounded-xl font-bold text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-800 transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveManual}
                    disabled={isSavingManual || !manualName || !manualContent}
                    className="flex-[2] bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-xl shadow-lg shadow-indigo-600/20 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {isSavingManual ? (
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    {isSavingManual ? 'Saving...' : 'Save Knowledge'}
                  </button>
                </footer>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}

function StatusBadge({ status }: { status: KnowledgeSource['status'] }) {
  const configs = {
    pending: { icon: <Clock className="w-3 h-3" />, color: 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-slate-400 border-gray-300 dark:border-slate-700' },
    processing: { icon: <Clock className="w-3 h-3 animate-spin" />, color: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' },
    completed: { icon: <CheckCircle2 className="w-3 h-3" />, color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
    failed: { icon: <AlertCircle className="w-3 h-3" />, color: 'bg-rose-500/10 text-rose-400 border-rose-500/20' }
  };

  const config = configs[status];

  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold border ${config.color}`}>
      {config.icon}
      <span className="capitalize">{status}</span>
    </div>
  );
}
