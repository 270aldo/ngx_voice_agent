/**
 * Authentication Hook
 * 
 * Provides authentication state and methods throughout the app
 */

import { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  setAuthToken, 
  setUser, 
  getUser, 
  clearAuth, 
  isAuthenticated as checkAuth,
  User,
  AuthToken 
} from '../services/auth';
import { authApi } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    organization_name?: string;
  }) => Promise<{ success: boolean; error?: string }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is authenticated on mount
    const initAuth = async () => {
      if (checkAuth()) {
        const storedUser = getUser();
        if (storedUser) {
          setUserState(storedUser);
        } else {
          // Try to fetch user info
          const response = await authApi.getMe();
          if (response.data) {
            setUser(response.data);
            setUserState(response.data);
          } else {
            clearAuth();
          }
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await authApi.login(email, password);
      
      if (response.data) {
        const token: AuthToken = response.data;
        setAuthToken(token);
        
        // Fetch user info
        const userResponse = await authApi.getMe();
        if (userResponse.data) {
          setUser(userResponse.data);
          setUserState(userResponse.data);
          navigate('/dashboard');
          return { success: true };
        }
      }
      
      return { 
        success: false, 
        error: response.error || 'Login failed' 
      };
    } catch (error) {
      return { 
        success: false, 
        error: 'An error occurred during login' 
      };
    }
  };

  const register = async (data: {
    email: string;
    password: string;
    full_name: string;
    organization_name?: string;
  }) => {
    try {
      const response = await authApi.register(data);
      
      if (response.data) {
        const token: AuthToken = response.data;
        setAuthToken(token);
        
        // Fetch user info
        const userResponse = await authApi.getMe();
        if (userResponse.data) {
          setUser(userResponse.data);
          setUserState(userResponse.data);
          navigate('/dashboard');
          return { success: true };
        }
      }
      
      return { 
        success: false, 
        error: response.error || 'Registration failed' 
      };
    } catch (error) {
      return { 
        success: false, 
        error: 'An error occurred during registration' 
      };
    }
  };

  const logout = () => {
    clearAuth();
    setUserState(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider 
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// For backward compatibility
export default useAuth;