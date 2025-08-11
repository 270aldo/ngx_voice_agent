import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  TrendingUp, 
  Users, 
  MessageSquare, 
  DollarSign,
  Activity,
  Target,
  Clock,
  Zap,
  Wifi,
  WifiOff
} from 'lucide-react'
import { MetricCard } from '../components/dashboard/MetricCard'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { useWebSocket } from '../contexts/WebSocketContext'
import { useToast } from '../hooks/use-toast'
import { dashboardApi } from '../services/api'

// Mock data - will be replaced with real API calls
const mockMetrics = {
  conversions: { value: '47%', change: 12 },
  activeLeads: { value: '23', change: 8 },
  revenue: { value: '$12,450', change: 15 },
  responseTime: { value: '0.3s', change: -25 },
  conversations: { value: '156', change: 5 },
  satisfaction: { value: '9.2/10', change: 3 },
}

export function Dashboard() {
  const [metrics, setMetrics] = useState(mockMetrics)
  const [loading, setLoading] = useState(true)
  const [liveConversations, setLiveConversations] = useState<any[]>([])
  const [recentActivity, setRecentActivity] = useState<any[]>([])
  const [funnelData, setFunnelData] = useState<any[]>([])
  const { isConnected: wsConnected, lastMetricUpdate, lastConversationUpdate } = useWebSocket()
  const { toast } = useToast()

  useEffect(() => {
    // Fetch initial metrics
    const fetchMetrics = async () => {
      try {
        const response = await dashboardApi.getMetrics('today')
        if (response.data) {
          const data = response.data
          
          setMetrics({
            conversions: {
              value: `${data.conversions?.rate || '0'}%`,
              change: data.conversions?.change || 0
            },
            activeLeads: {
              value: data.active_leads?.count?.toString() || '0',
              change: data.active_leads?.change || 0
            },
            revenue: {
              value: `$${(data.revenue?.total || 0).toLocaleString()}`,
              change: data.revenue?.change || 0
            },
            responseTime: {
              value: `${(data.response_time?.average || 0).toFixed(1)}s`,
              change: data.response_time?.change || 0
            },
            conversations: {
              value: data.conversations_count?.total?.toString() || '0',
              change: data.conversations_count?.change || 0
            },
            satisfaction: {
              value: `${(data.satisfaction_score?.average || 0).toFixed(1)}/10`,
              change: data.satisfaction_score?.change || 0
            }
          })
        }
      } catch (error) {
        console.error('Error fetching metrics:', error)
        // Fall back to mock data on error
        setMetrics(mockMetrics)
        toast({
          title: "Aviso",
          description: "Usando datos de ejemplo - API no disponible",
          variant: "default",
        })
      } finally {
        setLoading(false)
      }
    }

    fetchMetrics()
    
    // Fetch live conversations
    const fetchLiveConversations = async () => {
      try {
        const response = await dashboardApi.getLiveConversations(10)
        if (response.data) {
          setLiveConversations(response.data)
        }
      } catch (error) {
        console.error('Error fetching live conversations:', error)
      }
    }
    
    // Fetch recent activity
    const fetchRecentActivity = async () => {
      try {
        const response = await dashboardApi.getActivityFeed(5)
        if (response.data) {
          setRecentActivity(response.data)
        }
      } catch (error) {
        console.error('Error fetching recent activity:', error)
      }
    }
    
    // Fetch funnel data
    const fetchFunnelData = async () => {
      try {
        const response = await dashboardApi.getFunnel('today')
        if (response.data && response.data.stages) {
          setFunnelData(response.data.stages)
        }
      } catch (error) {
        console.error('Error fetching funnel data:', error)
      }
    }
    
    // Fetch all data
    fetchLiveConversations()
    fetchRecentActivity()
    fetchFunnelData()
  }, [])

  // Handle WebSocket metric updates
  useEffect(() => {
    if (lastMetricUpdate) {
      const update = lastMetricUpdate
      
      // Update metrics based on the update type
      if (update.metric_type === 'conversion' && update.data.conversion_rate) {
        setMetrics(prev => ({
          ...prev,
          conversions: {
            value: `${Math.round(update.data.conversion_rate * 100)}%`,
            change: update.data.conversion_change || prev.conversions.change
          }
        }))
      }
      
      if (update.metric_type === 'performance' && update.data.response_time) {
        setMetrics(prev => ({
          ...prev,
          responseTime: {
            value: `${update.data.response_time.toFixed(1)}s`,
            change: update.data.response_change || prev.responseTime.change
          }
        }))
      }
      
      if (update.metric_type === 'activity') {
        setMetrics(prev => ({
          ...prev,
          activeLeads: {
            value: update.data.active_conversations?.toString() || prev.activeLeads.value,
            change: prev.activeLeads.change
          },
          conversations: {
            value: update.data.total_conversations?.toString() || prev.conversations.value,
            change: prev.conversations.change
          }
        }))
      }
    }
  }, [lastMetricUpdate])

  // Handle WebSocket conversation updates
  useEffect(() => {
    if (lastConversationUpdate) {
      const update = lastConversationUpdate
      
      // Refresh live conversations when there are updates
      if (update.event_type === 'started' || update.event_type === 'ended') {
        // Refetch live conversations and activity
        const fetchLiveConversations = async () => {
          try {
            const response = await dashboardApi.getLiveConversations(10)
            if (response.data) {
              setLiveConversations(response.data)
            }
          } catch (error) {
            console.error('Error fetching live conversations:', error)
          }
        }
        
        const fetchRecentActivity = async () => {
          try {
            const response = await dashboardApi.getActivityFeed(5)
            if (response.data) {
              setRecentActivity(response.data)
            }
          } catch (error) {
            console.error('Error fetching recent activity:', error)
          }
        }
        
        fetchLiveConversations()
        fetchRecentActivity()
      }
    }
  }, [lastConversationUpdate])

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-heading text-white">Dashboard</h1>
          <p className="text-gray-400 mt-1">
            Monitorea el rendimiento de tu agente NGX en tiempo real
          </p>
        </div>
        <div className="flex items-center gap-2">
          {wsConnected ? (
            <div className="flex items-center gap-2 text-green-500">
              <Wifi className="w-4 h-4" />
              <span className="text-sm">En vivo</span>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            </div>
          ) : (
            <div className="flex items-center gap-2 text-gray-500">
              <WifiOff className="w-4 h-4" />
              <span className="text-sm">Reconectando...</span>
            </div>
          )}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        <MetricCard
          title="Conversiones Hoy"
          value={metrics.conversions.value}
          change={metrics.conversions.change}
          icon={TrendingUp}
          iconColor="text-green-500"
          loading={loading}
        />
        <MetricCard
          title="Leads Activos"
          value={metrics.activeLeads.value}
          change={metrics.activeLeads.change}
          icon={Users}
          iconColor="text-electric-violet"
          loading={loading}
        />
        <MetricCard
          title="Ingresos"
          value={metrics.revenue.value}
          change={metrics.revenue.change}
          icon={DollarSign}
          iconColor="text-yellow-500"
          loading={loading}
        />
        <MetricCard
          title="Tiempo de Respuesta"
          value={metrics.responseTime.value}
          change={metrics.responseTime.change}
          icon={Zap}
          iconColor="text-blue-500"
          loading={loading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* Conversion Funnel */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Funnel de Conversión</span>
              <Target className="w-5 h-5 text-electric-violet" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {(funnelData.length > 0 ? funnelData : [
                { name: 'Visitantes', count: 1250, conversion_rate: 100 },
                { name: 'Engaged', count: 875, conversion_rate: 70 },
                { name: 'Qualified', count: 450, conversion_rate: 36 },
                { name: 'Converted', count: 156, conversion_rate: 12.5 },
              ]).map((stage, index) => (
                <motion.div
                  key={stage.stage}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-400">{stage.name}</span>
                    <span className="text-sm font-medium">{stage.count}</span>
                  </div>
                  <div className="w-full bg-black/30 rounded-full h-2">
                    <motion.div
                      className="bg-gradient-to-r from-electric-violet to-deep-purple h-2 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${stage.conversion_rate}%` }}
                      transition={{ duration: 1, delay: index * 0.1 }}
                    />
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Actividad Reciente</span>
              <Activity className="w-5 h-5 text-electric-violet" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(recentActivity.length > 0 ? recentActivity.map(activity => ({
                time: new Date(activity.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
                event: activity.description,
                type: activity.event_type,
                customer: activity.customer_name
              })) : [
                { time: '2 min', event: 'Nueva conversación iniciada', type: 'conversation' },
                { time: '5 min', event: 'Lead calificado - Juan P.', type: 'qualified' },
                { time: '12 min', event: 'Conversión completada - María G.', type: 'conversion' },
                { time: '18 min', event: 'Cita agendada - Carlos R.', type: 'appointment' },
                { time: '25 min', event: 'Objeción resuelta - Ana L.', type: 'objection' },
              ]).map((activity, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-start space-x-3 p-2 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <div className="flex-shrink-0 mt-0.5">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      activity.type === 'conversion' ? 'bg-green-500' :
                      activity.type === 'qualified' ? 'bg-electric-violet' :
                      activity.type === 'appointment' ? 'bg-blue-500' :
                      'bg-gray-400'
                    )} />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm">{activity.event}</p>
                    <p className="text-xs text-gray-500 flex items-center mt-0.5">
                      <Clock className="w-3 h-3 mr-1" />
                      {activity.time}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Live Conversations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Conversaciones en Vivo</span>
            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-sm text-gray-400">{liveConversations.length} activas</span>
              </div>
              <Button size="sm" variant="outline">
                Ver todas
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {liveConversations.length === 0 && !loading && (
            <div className="text-center py-8 text-gray-400">
              <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No hay conversaciones activas en este momento</p>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 md:gap-4">
            {(liveConversations.length > 0 ? liveConversations.map(conv => ({
              name: conv.customer_name,
              status: conv.last_message || `En etapa: ${conv.stage}`,
              duration: `${Math.floor(conv.duration_seconds / 60)}:${(conv.duration_seconds % 60).toString().padStart(2, '0')}`,
              emotion: conv.emotional_state
            })) : [
              { name: 'Carlos M.', status: 'Preguntando sobre precios', duration: '3:45', emotion: 'interested' },
              { name: 'Ana S.', status: 'Evaluando características', duration: '5:12', emotion: 'curious' },
              { name: 'Luis R.', status: 'Listo para agendar', duration: '8:23', emotion: 'excited' },
            ]).map((conversation, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 }}
                className="p-4 rounded-lg bg-black/30 border border-deep-purple/20 hover:border-electric-violet/30 transition-all cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2">
                  <h4 className="font-medium">{conversation.name}</h4>
                  <span className="text-xs text-gray-400">{conversation.duration}</span>
                </div>
                <p className="text-sm text-gray-400 mb-2">{conversation.status}</p>
                <div className="flex items-center space-x-2">
                  <MessageSquare className="w-4 h-4 text-electric-violet" />
                  <span className={cn(
                    "text-xs capitalize",
                    conversation.emotion === 'excited' ? 'text-green-500' :
                    conversation.emotion === 'interested' ? 'text-electric-violet' :
                    'text-gray-400'
                  )}>
                    {conversation.emotion}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Helper function
function cn(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}