import { createContext, useContext } from 'react';

export type UserRole = 'instructor' | 'student';

export interface AuthState {
  role: UserRole;
  token: string;
  assignedTopologyId: string | null;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthContext.Provider');
  return ctx;
}
