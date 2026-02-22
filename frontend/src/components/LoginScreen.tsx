import { useState } from 'react';
import type { AuthState } from '../store/AuthContext';
import * as api from '../api/client';
import './LoginScreen.css';

interface LoginScreenProps {
  onLogin: (auth: AuthState) => void;
}

type Mode = 'pick' | 'instructor' | 'student';

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [mode, setMode] = useState<Mode>('pick');
  const [token, setToken] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleInstructorLogin = async () => {
    if (!token.trim()) return;
    setError('');
    setLoading(true);
    try {
      // Validate the instructor token by making an authenticated request
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

  const handleStudentLogin = async () => {
    if (!joinCode.trim()) return;
    setError('');
    setLoading(true);
    try {
      const res = await api.studentLogin(joinCode.trim());
      onLogin({
        role: 'student',
        token: res.token,
        assignedTopologyId: res.topology_id,
      });
    } catch {
      setError('Invalid join code');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, handler: () => void) => {
    if (e.key === 'Enter') handler();
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-header">
          <h1 className="login-title">AE3GIS</h1>
          <span className="login-subtitle">Network Topology Platform</span>
        </div>

        {mode === 'pick' && (
          <div className="login-pick">
            <button className="login-role-btn instructor" onClick={() => setMode('instructor')}>
              Instructor
            </button>
            <button className="login-role-btn student" onClick={() => setMode('student')}>
              Student
            </button>
          </div>
        )}

        {mode === 'instructor' && (
          <div className="login-form">
            <label className="login-label">Instructor Token</label>
            <input
              className="login-input"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              onKeyDown={(e) => handleKeyDown(e, handleInstructorLogin)}
              placeholder="Enter token..."
              autoFocus
              disabled={loading}
            />
            {error && <div className="login-error">{error}</div>}
            <div className="login-actions">
              <button className="login-btn back" onClick={() => { setMode('pick'); setError(''); }}>
                Back
              </button>
              <button
                className="login-btn submit"
                onClick={handleInstructorLogin}
                disabled={loading || !token.trim()}
              >
                {loading ? 'Verifying...' : 'Login'}
              </button>
            </div>
          </div>
        )}

        {mode === 'student' && (
          <div className="login-form">
            <label className="login-label">Join Code</label>
            <input
              className="login-input"
              type="text"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              onKeyDown={(e) => handleKeyDown(e, handleStudentLogin)}
              placeholder="Enter join code..."
              autoFocus
              disabled={loading}
            />
            {error && <div className="login-error">{error}</div>}
            <div className="login-actions">
              <button className="login-btn back" onClick={() => { setMode('pick'); setError(''); }}>
                Back
              </button>
              <button
                className="login-btn submit"
                onClick={handleStudentLogin}
                disabled={loading || !joinCode.trim()}
              >
                {loading ? 'Verifying...' : 'Join'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
