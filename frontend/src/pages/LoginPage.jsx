import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Sparkles, Loader2 } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export default function LoginPage() {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            if (!isLogin) {
                // SIGNUP: Backend mein email ko hi username ki tarah bhej rahe hain
                const regRes = await fetch(`${API_BASE}/api/auth/users/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        username: email,  // <-- EMAIL AS USERNAME
                        email: email, 
                        password, 
                        re_password: password 
                    })
                });
                
                const regData = await regRes.json();

                if (!regRes.ok) {
                    const errorMsg = Object.values(regData).flat()[0] || 'Signup failed. Use a strong password.';
                    throw new Error(errorMsg);
                }
            }

            // LOGIN: Wahi email as username bhej rahe hain
            const loginRes = await fetch(`${API_BASE}/api/auth/token/login/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    username: email, // <-- EMAIL AS USERNAME
                    password 
                }) 
            });
            
            const loginData = await loginRes.json();
            
            if (!loginRes.ok) {
                throw new Error(loginData.non_field_errors?.[0] || 'Unable to log in with provided credentials.');
            }

            login(loginData.auth_token);
            window.location.href = '/'; 

        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4">
            <div className="w-full max-w-md p-8 bg-slate-900/80 border border-slate-800 rounded-2xl backdrop-blur-sm">
                <div className="flex items-center gap-3 mb-8 justify-center">
                    <div className="p-2 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-500/30">
                        <Sparkles className="w-6 h-6 text-white" />
                    </div>
                    <span className="font-bold text-2xl tracking-wide text-white">ExpenseAI</span>
                </div>

                <h2 className="text-xl font-bold text-white text-center mb-6">
                    {isLogin ? 'Welcome Back' : 'Create an Account'}
                </h2>

                {error && (
                    <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg text-center">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">Email Address</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full bg-slate-950 text-white text-sm px-4 py-2.5 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
                            placeholder="you@example.com"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">Password</label>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-slate-950 text-white text-sm px-4 py-2.5 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
                            placeholder="••••••••"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl transition flex justify-center items-center mt-6 shadow-lg shadow-indigo-600/20"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (isLogin ? 'Log In' : 'Sign Up')}
                    </button>
                </form>

                <p className="mt-6 text-center text-xs text-slate-400">
                    {isLogin ? "Don't have an account? " : "Already have an account? "}
                    <button
                        onClick={() => { setIsLogin(!isLogin); setError(''); }}
                        className="text-indigo-400 hover:underline font-semibold"
                    >
                        {isLogin ? 'Sign Up' : 'Log In'}
                    </button>
                </p>
            </div>
        </div>
    );
}