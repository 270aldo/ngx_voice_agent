import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authApi } from '../services/api'
import Cookies from 'js-cookie'

interface User {
  id: string
  email: string
  name: string
  role: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  csrfToken: string | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [csrfToken, setCsrfToken] = useState<string | null>(null)

  useEffect(() => {
    // Check for existing session
    const checkAuth = async () => {
      try {
        // Get CSRF token first
        const csrfResponse = await fetch('/api/v1/auth/csrf', {
          credentials: 'include'
        })
        if (csrfResponse.ok) {
          const { csrf_token } = await csrfResponse.json()
          setCsrfToken(csrf_token)
          
          // Token is now in httpOnly cookie, check session
          const response = await fetch('/api/v1/auth/me', {
            credentials: 'include',
            headers: {
              'X-CSRF-Token': csrf_token
            }
          })
          
          if (response.ok) {
            const userData = await response.json()
            setUser({
              id: userData.id,
              email: userData.email,
              name: userData.full_name,
              role: userData.role
            })
          }
        }
      } catch (error) {
        console.error('Auth check failed:', error)
      } finally {
        setIsLoading(false)
      }
    }
    
    checkAuth()
  }, [])

  const login = async (email: string, password: string) => {
    try {
      // Get CSRF token first
      const csrfResponse = await fetch('/api/v1/auth/csrf', {
        credentials: 'include'
      })
      const { csrf_token } = await csrfResponse.json()
      setCsrfToken(csrf_token)
      
      // Login with CSRF protection
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf_token
        },
        credentials: 'include',
        body: JSON.stringify({ email, password })
      })
      
      if (!response.ok) {
        throw new Error('Login failed')
      }
      
      const data = await response.json()
      // Token is now stored in httpOnly cookie by the server
      setUser({
        id: data.user.id,
        email: data.user.email,
        name: data.user.full_name,
        role: data.user.role
      })
    } catch (error) {
      throw error
    }
  }

  const logout = async () => {
    try {
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRF-Token': csrfToken || ''
        }
      })
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      setUser(null)
      setCsrfToken(null)
    }
  }

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      logout,
      csrfToken
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}