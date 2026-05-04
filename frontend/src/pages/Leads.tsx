import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../lib/auth';
import api from '../lib/api';
import { Mail, User, Clock, ChevronLeft, ChevronRight } from 'lucide-react';

interface Lead {
  id: number;
  workspace_id: number;
  session_id: string | null;
  email: string;
  name: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export default function Leads() {
  const { token, user } = useAuth();
  const workspaceId = user?.workspace_id;

  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const pageSize = 25;

  useEffect(() => {
    fetchLeads();
  }, [workspaceId, page]);

  const fetchLeads = async () => {
    if (!workspaceId) return;
    try {
      setLoading(true);
      const res = await api.get(`/widget-admin/${workspaceId}/leads`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { skip: page * pageSize, limit: pageSize },
      });
      setLeads(res.data);
    } catch {
      setLeads([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (iso: string) => {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Leads</h1>
          <p className="text-sm text-slate-400 mt-1">
            Contacts captured from your chat widget.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : leads.length === 0 ? (
            <div className="text-center py-20 text-slate-500">
              <Mail className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No leads captured yet.</p>
              <p className="text-xs mt-1">
                Enable lead capture in your widget settings to start collecting contacts.
              </p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Captured
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4 text-indigo-400" />
                        <span className="text-sm text-white">{lead.email}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-slate-500" />
                        <span className="text-sm text-slate-300">
                          {lead.name || '—'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-slate-500" />
                        <span className="text-sm text-slate-400">
                          {formatDate(lead.created_at)}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Pagination */}
          {leads.length > 0 && (
            <div className="flex items-center justify-between px-6 py-3 border-t border-slate-800">
              <span className="text-xs text-slate-500">
                Page {page + 1}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-4 h-4 text-slate-300" />
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={leads.length < pageSize}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight className="w-4 h-4 text-slate-300" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
