import { useState } from 'react';
import type { AuthState } from '../store/AuthContext';
import * as api from '../api/client';
import './LoginScreen.css';

interface LoginScreenProps {
  onLogin: (auth: AuthState) => void;
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!token.trim()) return;
    setError('');
    setLoading(true);
    try {
      api.setAuthToken(token.trim());
      await api.listTopologies();
      onLogin({ role: 'instructor', token: token.trim(), assignedTopologyId: null });
    } catch {
      api.setAuthToken(null);
      setError('Invalid instructor token');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-header">
          <h1 className="login-title">AE3GIS</h1>
          <span className="login-subtitle">Network Topology Platform</span>
        </div>
        <div className="login-form">
          <label className="login-label">Instructor Token</label>
          <input
            className="login-input"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') void handleLogin(); }}
            placeholder="Enter token..."
            autoFocus
            disabled={loading}
          />
          {error && <div className="login-error">{error}</div>}
          <div className="login-actions">
            <button
              className="login-btn submit"
              onClick={handleLogin}
              disabled={loading || !token.trim()}
            >
              {loading ? 'Verifying...' : 'Login'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
