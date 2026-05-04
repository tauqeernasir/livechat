import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../lib/auth';
import api from '../lib/api';
import {
    Copy,
    Check,
    RefreshCw,
    ToggleLeft,
    ToggleRight,
    ExternalLink,
} from 'lucide-react';

interface WidgetConfig {
    id: number;
    workspace_id: number;
    widget_key: string;
    is_active: boolean;
    allowed_origins: string[];
    position: string;
    primary_color: string;
    welcome_message: string;
    placeholder_text: string;
    icon_url: string | null;
    lead_capture_enabled: boolean;
    lead_capture_fields: string[];
    updated_at: string;
}

export default function WidgetSettings() {
    const { token, user } = useAuth();
    const workspaceId = user?.workspace_id;

    const [config, setConfig] = useState<WidgetConfig | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [copied, setCopied] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Editable fields
    const [primaryColor, setPrimaryColor] = useState('#6366f1');
    const [position, setPosition] = useState('bottom-right');
    const [welcomeMessage, setWelcomeMessage] = useState('');
    const [placeholderText, setPlaceholderText] = useState('');
    const [leadCaptureEnabled, setLeadCaptureEnabled] = useState(false);
    const [allowedOrigins, setAllowedOrigins] = useState('');

    useEffect(() => {
        fetchConfig();
    }, [workspaceId]);

    const fetchConfig = async () => {
        if (!workspaceId) return;
        try {
            setLoading(true);
            const res = await api.get(`/widget-admin/${workspaceId}`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = res.data;
            setConfig(data);
            setPrimaryColor(data.primary_color);
            setPosition(data.position);
            setWelcomeMessage(data.welcome_message);
            setPlaceholderText(data.placeholder_text);
            setLeadCaptureEnabled(data.lead_capture_enabled);
            setAllowedOrigins(data.allowed_origins.join(', '));
        } catch (err) {
            setError('Failed to load widget configuration');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!workspaceId || !config) return;
        try {
            setSaving(true);
            const res = await api.patch(
                `/widget-admin/${workspaceId}`,
                {
                    primary_color: primaryColor,
                    position,
                    welcome_message: welcomeMessage,
                    placeholder_text: placeholderText,
                    lead_capture_enabled: leadCaptureEnabled,
                    allowed_origins: allowedOrigins
                        .split(',')
                        .map((s) => s.trim())
                        .filter(Boolean),
                },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setConfig(res.data);
        } catch {
            setError('Failed to save');
        } finally {
            setSaving(false);
        }
    };

    const handleRotateKey = async () => {
        if (!workspaceId || !confirm('Rotate widget key? The old key will stop working immediately.'))
            return;
        try {
            const res = await api.post(`/widget-admin/${workspaceId}/rotate-key`, null, {
                headers: { Authorization: `Bearer ${token}` },
            });
            setConfig(res.data);
        } catch {
            setError('Failed to rotate key');
        }
    };

    const handleToggle = async () => {
        if (!workspaceId) return;
        try {
            const res = await api.post(`/widget-admin/${workspaceId}/toggle`, null, {
                headers: { Authorization: `Bearer ${token}` },
            });
            setConfig(res.data);
        } catch {
            setError('Failed to toggle widget');
        }
    };

    const copyEmbedCode = () => {
        if (!config) return;
        const code = `<script src="${window.location.origin}/widget/embed.js?key=${config.widget_key}"></script>`;
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center py-20">
                    <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="space-y-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-white">Chat Widget</h1>
                        <p className="text-sm text-slate-400 mt-1">
                            Embed a chat widget on your website to let visitors talk to your AI agent.
                        </p>
                    </div>
                    <button
                        onClick={handleToggle}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                        style={{
                            backgroundColor: config?.is_active ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                            color: config?.is_active ? '#22c55e' : '#ef4444',
                        }}
                    >
                        {config?.is_active ? (
                            <ToggleRight className="w-5 h-5" />
                        ) : (
                            <ToggleLeft className="w-5 h-5" />
                        )}
                        {config?.is_active ? 'Active' : 'Inactive'}
                    </button>
                </div>

                {error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                        {error}
                    </div>
                )}

                {/* Embed Code */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-3">Embed Code</h2>
                    <p className="text-sm text-slate-400 mb-4">
                        Copy and paste this script tag into your website's HTML, right before the closing{' '}
                        <code className="text-indigo-400">&lt;/body&gt;</code> tag.
                    </p>
                    <div className="flex items-center gap-2">
                        <code className="flex-1 bg-slate-800 px-4 py-3 rounded-lg text-sm text-green-400 font-mono overflow-x-auto">
                            {`<script src="${window.location.origin}/widget/embed.js?key=${config?.widget_key}"></script>`}
                        </code>
                        <button
                            onClick={copyEmbedCode}
                            className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                        >
                            {copied ? (
                                <Check className="w-5 h-5 text-green-400" />
                            ) : (
                                <Copy className="w-5 h-5 text-slate-400" />
                            )}
                        </button>
                    </div>
                    <div className="mt-3 flex items-center gap-4">
                        <span className="text-xs text-slate-500">
                            Key: <code className="text-slate-400">{config?.widget_key}</code>
                        </span>
                        <button
                            onClick={handleRotateKey}
                            className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors"
                        >
                            <RefreshCw className="w-3 h-3" />
                            Rotate Key
                        </button>
                    </div>
                </div>

                {/* Customization */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-6">Appearance</h2>
                    <div className="grid grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Primary Color
                            </label>
                            <div className="flex items-center gap-3">
                                <input
                                    type="color"
                                    value={primaryColor}
                                    onChange={(e) => setPrimaryColor(e.target.value)}
                                    className="w-10 h-10 rounded-lg border border-slate-700 cursor-pointer"
                                />
                                <input
                                    type="text"
                                    value={primaryColor}
                                    onChange={(e) => setPrimaryColor(e.target.value)}
                                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Position
                            </label>
                            <select
                                value={position}
                                onChange={(e) => setPosition(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                            >
                                <option value="bottom-right">Bottom Right</option>
                                <option value="bottom-left">Bottom Left</option>
                            </select>
                        </div>

                        <div className="col-span-2">
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Welcome Message
                            </label>
                            <input
                                type="text"
                                value={welcomeMessage}
                                onChange={(e) => setWelcomeMessage(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                            />
                        </div>

                        <div className="col-span-2">
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Placeholder Text
                            </label>
                            <input
                                type="text"
                                value={placeholderText}
                                onChange={(e) => setPlaceholderText(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                            />
                        </div>

                        <div className="col-span-2">
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Allowed Origins{' '}
                                <span className="text-slate-500">(comma-separated, leave empty for any)</span>
                            </label>
                            <input
                                type="text"
                                value={allowedOrigins}
                                onChange={(e) => setAllowedOrigins(e.target.value)}
                                placeholder="https://example.com, https://app.example.com"
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                            />
                        </div>
                    </div>
                </div>

                {/* Lead Capture */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-white">Lead Capture</h2>
                        <button
                            onClick={() => setLeadCaptureEnabled(!leadCaptureEnabled)}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${leadCaptureEnabled
                                    ? 'bg-green-500/10 text-green-400'
                                    : 'bg-slate-800 text-slate-400'
                                }`}
                        >
                            {leadCaptureEnabled ? (
                                <ToggleRight className="w-4 h-4" />
                            ) : (
                                <ToggleLeft className="w-4 h-4" />
                            )}
                            {leadCaptureEnabled ? 'Enabled' : 'Disabled'}
                        </button>
                    </div>
                    <p className="text-sm text-slate-400">
                        When enabled, visitors must enter their email before chatting. Leads are saved to your
                        dashboard.
                    </p>
                </div>

                {/* Save */}
                <div className="flex justify-end">
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                        {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>

                {/* Live Preview */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-4">Preview</h2>
                    <div className="relative bg-slate-800 rounded-lg h-96 overflow-hidden">
                        {/* Mini preview of the widget */}
                        <div className="absolute bottom-4 right-4 flex flex-col items-end gap-3">
                            <div
                                className="w-72 rounded-2xl overflow-hidden shadow-xl"
                                style={{ border: `1px solid ${primaryColor}20` }}
                            >
                                <div
                                    className="px-4 py-3 text-white text-sm font-semibold"
                                    style={{ backgroundColor: primaryColor }}
                                >
                                    Chat
                                </div>
                                <div className="bg-white p-4 text-center text-gray-500 text-sm h-48 flex items-center justify-center">
                                    {welcomeMessage || 'Hi! How can I help you today?'}
                                </div>
                                <div className="bg-white border-t px-3 py-2 flex items-center gap-2">
                                    <div className="flex-1 bg-gray-100 rounded-lg px-3 py-2 text-xs text-gray-400">
                                        {placeholderText || 'Type your message...'}
                                    </div>
                                    <div
                                        className="px-3 py-2 rounded-lg text-white text-xs"
                                        style={{ backgroundColor: primaryColor }}
                                    >
                                        Send
                                    </div>
                                </div>
                                <div className="bg-white text-center py-1 text-[10px] text-gray-300 border-t">
                                    Powered by Lagent
                                </div>
                            </div>
                            <div
                                className="w-12 h-12 rounded-full flex items-center justify-center shadow-lg"
                                style={{ backgroundColor: primaryColor }}
                            >
                                <ExternalLink className="w-5 h-5 text-white" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
}
