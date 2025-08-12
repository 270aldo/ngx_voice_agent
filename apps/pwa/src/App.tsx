import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AuthGuard } from './components/AuthGuard'
import { WebSocketProvider } from './contexts/WebSocketContext'
import { Dashboard } from './pages/Dashboard'
import { Conversations } from './pages/Conversations'
import { Analytics } from './pages/Analytics'
import { Agents } from './pages/Agents'
import { Settings } from './pages/Settings'
import { Login } from './pages/Login'
import { useAuth } from './hooks/useAuth'
import { Toaster } from './components/ui/toaster'
import { ErrorBoundary, RouteErrorBoundary } from './components/ErrorBoundary'

function App() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="loading-dots-ngx">
          <div></div>
          <div></div>
          <div></div>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-black text-white">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <AuthGuard>
              <WebSocketProvider autoConnect={true}>
                <Layout />
              </WebSocketProvider>
            </AuthGuard>
          }>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={
              <RouteErrorBoundary>
                <Dashboard />
              </RouteErrorBoundary>
            } />
            <Route path="conversations" element={
              <RouteErrorBoundary>
                <Conversations />
              </RouteErrorBoundary>
            } />
            <Route path="analytics" element={
              <RouteErrorBoundary>
                <Analytics />
              </RouteErrorBoundary>
            } />
            <Route path="agents" element={
              <RouteErrorBoundary>
                <Agents />
              </RouteErrorBoundary>
            } />
            <Route path="settings" element={
              <RouteErrorBoundary>
                <Settings />
              </RouteErrorBoundary>
            } />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        <Toaster />
      </div>
    </ErrorBoundary>
  )
}

export default App