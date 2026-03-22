import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    if (!localStorage.getItem('token')) { setLoading(false); return; }
    try {
      const profile = await api.getProfile();
      setUser(profile);
    } catch {
      api.setToken(null);
      setUser(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadUser(); }, [loadUser]);

  const login = async (email, password) => {
    const data = await api.login(email, password);
    api.setToken(data.access_token);
    const profile = await api.getProfile();
    setUser(profile);
    return profile;
  };

  const register = async (email, password, name) => {
    const data = await api.register(email, password, name);
    api.setToken(data.access_token);
    const profile = await api.getProfile();
    setUser(profile);
    return profile;
  };

  const logout = () => {
    api.setToken(null);
    setUser(null);
  };

  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
