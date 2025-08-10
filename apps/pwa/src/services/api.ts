/**
 * API Service for NGX Command Center
 * 
 * Handles all API calls to the backend with authentication
 */

import { getAuthHeader, clearAuth } from './auth';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

// CSRF Token management
let csrfToken: string | null = null;

/**
 * Get CSRF token from backend
 */
export async function getCSRFToken(): Promise<string | null> {
  if (csrfToken) return csrfToken;
  
  try {
    const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/auth/csrf-token`, {
      credentials: 'include'
    });
    
    if (response.ok) {
      const data = await response.json();
      csrfToken = data.csrf_token;
      return csrfToken;
    }
  } catch (error) {
    console.warn('Failed to get CSRF token:', error);
  }
  
  return null;
}

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Make an authenticated API request with CSRF protection
   */
  private async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    
    // Prepare headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
      ...options.headers,
    };
    
    // Add CSRF token for state-changing operations
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method?.toUpperCase() || 'GET')) {
      const token = await getCSRFToken();
      if (token) {
        headers['X-CSRF-Token'] = token;
      }
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include', // Important for httpOnly cookies
      });

      // Handle 401 unauthorized
      if (response.status === 401) {
        clearAuth();
        csrfToken = null; // Clear CSRF token
        window.location.href = '/login';
        return {
          error: 'Unauthorized',
          status: 401,
        };
      }
      
      // Handle 403 CSRF token invalid
      if (response.status === 403) {
        const errorData = await response.json().catch(() => ({}));
        if (errorData.detail?.includes('CSRF')) {
          csrfToken = null; // Clear invalid token
          // Retry once with new token
          return this.request(endpoint, options);
        }
      }

      const data = await response.json();

      if (!response.ok) {
        return {
          error: data.detail || 'Request failed',
          status: response.status,
        };
      }

      return {
        data,
        status: response.status,
      };
    } catch (error) {
      console.error('API request error:', error);
      return {
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      };
    }
  }

  /**
   * GET request
   */
  async get<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * POST request
   */
  async post<T = any>(endpoint: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  /**
   * PUT request
   */
  async put<T = any>(endpoint: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  /**
   * DELETE request
   */
  async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    });
  }

  /**
   * PATCH request
   */
  async patch<T = any>(endpoint: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  }
}

// Create singleton instance
const apiService = new ApiService();

// Export service and specific API functions
export default apiService;

// Dashboard API
export const dashboardApi = {
  getMetrics: (timeframe = 'today') => apiService.get(`/dashboard/metrics?timeframe=${timeframe}`),
  getFunnel: (timeframe = 'today') => apiService.get(`/dashboard/funnel?timeframe=${timeframe}`),
  getLiveConversations: (limit = 10) => apiService.get(`/dashboard/conversations/live?limit=${limit}`),
  getActivityFeed: (limit = 20) => apiService.get(`/dashboard/activity/recent?limit=${limit}`),
  getAnalyticsSummary: (timeframe = 'week') => apiService.get(`/dashboard/analytics/summary?timeframe=${timeframe}`),
  queryAnalytics: (query: string) => apiService.post('/dashboard/query', { query }),
};

// Auth API
export const authApi = {
  login: (email: string, password: string) => 
    apiService.post('/auth/login', { email, password }),
  register: (data: { email: string; password: string; full_name: string; organization_name?: string }) => 
    apiService.post('/auth/register', data),
  getMe: () => apiService.get('/auth/me'),
  refresh: () => apiService.post('/auth/refresh'),
  getOrganization: () => apiService.get('/auth/organization'),
};

// Conversations API
export const conversationsApi = {
  list: (params?: { status?: string; limit?: number; offset?: number }) => 
    apiService.get(`/conversations${params ? '?' + new URLSearchParams(params as any).toString() : ''}`),
  get: (id: string) => apiService.get(`/conversations/${id}`),
  getMessages: (id: string, params?: { limit?: number; offset?: number }) => 
    apiService.get(`/conversations/${id}/messages${params ? '?' + new URLSearchParams(params as any).toString() : ''}`),
  sendMessage: (id: string, message: string) => 
    apiService.post(`/conversations/${id}/messages`, { message }),
  endConversation: (id: string, outcome: string, summary?: any) => 
    apiService.post(`/conversations/${id}/end`, { outcome, summary }),
};

// Analytics API (using dashboard endpoints since analytics endpoints are not implemented yet)
export const analyticsApi = {
  getOverview: (period: string = '7d') => 
    dashboardApi.getAnalyticsSummary(period),
  getConversionTrends: (period: string = '30d') => 
    dashboardApi.getFunnel(period === '30d' ? 'month' : period === '7d' ? 'week' : 'today'),
  getAgentPerformance: () => 
    dashboardApi.getMetrics('week'),
  getLeadSources: () => 
    dashboardApi.getActivityFeed(100),
  // Additional analytics methods
  getMetrics: (timeframe: string = 'week') => 
    dashboardApi.getMetrics(timeframe),
  getFunnelData: (timeframe: string = 'today') => 
    dashboardApi.getFunnel(timeframe),
  getChannelPerformance: () => 
    dashboardApi.getAnalyticsSummary('week'),
  getHourlyActivity: () => 
    dashboardApi.getAnalyticsSummary('today'),
  exportData: (period: string, format: string = 'json') => 
    apiService.get(`/dashboard/analytics/export?period=${period}&format=${format}`)
};

// Agent Configuration API (to be implemented)
export const agentApi = {
  getConfig: () => apiService.get('/agents/config'),
  updateConfig: (config: any) => apiService.put('/agents/config', config),
  getPersonalities: () => apiService.get('/agents/personalities'),
  updatePersonality: (id: string, data: any) => 
    apiService.put(`/agents/personalities/${id}`, data),
};

// WebSocket URL export
export { WS_BASE_URL };

// Health check
export const healthApi = {
  check: () => fetch(`${API_BASE_URL.replace('/api/v1', '')}/health`, { credentials: 'include' })
    .then(res => res.json())
    .catch(() => ({ status: 'error' }))
};

// Utility functions
export const formatApiError = (error: any): string => {
  if (error?.data?.detail) return error.data.detail;
  if (error?.error) return error.error;
  return 'An unexpected error occurred';
};

export const isApiError = (response: ApiResponse): boolean => {
  return response.status >= 400 || !!response.error;
};

// Export types
export type { ApiResponse };

// CSRF token utility export
export { getCSRFToken };