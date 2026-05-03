import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Bot, Mail, Lock, User as UserIcon, Loader2, ArrowRight, Check } from 'lucide-react';
import { useAuth } from '../lib/auth';
import api from '../lib/api';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/auth/register', {
        email,
        password,
        username
      });
      
      login(response.data.token.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col lg:flex-row">
      {/* Left Side: Info */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-indigo-600 p-12 flex-col justify-between overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,_var(--tw-gradient-stops))] from-indigo-900/40 via-transparent to-transparent" />
        
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-12">
            <Bot className="w-10 h-10 text-white" />
            <span className="text-2xl font-bold text-white tracking-tight">Antigravity</span>
          </div>
          
          <h2 className="text-5xl font-extrabold text-white leading-tight mb-6">
            Scale your support <br /> with AI agents.
          </h2>
          <p className="text-indigo-100 text-xl max-w-md leading-relaxed">
            Deploy hyper-personalized chat agents trained on your business data in minutes.
          </p>
        </div>

        <div className="relative z-10 space-y-6">
          <FeatureItem text="RAG-powered responses from your docs" />
          <FeatureItem text="Seamless embeddable chat widgets" />
          <FeatureItem text="Built-in lead generation & analytics" />
        </div>
      </div>

      {/* Right Side: Form */}
      <div className="flex-grow flex items-center justify-center p-6 bg-slate-950">
        <div className="w-full max-w-md">
          <div className="mb-8 lg:hidden flex flex-col items-center">
             <Bot className="w-12 h-12 text-indigo-600 mb-4" />
             <h1 className="text-2xl font-bold text-white">Create Account</h1>
          </div>
          
          <h1 className="hidden lg:block text-3xl font-bold text-white mb-2">Create your account</h1>
          <p className="hidden lg:block text-slate-400 mb-8">Join 500+ businesses scaling with Antigravity</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Full Name</label>
              <div className="relative">
                <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl py-3 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent transition-all"
                  placeholder="John Doe"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl py-3 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent transition-all"
                  placeholder="name@company.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl py-3 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent transition-all"
                  placeholder="••••••••"
                />
              </div>
              <p className="mt-2 text-xs text-slate-500">Must be at least 8 characters with numbers & symbols</p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold py-4 rounded-xl shadow-lg shadow-indigo-600/20 transition-all flex items-center justify-center gap-2 group mt-4"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  Create Account
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          <p className="mt-8 text-center text-slate-400 text-sm">
            Already have an account?{' '}
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-semibold">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function FeatureItem({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-3 text-indigo-100">
      <div className="bg-white/10 p-1 rounded-full">
        <Check className="w-4 h-4" />
      </div>
      <span className="font-medium">{text}</span>
    </div>
  );
}
