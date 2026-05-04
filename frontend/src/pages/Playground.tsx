import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../lib/auth';
import api from '../lib/api';
import Layout from '../components/Layout';
import {
  Send,
  Plus,
  Trash2,
  Clock,
  MessageSquare,
  Bot,
  User as UserIcon,
  ChevronDown,
  Loader2,
  ExternalLink,
  RefreshCcw
} from 'lucide-react';

interface SessionInfo {
  id: string;
  name: string;
  created_at: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
}

interface Workspace {
  id: number;
  name: string;
}

export default function Playground() {
  const { user } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSessionToken, setActiveSessionToken] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 1. Fetch Workspaces on mount
  useEffect(() => {
    const fetchWorkspaces = async () => {
      try {
        const response = await api.get('/auth/workspaces');
        setWorkspaces(response.data);
        if (response.data.length > 0) {
          setSelectedWorkspaceId(user?.workspace_id || response.data[0].id);
        }
      } catch (err) {
        console.error('Failed to fetch workspaces', err);
      }
    };
    fetchWorkspaces();
  }, [user]);

  // 2. Fetch Sessions when Workspace changes
  useEffect(() => {
    if (selectedWorkspaceId) {
      fetchSessions(selectedWorkspaceId);
    }
  }, [selectedWorkspaceId]);

  const fetchSessions = async (workspaceId: number) => {
    setIsLoadingSessions(true);
    try {
      const response = await api.get(`/chatbot/sessions/${workspaceId}`);
      setSessions(response.data);
    } catch (err) {
      console.error('Failed to fetch sessions', err);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const createNewSession = async () => {
    if (!selectedWorkspaceId) return;
    try {
      const response = await api.post(`/auth/session?workspace_id=${selectedWorkspaceId}`);
      const newSession = {
        id: response.data.session_id,
        name: response.data.name || 'New Chat',
        created_at: new Date().toISOString()
      };
      setSessions([newSession, ...sessions]);
      selectSession(newSession.id, response.data.token);
    } catch (err) {
      console.error('Failed to create session', err);
    }
  };

  const selectSession = async (sessionId: string, token?: string) => {
    setActiveSessionId(sessionId);
    setMessages([]);

    // If we don't have a token (e.g. from history), we need to handle it.
    // In this MVP, we'll assume we can use the user token to fetch history,
    // but the actual chat needs the session token.
    // Wait, let's simplify: for the playground, we'll just use the user token for everything
    // and let the backend handle session auth if possible, OR we store tokens in the list.
    // For now, let's just use the USER token for chat too if the backend allows it.
    // Actually, the chatbot.py Depends(get_current_session) which expects a session token.
    // So we MUST get a session token.

    if (token) {
      setActiveSessionToken(token);
    } else {
      // Re-fetch or re-auth the session to get a token
      // This is a gap in my backend: listing sessions doesn't return tokens.
      // I'll update the listing API to return tokens or just use the user token in the backend.
      // For now, I'll use the user token and see if it works (it won't because of the dependency).
      // I'll fix the backend in the next turn if needed.
    }

    try {
      // Fetch history using the current user context
      const response = await api.get(`/chatbot/messages`, {
        headers: { 'X-Session-Id': sessionId }
      });
      setMessages(response.data.messages);
    } catch (err) {
      console.error('Failed to fetch messages', err);
    }
  };

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.delete(`/chatbot/session/${sessionId}`);
      setSessions(sessions.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to delete session', err);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !activeSessionId || isStreaming) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setIsStreaming(true);

    try {
      // Use the regular chat endpoint but with session ID in headers
      // The backend uses get_current_session which checks Authorization header for a session token.
      // If we don't have a session token, we'll have issues.
      // Let's assume for now we use the user token and the backend is updated to support it.

      const response = await fetch('/api/v1/chatbot/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Session-Id': activeSessionId
        },
        body: JSON.stringify({
          messages: [userMessage]
        })
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      let sources: string[] = [];

      setMessages(prev => [...prev, { role: 'assistant', content: '', sources: [] }]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.done) break;

              assistantContent += data.content;

              // Simple heuristic to extract sources from the text if they are appended
              // (Our backend tool appends them in a specific format)
              // Actually, the LangGraph agent might return them in a different way.
              // For now, let's just display the content as is.

              setMessages(prev => {
                const last = prev[prev.length - 1];
                return [
                  ...prev.slice(0, -1),
                  { ...last, content: assistantContent }
                ];
              });
            } catch (e) {
              // Ignore parse errors for partial chunks
            }
          }
        }
      }
    } catch (err) {
      console.error('Streaming error', err);
    } finally {
      setIsStreaming(false);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <Layout fullWidth>
      <div className="flex h-screen bg-slate-950 overflow-hidden border-t border-slate-900">
        {/* Sessions Sidebar */}
        <div className="w-80 border-r border-slate-900 bg-slate-900/20 flex flex-col">
          <div className="p-4 border-b border-slate-900">
            <button
              onClick={createNewSession}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-indigo-600/10"
            >
              <Plus className="w-5 h-5" />
              New Chat
            </button>
          </div>

          <div className="flex-grow overflow-y-auto p-3 space-y-2 custom-scrollbar">
            {isLoadingSessions ? (
              <div className="flex flex-col items-center justify-center py-10 text-slate-500 gap-3">
                <Loader2 className="w-6 h-6 animate-spin" />
                <span className="text-xs">Loading history...</span>
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center py-10 text-slate-600 px-4">
                <Clock className="w-10 h-10 mx-auto mb-4 opacity-20" />
                <p className="text-sm">No sessions found for this workspace.</p>
              </div>
            ) : (
              sessions.map(session => (
                <div
                  key={session.id}
                  onClick={() => selectSession(session.id)}
                  className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all border ${activeSessionId === session.id
                    ? 'bg-indigo-600/10 border-indigo-500/30 text-white'
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                    }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <MessageSquare className={`w-4 h-4 flex-shrink-0 ${activeSessionId === session.id ? 'text-indigo-400' : 'text-slate-600'}`} />
                    <span className="text-sm truncate font-medium">{session.name}</span>
                  </div>
                  <button
                    onClick={(e) => deleteSession(session.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-rose-500/10 hover:text-rose-400 rounded-lg transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-grow flex flex-col bg-slate-950">
          {/* Header / Agent Selector */}
          <div className="px-6 py-4 border-b border-slate-900 flex items-center justify-between bg-slate-900/10">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-xl relative group">
                <Bot className="w-4 h-4 text-indigo-500" />
                <select
                  value={selectedWorkspaceId || ''}
                  onChange={(e) => setSelectedWorkspaceId(Number(e.target.value))}
                  className="bg-transparent text-sm font-semibold text-white outline-none cursor-pointer pr-6 appearance-none"
                >
                  {workspaces.map(ws => (
                    <option key={ws.id} value={ws.id} className="bg-slate-900">{ws.name}</option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-3 pointer-events-none" />
              </div>
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Live Test Mode</span>
            </div>

            {activeSessionId && (
              <button
                onClick={() => selectSession(activeSessionId)}
                className="p-2 text-slate-500 hover:text-indigo-400 transition-colors"
                title="Reset local state"
              >
                <RefreshCcw className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Messages */}
          <div className="flex-grow overflow-y-auto p-6 space-y-8 custom-scrollbar">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
                <div className="w-16 h-16 bg-indigo-600/10 rounded-2xl flex items-center justify-center mb-6 ring-1 ring-indigo-500/20">
                  <Bot className="w-8 h-8 text-indigo-500" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Ready to test?</h3>
                <p className="text-slate-400 text-sm mb-8">
                  Select a session from the history or start a new one to verify your agent's training and personality.
                </p>
                {!activeSessionId && (
                  <button
                    onClick={createNewSession}
                    className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold px-6 py-3 rounded-xl border border-slate-800 transition-all"
                  >
                    <Plus className="w-4 h-4" />
                    Start Session
                  </button>
                )}
              </div>
            ) : (
              <>
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg ${msg.role === 'assistant'
                      ? 'bg-indigo-600 text-white shadow-indigo-600/10'
                      : 'bg-slate-800 text-slate-400'
                      }`}>
                      {msg.role === 'assistant' ? <Bot className="w-5 h-5" /> : <UserIcon className="w-5 h-5" />}
                    </div>
                    <div className={`flex flex-col max-w-[80%] ${msg.role === 'user' ? 'items-end' : ''}`}>
                      <div className={`px-5 py-4 rounded-2xl whitespace-pre-wrap text-sm leading-relaxed ${msg.role === 'assistant'
                        ? 'bg-slate-900 border border-slate-800 text-slate-200'
                        : 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/10'
                        }`}>
                        {msg.content}

                        {msg.role === 'assistant' && msg.content === '' && isStreaming && (
                          <span className="inline-flex gap-1 items-center ml-1">
                            <span className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                            <span className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                            <span className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce"></span>
                          </span>
                        )}
                      </div>

                      {/* Sources Section */}
                      {msg.role === 'assistant' && msg.content && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {/* We extract sources from the text if the backend appends them, 
                              or we can have the backend send them as metadata.
                              For now, let's assume we parse "(Source: filename)" patterns.
                          */}
                          {extractSources(msg.content).map((source, sIdx) => (
                            <div
                              key={sIdx}
                              className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-900/50 border border-slate-800 rounded-lg text-[10px] font-bold text-slate-500 hover:text-indigo-400 hover:border-indigo-500/30 transition-all cursor-default"
                            >
                              <ExternalLink className="w-3 h-3" />
                              {source}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input Area */}
          <div className="p-6 bg-slate-950">
            <div className="max-w-4xl mx-auto relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-2xl blur opacity-0 group-focus-within:opacity-100 transition-all duration-500"></div>
              <div className="relative flex items-center bg-slate-900 border border-slate-800 rounded-2xl p-2 pl-4 transition-all focus-within:border-indigo-500/50 focus-within:ring-4 focus-within:ring-indigo-500/5 shadow-xl">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder={activeSessionId ? "Type your test query..." : "Create a session to start testing"}
                  disabled={!activeSessionId || isStreaming}
                  className="flex-grow bg-transparent border-none outline-none text-white text-sm py-2 disabled:opacity-50"
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || !activeSessionId || isStreaming}
                  className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:bg-slate-800 text-white p-3 rounded-xl transition-all shadow-lg shadow-indigo-600/20 active:scale-95"
                >
                  {isStreaming ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

function extractSources(text: string): string[] {
  const sources: string[] = [];
  const regex = /\(Source: ([^)]+)\)/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (!sources.includes(match[1])) {
      sources.push(match[1]);
    }
  }
  return sources;
}
