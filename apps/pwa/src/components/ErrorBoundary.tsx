import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react'
import { Button } from './ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
  errorCount: number
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render shows the fallback UI
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo)
    }

    // Update state with error details
    this.setState(prevState => ({
      errorInfo,
      errorCount: prevState.errorCount + 1
    }))

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    // Send error to logging service in production
    if (process.env.NODE_ENV === 'production') {
      this.logErrorToService(error, errorInfo)
    }
  }

  logErrorToService = (error: Error, errorInfo: ErrorInfo) => {
    // Here you would send the error to your logging service
    // For example: Sentry, LogRocket, or your custom error tracking
    const errorData = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    }

    // Example: Send to your API endpoint
    fetch('/api/v1/errors', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(errorData)
    }).catch(err => {
      console.error('Failed to log error:', err)
    })
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    })
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      // If custom fallback is provided, use it
      if (this.props.fallback) {
        return <>{this.props.fallback}</>
      }

      // Default error UI
      return (
        <div className="min-h-screen bg-black flex items-center justify-center p-4">
          <Card className="bg-glass border-white/10 max-w-2xl w-full">
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <div className="p-3 bg-red-500/20 rounded-full">
                  <AlertTriangle className="w-8 h-8 text-red-500" />
                </div>
              </div>
              <CardTitle className="text-2xl text-white">
                Oops! Algo salió mal
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <p className="text-gray-400 text-center">
                Ha ocurrido un error inesperado. Hemos sido notificados y estamos trabajando para solucionarlo.
              </p>

              {/* Error details in development mode */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <div className="bg-black/50 rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 text-red-400 mb-2">
                    <Bug className="w-4 h-4" />
                    <span className="font-semibold">Error Details (Dev Only)</span>
                  </div>
                  <div className="text-xs text-gray-500 font-mono">
                    <p className="text-red-400 mb-2">{this.state.error.message}</p>
                    <details className="cursor-pointer">
                      <summary className="text-gray-400 hover:text-white transition-colors">
                        Stack Trace
                      </summary>
                      <pre className="mt-2 text-gray-600 overflow-x-auto whitespace-pre-wrap">
                        {this.state.error.stack}
                      </pre>
                    </details>
                    {this.state.errorInfo && (
                      <details className="cursor-pointer mt-2">
                        <summary className="text-gray-400 hover:text-white transition-colors">
                          Component Stack
                        </summary>
                        <pre className="mt-2 text-gray-600 overflow-x-auto whitespace-pre-wrap">
                          {this.state.errorInfo.componentStack}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button
                  onClick={this.handleReset}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Intentar de Nuevo
                </Button>
                <Button
                  onClick={this.handleReload}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Recargar Página
                </Button>
                <Button
                  onClick={this.handleGoHome}
                  className="flex items-center gap-2"
                >
                  <Home className="w-4 h-4" />
                  Ir al Inicio
                </Button>
              </div>

              {/* Error count warning */}
              {this.state.errorCount > 2 && (
                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
                  <p className="text-sm text-yellow-500 text-center">
                    Este error ha ocurrido {this.state.errorCount} veces. 
                    Si el problema persiste, por favor contacta al soporte.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

// Hook for functional components to catch errors
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null)

  React.useEffect(() => {
    if (error) {
      throw error
    }
  }, [error])

  const resetError = () => setError(null)
  const captureError = (error: Error) => setError(error)

  return { resetError, captureError }
}

// Async Error Boundary for handling async errors
export class AsyncErrorBoundary extends ErrorBoundary {
  componentDidMount() {
    // Listen for unhandled promise rejections
    window.addEventListener('unhandledrejection', this.handleUnhandledRejection)
  }

  componentWillUnmount() {
    window.removeEventListener('unhandledrejection', this.handleUnhandledRejection)
  }

  handleUnhandledRejection = (event: PromiseRejectionEvent) => {
    console.error('Unhandled promise rejection:', event.reason)
    
    // Convert rejection reason to Error if it's not already
    const error = event.reason instanceof Error 
      ? event.reason 
      : new Error(String(event.reason))
    
    // Trigger error boundary
    this.setState({
      hasError: true,
      error,
      errorInfo: {
        componentStack: 'Unhandled Promise Rejection'
      } as ErrorInfo
    })

    // Prevent default browser error handling
    event.preventDefault()
  }
}

// Specialized error boundary for specific components
export class RouteErrorBoundary extends ErrorBoundary {
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
          <div className="text-center space-y-4">
            <div className="flex justify-center">
              <div className="p-3 bg-red-500/20 rounded-full">
                <AlertTriangle className="w-6 h-6 text-red-500" />
              </div>
            </div>
            <h2 className="text-xl font-semibold text-white">
              Error al cargar esta página
            </h2>
            <p className="text-gray-400 max-w-md">
              No pudimos cargar esta sección. Por favor, intenta recargar la página.
            </p>
            <div className="flex gap-3 justify-center">
              <Button onClick={this.handleReset} variant="outline" size="sm">
                Reintentar
              </Button>
              <Button onClick={this.handleGoHome} size="sm">
                Ir al Dashboard
              </Button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

// Widget Error Boundary for smaller components
export class WidgetErrorBoundary extends ErrorBoundary {
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-center gap-2 text-red-500">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm">Error al cargar este componente</span>
          </div>
          <button
            onClick={this.handleReset}
            className="text-xs text-red-400 hover:text-red-300 mt-2 underline"
          >
            Reintentar
          </button>
        </div>
      )
    }

    return this.props.children
  }
}