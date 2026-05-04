import React, { useState, useEffect, useCallback } from 'react';
import {
    Plus,
    Link2,
    RefreshCw,
    CheckCircle2,
    AlertCircle,
    Clock,
    Search,
    Trash2,
    Power,
    PowerOff,
    Globe,
    ChevronDown,
    ChevronRight,
    Save,
    ExternalLink,
    FileJson,
    ToggleLeft,
    ToggleRight,
} from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../lib/auth';
import Layout from '../components/Layout';

// ─── Types ───────────────────────────────────────────────────────────

interface Operation {
    id: number;
    operation_id: string;
    method: string;
    path: string;
    summary: string | null;
    description: string | null;
    enabled: boolean;
}

interface Integration {
    id: number;
    workspace_id: number;
    name: string;
    integration_type: string;
    spec_url: string | null;
    auth_type: string;
    base_url: string | null;
    status: 'pending' | 'syncing' | 'active' | 'error' | 'disabled';
    error_message: string | null;
    enabled: boolean;
    created_at: string;
    updated_at: string;
    operations: Operation[];
}

// ─── Main Component ──────────────────────────────────────────────────

export default function Integrations() {
    const { user } = useAuth();
    const [integrations, setIntegrations] = useState<Integration[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [expandedId, setExpandedId] = useState<number | null>(null);

    // Create form state
    const [createName, setCreateName] = useState('');
    const [createSpecMode, setCreateSpecMode] = useState<'url' | 'json'>('url');
    const [createSpecUrl, setCreateSpecUrl] = useState('');
    const [createSpecJson, setCreateSpecJson] = useState('');
    const [createAuthType, setCreateAuthType] = useState('none');
    const [createAuthHeader, setCreateAuthHeader] = useState('Authorization');
    const [createCredentials, setCreateCredentials] = useState('');
    const [createBaseUrl, setCreateBaseUrl] = useState('');
    const [isCreating, setIsCreating] = useState(false);
    const [createError, setCreateError] = useState('');

    // Edit state
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editName, setEditName] = useState('');
    const [editAuthType, setEditAuthType] = useState('');
    const [editAuthHeader, setEditAuthHeader] = useState('');
    const [editCredentials, setEditCredentials] = useState('');
    const [editBaseUrl, setEditBaseUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    const fetchIntegrations = useCallback(async () => {
        if (!user?.workspace_id) return;
        try {
            const response = await api.get(`/integrations?workspace_id=${user.workspace_id}`);
            setIntegrations(response.data.integrations || []);
        } catch (error) {
            console.error('Failed to fetch integrations:', error);
            setIntegrations([]);
        } finally {
            setIsLoading(false);
        }
    }, [user?.workspace_id]);

    useEffect(() => {
        fetchIntegrations();
    }, [fetchIntegrations]);

    // ─── Create ──────────────────────────────────────────────────────

    const resetCreateForm = () => {
        setCreateName('');
        setCreateSpecMode('url');
        setCreateSpecUrl('');
        setCreateSpecJson('');
        setCreateAuthType('none');
        setCreateAuthHeader('Authorization');
        setCreateCredentials('');
        setCreateBaseUrl('');
        setCreateError('');
    };

    const handleCreate = async () => {
        if (!createName || !user?.workspace_id) return;
        setIsCreating(true);
        setCreateError('');

        let specContent: object | undefined;
        if (createSpecMode === 'json') {
            try {
                specContent = JSON.parse(createSpecJson);
            } catch {
                setCreateError('Invalid JSON. Please check your OpenAPI spec.');
                setIsCreating(false);
                return;
            }
        }

        try {
            await api.post(`/integrations?workspace_id=${user.workspace_id}`, {
                name: createName,
                spec_url: createSpecMode === 'url' ? createSpecUrl : undefined,
                spec_content: createSpecMode === 'json' ? specContent : undefined,
                auth_type: createAuthType,
                auth_header_name: createAuthHeader,
                credentials: createCredentials || undefined,
                base_url: createBaseUrl || undefined,
            });
            setIsCreateOpen(false);
            resetCreateForm();
            fetchIntegrations();
        } catch (error: any) {
            const detail = error?.response?.data?.detail;
            setCreateError(typeof detail === 'string' ? detail : 'Failed to create integration.');
        } finally {
            setIsCreating(false);
        }
    };

    // ─── Update ──────────────────────────────────────────────────────

    const startEditing = (integration: Integration) => {
        setEditingId(integration.id);
        setEditName(integration.name);
        setEditAuthType(integration.auth_type);
        setEditAuthHeader('Authorization');
        setEditCredentials('');
        setEditBaseUrl(integration.base_url || '');
    };

    const handleUpdate = async (integrationId: number) => {
        if (!user?.workspace_id) return;
        setIsSaving(true);
        try {
            await api.patch(
                `/integrations/${integrationId}?workspace_id=${user.workspace_id}`,
                {
                    name: editName || undefined,
                    auth_type: editAuthType || undefined,
                    auth_header_name: editAuthHeader || undefined,
                    credentials: editCredentials || undefined,
                    base_url: editBaseUrl || undefined,
                }
            );
            setEditingId(null);
            fetchIntegrations();
        } catch (error) {
            console.error('Failed to update integration:', error);
            alert('Failed to save changes.');
        } finally {
            setIsSaving(false);
        }
    };

    // ─── Toggle / Delete / Sync ──────────────────────────────────────

    const handleToggle = async (integration: Integration) => {
        if (!user?.workspace_id) return;
        try {
            await api.patch(
                `/integrations/${integration.id}?workspace_id=${user.workspace_id}`,
                { enabled: !integration.enabled }
            );
            fetchIntegrations();
        } catch (error) {
            console.error('Failed to toggle integration:', error);
        }
    };

    const handleDelete = async (integrationId: number) => {
        if (!user?.workspace_id) return;
        if (!confirm('Delete this integration and all its operations?')) return;
        try {
            await api.delete(`/integrations/${integrationId}?workspace_id=${user.workspace_id}`);
            fetchIntegrations();
        } catch (error) {
            console.error('Failed to delete integration:', error);
        }
    };

    const handleSync = async (integrationId: number) => {
        if (!user?.workspace_id) return;
        try {
            await api.post(`/integrations/${integrationId}/sync?workspace_id=${user.workspace_id}`);
            fetchIntegrations();
        } catch (error: any) {
            const detail = error?.response?.data?.detail;
            alert(typeof detail === 'string' ? detail : 'Sync failed.');
        }
    };

    const handleToggleOperation = async (integrationId: number, operationId: number, enabled: boolean) => {
        if (!user?.workspace_id) return;
        try {
            await api.post(
                `/integrations/${integrationId}/operations/toggle?workspace_id=${user.workspace_id}`,
                { operation_ids: [operationId], enabled }
            );
            fetchIntegrations();
        } catch (error) {
            console.error('Failed to toggle operation:', error);
        }
    };

    const handleToggleAllOperations = async (integration: Integration, enabled: boolean) => {
        if (!user?.workspace_id || integration.operations.length === 0) return;
        try {
            await api.post(
                `/integrations/${integration.id}/operations/toggle?workspace_id=${user.workspace_id}`,
                { operation_ids: integration.operations.map(op => op.id), enabled }
            );
            fetchIntegrations();
        } catch (error) {
            console.error('Failed to toggle all operations:', error);
        }
    };

    // ─── Render ──────────────────────────────────────────────────────

    const filteredIntegrations = integrations.filter(i =>
        i.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <Layout>
            <div className="flex flex-col gap-8">
                {/* Header */}
                <header className="flex items-end justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Integrations</h1>
                        <p className="text-gray-500 dark:text-slate-400">Connect external APIs so your agent can fetch live data.</p>
                    </div>
                    <button
                        onClick={() => setIsCreateOpen(true)}
                        className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-gray-900 dark:text-white px-5 py-2.5 rounded-xl font-medium transition-all shadow-lg shadow-indigo-600/20"
                    >
                        <Plus className="w-4 h-4" />
                        Connect API
                    </button>
                </header>

                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search integrations..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full bg-white dark:bg-slate-900/50 border border-gray-200 dark:border-slate-800 rounded-2xl py-3 pl-12 pr-4 text-gray-900 dark:text-white placeholder:text-gray-300 dark:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 transition-all"
                    />
                </div>

                {/* List */}
                <div className="space-y-4">
                    {isLoading ? (
                        <div className="bg-white dark:bg-slate-900/50 border border-gray-200 dark:border-slate-800 rounded-3xl p-20 flex flex-col items-center justify-center text-gray-400 dark:text-slate-500">
                            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
                            <p>Loading integrations...</p>
                        </div>
                    ) : filteredIntegrations.length > 0 ? (
                        filteredIntegrations.map((integration) => (
                            <IntegrationCard
                                key={integration.id}
                                integration={integration}
                                isExpanded={expandedId === integration.id}
                                isEditing={editingId === integration.id}
                                onToggleExpand={() => setExpandedId(expandedId === integration.id ? null : integration.id)}
                                onToggle={() => handleToggle(integration)}
                                onSync={() => handleSync(integration.id)}
                                onDelete={() => handleDelete(integration.id)}
                                onStartEdit={() => startEditing(integration)}
                                onCancelEdit={() => setEditingId(null)}
                                onSaveEdit={() => handleUpdate(integration.id)}
                                isSaving={isSaving}
                                editName={editName}
                                setEditName={setEditName}
                                editAuthType={editAuthType}
                                setEditAuthType={setEditAuthType}
                                editAuthHeader={editAuthHeader}
                                setEditAuthHeader={setEditAuthHeader}
                                editCredentials={editCredentials}
                                setEditCredentials={setEditCredentials}
                                editBaseUrl={editBaseUrl}
                                setEditBaseUrl={setEditBaseUrl}
                                onToggleOperation={(opId, enabled) => handleToggleOperation(integration.id, opId, enabled)}
                                onToggleAllOperations={(enabled) => handleToggleAllOperations(integration, enabled)}
                            />
                        ))
                    ) : (
                        <div className="bg-white dark:bg-slate-900/50 border border-gray-200 dark:border-slate-800 rounded-3xl p-20 flex flex-col items-center justify-center text-center">
                            <div className="w-16 h-16 bg-gray-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center mb-6 text-gray-300 dark:text-slate-600">
                                <Globe className="w-8 h-8" />
                            </div>
                            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">No integrations yet</h3>
                            <p className="text-gray-500 dark:text-slate-400 max-w-sm">
                                Connect an external API by providing its OpenAPI spec so your agent can query live data.
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* Create Slide-over */}
            {isCreateOpen && (
                <div className="fixed inset-0 z-50 overflow-hidden">
                    <div className="absolute inset-0 bg-gray-900/50 dark:bg-slate-950/80 backdrop-blur-sm" onClick={() => { setIsCreateOpen(false); resetCreateForm(); }} />
                    <div className="absolute inset-y-0 right-0 max-w-full flex">
                        <div className="w-screen max-w-2xl">
                            <div className="h-full flex flex-col bg-white dark:bg-slate-900 border-l border-gray-200 dark:border-slate-800 shadow-2xl">
                                <header className="p-6 border-b border-gray-200 dark:border-slate-800 flex items-center justify-between">
                                    <div>
                                        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Connect API</h2>
                                        <p className="text-sm text-gray-400 dark:text-slate-500">Provide an OpenAPI spec to register callable endpoints.</p>
                                    </div>
                                    <button onClick={() => { setIsCreateOpen(false); resetCreateForm(); }} className="p-2 text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:text-white transition-colors">
                                        <Plus className="w-6 h-6 rotate-45" />
                                    </button>
                                </header>

                                <div className="flex-grow overflow-y-auto p-6 space-y-6">
                                    {/* Name */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-semibold text-gray-600 dark:text-slate-300">Integration Name</label>
                                        <input
                                            type="text"
                                            placeholder="e.g. Order Service"
                                            value={createName}
                                            onChange={(e) => setCreateName(e.target.value)}
                                            className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-xl py-3 px-4 text-gray-900 dark:text-white placeholder:text-gray-300 dark:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 transition-all"
                                        />
                                    </div>

                                    {/* Spec Source */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-semibold text-gray-600 dark:text-slate-300">OpenAPI Spec</label>
                                        <div className="flex gap-2 mb-3">
                                            <button
                                                onClick={() => setCreateSpecMode('url')}
                                                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${createSpecMode === 'url'
                                                        ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-600/30'
                                                        : 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-slate-400 border border-gray-300 dark:border-slate-700 hover:bg-gray-200 dark:hover:bg-slate-700'
                                                    }`}
                                            >
                                                <Link2 className="w-4 h-4" />
                                                From URL
                                            </button>
                                            <button
                                                onClick={() => setCreateSpecMode('json')}
                                                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${createSpecMode === 'json'
                                                        ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-600/30'
                                                        : 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-slate-400 border border-gray-300 dark:border-slate-700 hover:bg-gray-200 dark:hover:bg-slate-700'
                                                    }`}
                                            >
                                                <FileJson className="w-4 h-4" />
                                                Paste JSON
                                            </button>
                                        </div>
                                        {createSpecMode === 'url' ? (
                                            <input
                                                type="url"
                                                placeholder="https://api.example.com/openapi.json"
                                                value={createSpecUrl}
                                                onChange={(e) => setCreateSpecUrl(e.target.value)}
                                                className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-xl py-3 px-4 text-gray-900 dark:text-white placeholder:text-gray-300 dark:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 transition-all"
                                            />
                                        ) : (
                                            <textarea
                                                placeholder='{"openapi": "3.0.0", ...}'
                                                value={createSpecJson}
                                                onChange={(e) => setCreateSpecJson(e.target.value)}
                                                rows={10}
                                                className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-xl py-3 px-4 text-gray-900 dark:text-white placeholder:text-gray-300 dark:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 transition-all font-mono text-sm resize-none"
                                            />
                                        )}
                                    </div>

                                    {/* Auth */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-semibold text-gray-600 dark:text-slate-300">Authentication</label>
                                        <select
                                            value={createAuthType}
                                            onChange={(e) => setCreateAuthType(e.target.value)}
                                            className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-xl py-3 px-4 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-600/20 transition-all"
                                        >
                                            <option value="none">No Authentication</option>
                                            <option value="bearer">Bearer Token</option>
                                            <option value="api_key">API Key (Header)</option>
                                            <option value="header">Custom Header</option>
                                        </select>
                                    </div>

                                    {createAuthType !== 'none' && (
                                        <>
                                            {createAuthType === 'header' && (
                                                <div className="space-y-2">
                                                    <label className="text-sm font-semibold text-gray-600 dark:text-slate-300">Header Name</label>
                                                    <input
                                                        type="text"
                                                        placeholder="X-API-Key"
                                                        value={createAuthHeader}
                                                        onChange={(e) => setCreateAuthHeader(e.target.value)}
                                                        className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-xl py-3 px-4 text-gray-900 dark:text-white placeholder:text-gray-300 dark:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 transition-all"
                                                    />
                                                </div>
                                            )}
                                            <div className="space-y-2">
                                                <label className="text-sm font-semibold text-gray-600 dark:text-slate-300">
                                                    {createAuthType === 'bearer' ? 'Bearer Token' : 'API Key / Secret'}
                                                </label>
                                                <input
                                                    type="password"
                                                    placeholder="••••••••••••••••"
                                                    value={createCredentials}
                                                    onChange={(e) => setCreateCredentials(e.target.value)}
                                                    className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-xl py-3 px-4 text-gray-900 dark:text-white placeholder:text-gray-300 dark:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 transition-all"
                                                />
                                            </div>
                                        </>
                                    )}

                                    {/* Base URL override */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-semibold text-gray-600 dark:text-slate-300">
                                            Base URL <span className="text-gray-400 dark:text-slate-500 font-normal">(optional — auto-detected from spec)</span>
                                        </label>
                                        <input
                                            type="url"
                                            placeholder="https://api.example.com/v1"
                                            value={createBaseUrl}
                                            onChange={(e) => setCreateBaseUrl(e.target.value)}
                                            className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-xl py-3 px-4 text-gray-900 dark:text-white placeholder:text-gray-300 dark:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 transition-all"
                                        />
                                    </div>

                                    {createError && (
                                        <div className="flex items-center gap-2 text-sm text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-xl px-4 py-3">
                                            <AlertCircle className="w-4 h-4 flex-shrink-0" />
                                            {createError}
                                        </div>
                                    )}
                                </div>

                                <footer className="p-6 border-t border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 flex gap-3">
                                    <button
                                        onClick={() => { setIsCreateOpen(false); resetCreateForm(); }}
                                        className="flex-grow py-3 rounded-xl font-bold text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:text-white hover:bg-gray-100 dark:bg-slate-800 transition-all"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleCreate}
                                        disabled={isCreating || !createName || (createSpecMode === 'url' ? !createSpecUrl : !createSpecJson)}
                                        className="flex-[2] bg-indigo-600 hover:bg-indigo-500 text-gray-900 dark:text-white font-bold py-3 rounded-xl shadow-lg shadow-indigo-600/20 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                                    >
                                        {isCreating ? (
                                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        ) : (
                                            <Link2 className="w-4 h-4" />
                                        )}
                                        {isCreating ? 'Connecting...' : 'Connect'}
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

// ─── Integration Card ──────────────────────────────────────────────

interface IntegrationCardProps {
    integration: Integration;
    isExpanded: boolean;
    isEditing: boolean;
    onToggleExpand: () => void;
    onToggle: () => void;
    onSync: () => void;
    onDelete: () => void;
    onStartEdit: () => void;
    onCancelEdit: () => void;
    onSaveEdit: () => void;
    isSaving: boolean;
    editName: string;
    setEditName: (v: string) => void;
    editAuthType: string;
    setEditAuthType: (v: string) => void;
    editAuthHeader: string;
    setEditAuthHeader: (v: string) => void;
    editCredentials: string;
    setEditCredentials: (v: string) => void;
    editBaseUrl: string;
    setEditBaseUrl: (v: string) => void;
    onToggleOperation: (opId: number, enabled: boolean) => void;
    onToggleAllOperations: (enabled: boolean) => void;
}

function IntegrationCard({
    integration,
    isExpanded,
    isEditing,
    onToggleExpand,
    onToggle,
    onSync,
    onDelete,
    onStartEdit,
    onCancelEdit,
    onSaveEdit,
    isSaving,
    editName,
    setEditName,
    editAuthType,
    setEditAuthType,
    editAuthHeader,
    setEditAuthHeader,
    editCredentials,
    setEditCredentials,
    editBaseUrl,
    setEditBaseUrl,
    onToggleOperation,
    onToggleAllOperations,
}: IntegrationCardProps) {
    const enabledCount = integration.operations.filter(op => op.enabled).length;
    const totalCount = integration.operations.length;

    return (
        <div className="bg-white dark:bg-slate-900/50 border border-gray-200 dark:border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
            {/* Card Header */}
            <div className="px-6 py-5 flex items-center justify-between">
                <div className="flex items-center gap-4 flex-grow min-w-0">
                    <div className="w-10 h-10 bg-gray-100 dark:bg-slate-800 rounded-lg flex items-center justify-center border border-gray-300 dark:border-slate-700/50 flex-shrink-0">
                        <Globe className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div className="min-w-0">
                        <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate">{integration.name}</h3>
                            <StatusBadge status={integration.status} />
                        </div>
                        <div className="flex items-center gap-3 mt-0.5">
                            {integration.base_url && (
                                <span className="text-[11px] text-gray-400 dark:text-slate-500 truncate max-w-[300px]">{integration.base_url}</span>
                            )}
                            <span className="text-[11px] text-gray-300 dark:text-slate-600">
                                {enabledCount}/{totalCount} endpoints active
                            </span>
                        </div>
                        {integration.error_message && (
                            <p className="text-[11px] text-rose-500 mt-1 truncate max-w-[400px]">{integration.error_message}</p>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                    {integration.spec_url && (
                        <button
                            onClick={onSync}
                            title="Re-sync spec"
                            className="p-2 text-gray-400 dark:text-slate-500 hover:text-indigo-400 transition-colors"
                        >
                            <RefreshCw className="w-4 h-4" />
                        </button>
                    )}
                    <button
                        onClick={onToggle}
                        title={integration.enabled ? 'Disable' : 'Enable'}
                        className={`p-2 transition-colors ${integration.enabled ? 'text-emerald-400 hover:text-emerald-300' : 'text-gray-300 dark:text-slate-600 hover:text-gray-500 dark:text-slate-400'}`}
                    >
                        {integration.enabled ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
                    </button>
                    <button
                        onClick={onStartEdit}
                        title="Edit"
                        className="p-2 text-gray-400 dark:text-slate-500 hover:text-gray-900 dark:text-white transition-colors"
                    >
                        <ExternalLink className="w-4 h-4" />
                    </button>
                    <button
                        onClick={onDelete}
                        title="Delete"
                        className="p-2 text-gray-400 dark:text-slate-500 hover:text-rose-400 transition-colors"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                    <button
                        onClick={onToggleExpand}
                        className="p-2 text-gray-400 dark:text-slate-500 hover:text-gray-900 dark:text-white transition-colors"
                    >
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </button>
                </div>
            </div>

            {/* Edit Panel */}
            {isEditing && (
                <div className="px-6 pb-5 border-t border-gray-200 dark:border-gray-200 dark:border-slate-800/50 pt-5 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-gray-500 dark:text-slate-400">Name</label>
                            <input
                                type="text"
                                value={editName}
                                onChange={(e) => setEditName(e.target.value)}
                                className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg py-2 px-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-600/20"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-gray-500 dark:text-slate-400">Auth Type</label>
                            <select
                                value={editAuthType}
                                onChange={(e) => setEditAuthType(e.target.value)}
                                className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg py-2 px-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-600/20"
                            >
                                <option value="none">None</option>
                                <option value="bearer">Bearer Token</option>
                                <option value="api_key">API Key</option>
                                <option value="header">Custom Header</option>
                            </select>
                        </div>
                        {editAuthType !== 'none' && (
                            <>
                                {editAuthType === 'header' && (
                                    <div className="space-y-1.5">
                                        <label className="text-xs font-semibold text-gray-500 dark:text-slate-400">Header Name</label>
                                        <input
                                            type="text"
                                            value={editAuthHeader}
                                            onChange={(e) => setEditAuthHeader(e.target.value)}
                                            className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg py-2 px-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-600/20"
                                        />
                                    </div>
                                )}
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-gray-500 dark:text-slate-400">New Credential</label>
                                    <input
                                        type="password"
                                        placeholder="Leave blank to keep current"
                                        value={editCredentials}
                                        onChange={(e) => setEditCredentials(e.target.value)}
                                        className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg py-2 px-3 text-sm text-gray-900 dark:text-white placeholder:text-gray-300 dark:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20"
                                    />
                                </div>
                            </>
                        )}
                        <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-gray-500 dark:text-slate-400">Base URL</label>
                            <input
                                type="url"
                                value={editBaseUrl}
                                onChange={(e) => setEditBaseUrl(e.target.value)}
                                className="w-full bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg py-2 px-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-600/20"
                            />
                        </div>
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                        <button
                            onClick={onCancelEdit}
                            className="px-4 py-2 text-sm font-medium text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:text-white hover:bg-gray-100 dark:bg-slate-800 rounded-lg transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={onSaveEdit}
                            disabled={isSaving}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-gray-900 dark:text-white rounded-lg transition-all disabled:opacity-50"
                        >
                            {isSaving ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save className="w-4 h-4" />}
                            Save
                        </button>
                    </div>
                </div>
            )}

            {/* Operations Table */}
            {isExpanded && integration.operations.length > 0 && (
                <div className="border-t border-gray-200 dark:border-gray-200 dark:border-slate-800/50">
                    <div className="px-6 py-3 bg-gray-100 dark:bg-slate-800/20 flex items-center justify-between">
                        <span className="text-xs font-bold text-gray-400 dark:text-slate-500 uppercase tracking-widest">Endpoints</span>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => onToggleAllOperations(true)}
                                className="text-[11px] font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
                            >
                                Enable All
                            </button>
                            <span className="text-gray-300 dark:text-slate-700">|</span>
                            <button
                                onClick={() => onToggleAllOperations(false)}
                                className="text-[11px] font-medium text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:text-slate-300 transition-colors"
                            >
                                Disable All
                            </button>
                        </div>
                    </div>
                    <div className="divide-y divide-slate-800/50">
                        {integration.operations.map((op) => (
                            <div key={op.id} className="px-6 py-3 flex items-center justify-between hover:bg-gray-100 dark:bg-slate-800/20 transition-colors">
                                <div className="flex items-center gap-3 min-w-0">
                                    <MethodBadge method={op.method} />
                                    <span className="text-sm text-gray-600 dark:text-slate-300 font-mono truncate">{op.path}</span>
                                    {op.summary && (
                                        <span className="text-xs text-gray-400 dark:text-slate-500 truncate max-w-[250px]">{op.summary}</span>
                                    )}
                                </div>
                                <button
                                    onClick={() => onToggleOperation(op.id, !op.enabled)}
                                    className="flex-shrink-0"
                                >
                                    {op.enabled ? (
                                        <ToggleRight className="w-6 h-6 text-emerald-400" />
                                    ) : (
                                        <ToggleLeft className="w-6 h-6 text-gray-300 dark:text-slate-600" />
                                    )}
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── Shared Components ─────────────────────────────────────────────

function StatusBadge({ status }: { status: Integration['status'] }) {
    const configs = {
        pending: { icon: <Clock className="w-3 h-3" />, color: 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-slate-400 border-gray-300 dark:border-slate-700' },
        syncing: { icon: <RefreshCw className="w-3 h-3 animate-spin" />, color: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' },
        active: { icon: <CheckCircle2 className="w-3 h-3" />, color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
        error: { icon: <AlertCircle className="w-3 h-3" />, color: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
        disabled: { icon: <PowerOff className="w-3 h-3" />, color: 'bg-gray-100 dark:bg-slate-800 text-gray-400 dark:text-slate-500 border-gray-300 dark:border-slate-700' },
    };
    const config = configs[status];
    return (
        <div className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${config.color}`}>
            {config.icon}
            <span className="capitalize">{status}</span>
        </div>
    );
}

function MethodBadge({ method }: { method: string }) {
    const colors: Record<string, string> = {
        GET: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
        HEAD: 'bg-slate-700/50 text-gray-500 dark:text-slate-400 border-slate-600',
        POST: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
        PUT: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        PATCH: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
        DELETE: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    };
    return (
        <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold border ${colors[method] || colors.GET}`}>
            {method}
        </span>
    );
}
