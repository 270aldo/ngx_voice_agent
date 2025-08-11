/**
 * Authentication Service
 * 
 * Handles authentication tokens and user session management.
 * Updated to work with httpOnly cookies for enhanced security.
 */

const USER_KEY = 'ngx_user';
const AUTH_STATE_KEY = 'ngx_auth_state';

export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  organization_id: string;
  role: string;
  is_active: boolean;
}

/**
 * Store authentication state (tokens are now in httpOnly cookies)
 */
export function setAuthToken(token: AuthToken): void {
  // Store minimal auth state info (tokens are in httpOnly cookies)
  const authState = {
    authenticated: true,
    expiresAt: Date.now() + (token.expires_in * 1000),
    tokenType: token.token_type
  };
  localStorage.setItem(AUTH_STATE_KEY, JSON.stringify(authState));
}

/**
 * Get authentication token (now from httpOnly cookies, this returns null as token is not accessible)
 */
export function getAuthToken(): string | null {
  // With httpOnly cookies, we can't access the token directly
  // The browser will automatically include it in requests
  return null;
}

/**
 * Get authentication state
 */
export function getAuthState(): { authenticated: boolean; expiresAt: number; tokenType: string } | null {
  const authStateData = localStorage.getItem(AUTH_STATE_KEY);
  if (!authStateData) return null;
  
  try {
    const authState = JSON.parse(authStateData);
    
    // Check if auth state is expired
    if (Date.now() > authState.expiresAt) {
      clearAuth();
      return null;
    }
    
    return authState;
  } catch {
    return null;
  }
}

/**
 * Store user information
 */
export function setUser(user: User): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * Get user information
 */
export function getUser(): User | null {
  const userData = localStorage.getItem(USER_KEY);
  if (!userData) return null;
  
  try {
    return JSON.parse(userData);
  } catch {
    return null;
  }
}

/**
 * Clear authentication data
 */
export function clearAuth(): void {
  localStorage.removeItem(AUTH_STATE_KEY);
  localStorage.removeItem(USER_KEY);
  // Clear httpOnly cookies by calling logout endpoint
  fetch('/api/v1/auth/logout', {
    method: 'POST',
    credentials: 'include'
  }).catch(() => {
    // Ignore errors during logout
  });
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  const authState = getAuthState();
  return authState?.authenticated === true;
}

/**
 * Get authorization header (empty with httpOnly cookies as auth is automatic)
 */
export function getAuthHeader(): Record<string, string> {
  // With httpOnly cookies, authentication is handled automatically
  // No need to manually add Authorization header
  return {};
}