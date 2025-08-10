/**
 * WebSocket Context Provider
 * 
 * Provides WebSocket functionality and state to the entire app
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import webSocketService, { MetricUpdate, ConversationUpdate } from '../services/websocket'
import { useToast } from '../hooks/use-toast'

interface WebSocketContextType {
  isConnected: boolean
  lastMetricUpdate: MetricUpdate | null
  lastConversationUpdate: ConversationUpdate | null
  connectionAttempts: number
  connect: () => void
  disconnect: () => void
  subscribe: (topic: string) => void
  unsubscribe: (topic: string) => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

interface WebSocketProviderProps {
  children: ReactNode
  autoConnect?: boolean
}

export function WebSocketProvider({ children, autoConnect = true }: WebSocketProviderProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMetricUpdate, setLastMetricUpdate] = useState<MetricUpdate | null>(null)
  const [lastConversationUpdate, setLastConversationUpdate] = useState<ConversationUpdate | null>(null)
  const [connectionAttempts, setConnectionAttempts] = useState(0)
  const { toast } = useToast()

  useEffect(() => {
    // Set up WebSocket event listeners
    const handleConnected = () => {
      setIsConnected(true)
      setConnectionAttempts(0)
      console.log('WebSocket connected successfully')
    }

    const handleDisconnected = () => {
      setIsConnected(false)
      console.log('WebSocket disconnected')
    }

    const handleError = (error: Error) => {
      console.error('WebSocket error:', error)
      setConnectionAttempts(prev => prev + 1)
    }

    const handleMetricUpdate = (update: MetricUpdate) => {
      setLastMetricUpdate(update)
      console.log('Received metric update:', update)
    }

    const handleConversationUpdate = (update: ConversationUpdate) => {
      setLastConversationUpdate(update)
      console.log('Received conversation update:', update)
      
      // Show toast notifications for important conversation events
      if (update.event_type === 'started') {
        toast({
          title: "Nueva conversación",
          description: `${update.data.customer?.name || 'Cliente'} ha iniciado una conversación`,
        })
      } else if (update.event_type === 'ended') {
        const outcome = update.data.outcome || 'finalizada'
        toast({
          title: "Conversación finalizada",
          description: `Conversación ${outcome}`,
          variant: outcome === 'converted' ? 'default' : 'destructive'
        })
      }
    }

    const handleLeadQualified = (data: any) => {
      toast({
        title: "Lead calificado",
        description: `${data.customer_name} ha sido calificado como lead de alta calidad`,
      })
    }

    const handlePatternDetected = (data: any) => {
      if (data.pattern_type === 'objection') {
        toast({
          title: "Patrón detectado",
          description: `Objeción detectada: ${data.pattern_name}`,
          variant: "default"
        })
      }
    }

    // Subscribe to events
    webSocketService.on('connected', handleConnected)
    webSocketService.on('disconnected', handleDisconnected)
    webSocketService.on('error', handleError)
    webSocketService.on('metric_update', handleMetricUpdate)
    webSocketService.on('conversation_update', handleConversationUpdate)
    webSocketService.on('lead_qualified', handleLeadQualified)
    webSocketService.on('pattern_detected', handlePatternDetected)

    // Auto-connect if enabled
    if (autoConnect) {
      webSocketService.connect()
    }

    // Cleanup on unmount
    return () => {
      webSocketService.off('connected', handleConnected)
      webSocketService.off('disconnected', handleDisconnected)
      webSocketService.off('error', handleError)
      webSocketService.off('metric_update', handleMetricUpdate)
      webSocketService.off('conversation_update', handleConversationUpdate)
      webSocketService.off('lead_qualified', handleLeadQualified)
      webSocketService.off('pattern_detected', handlePatternDetected)
      
      if (autoConnect) {
        webSocketService.disconnect()
      }
    }
  }, [autoConnect, toast])

  const connect = () => {
    webSocketService.connect()
  }

  const disconnect = () => {
    webSocketService.disconnect()
  }

  const subscribe = (topic: string) => {
    webSocketService.subscribe(topic)
  }

  const unsubscribe = (topic: string) => {
    webSocketService.unsubscribe(topic)
  }

  const value: WebSocketContextType = {
    isConnected,
    lastMetricUpdate,
    lastConversationUpdate,
    connectionAttempts,
    connect,
    disconnect,
    subscribe,
    unsubscribe
  }

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket(): WebSocketContextType {
  const context = useContext(WebSocketContext)
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

export default WebSocketContext