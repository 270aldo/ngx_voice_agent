import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  TrendingDown,
  Users,
  Target,
  Calendar,
  Download,
  Filter,
  BarChart3,
  LineChart,
  PieChart,
  Activity,
  Clock,
  DollarSign,
  Percent,
  MessageSquare,
  Phone,
  Mail,
  Globe,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react'
import {
  LineChart as RechartsLineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Treemap,
  ComposedChart
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { analyticsApi } from '../services/api'
import { useToast } from '../hooks/use-toast'

// NGX color palette for charts
const CHART_COLORS = {
  primary: '#8B5CF6', // Electric Violet
  secondary: '#5B21B6', // Deep Purple
  success: '#10B981',
  warning: '#F59E0B',
  danger: '#EF4444',
  info: '#3B82F6',
  gradient: ['#8B5CF6', '#5B21B6'],
  pieColors: ['#8B5CF6', '#5B21B6', '#10B981', '#F59E0B', '#3B82F6', '#EF4444']
}

// Mock data for development
const conversionTrendData = [
  { date: '01 Nov', conversions: 42, leads: 89, rate: 47.2 },
  { date: '08 Nov', conversions: 48, leads: 92, rate: 52.2 },
  { date: '15 Nov', conversions: 51, leads: 98, rate: 52.0 },
  { date: '22 Nov', conversions: 45, leads: 85, rate: 52.9 },
  { date: '29 Nov', conversions: 58, leads: 105, rate: 55.2 },
  { date: '06 Dic', conversions: 62, leads: 110, rate: 56.4 },
  { date: '13 Dic', conversions: 68, leads: 115, rate: 59.1 },
]

const leadSourcesData = [
  { name: 'Landing Page', value: 35, color: CHART_COLORS.primary },
  { name: 'Lead Magnet', value: 28, color: CHART_COLORS.secondary },
  { name: 'Blog', value: 18, color: CHART_COLORS.success },
  { name: 'Social Media', value: 12, color: CHART_COLORS.warning },
  { name: 'Referidos', value: 7, color: CHART_COLORS.info },
]

const channelPerformanceData = [
  { channel: 'Voz', conversions: 68, satisfaction: 9.2, responseTime: 0.2 },
  { channel: 'Chat', conversions: 45, satisfaction: 8.8, responseTime: 0.5 },
  { channel: 'Email', conversions: 32, satisfaction: 8.5, responseTime: 120 },
]

const hourlyActivityData = Array.from({ length: 24 }, (_, i) => ({
  hour: `${i.toString().padStart(2, '0')}:00`,
  conversations: Math.floor(Math.random() * 20) + 5,
  conversions: Math.floor(Math.random() * 10) + 2,
}))

const agentPerformanceData = [
  { metric: 'Conversiones', score: 92, fullMark: 100 },
  { metric: 'Satisfacción', score: 88, fullMark: 100 },
  { metric: 'Velocidad', score: 95, fullMark: 100 },
  { metric: 'Empatía', score: 90, fullMark: 100 },
  { metric: 'Conocimiento', score: 94, fullMark: 100 },
  { metric: 'Cierre', score: 87, fullMark: 100 },
]

const conversionFunnelData = [
  { stage: 'Visitantes', value: 1000, percentage: 100 },
  { stage: 'Leads', value: 450, percentage: 45 },
  { stage: 'Calificados', value: 280, percentage: 28 },
  { stage: 'Oportunidades', value: 120, percentage: 12 },
  { stage: 'Clientes', value: 47, percentage: 4.7 },
]

interface MetricCardProps {
  title: string
  value: string | number
  change?: number
  icon: React.ElementType
  trend?: 'up' | 'down' | 'neutral'
}

function AnalyticsMetricCard({ title, value, change, icon: Icon, trend }: MetricCardProps) {
  const getTrendIcon = () => {
    if (!trend || trend === 'neutral') return null
    return trend === 'up' ? 
      <TrendingUp className="w-4 h-4" /> : 
      <TrendingDown className="w-4 h-4" />
  }

  const getTrendColor = () => {
    if (!trend || trend === 'neutral') return 'text-gray-400'
    return trend === 'up' ? 'text-green-500' : 'text-red-500'
  }

  return (
    <Card className="bg-glass border-white/10">
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="p-2 bg-electric-violet/20 rounded-lg">
            <Icon className="w-5 h-5 text-electric-violet" />
          </div>
          {change !== undefined && (
            <div className={`flex items-center gap-1 text-sm ${getTrendColor()}`}>
              {getTrendIcon()}
              <span>{Math.abs(change)}%</span>
            </div>
          )}
        </div>
        <div>
          <p className="text-sm text-gray-400 mb-1">{title}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}

// Custom Tooltip
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-glass backdrop-blur-md p-3 rounded-lg border border-white/10">
        <p className="text-white font-medium mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export function Analytics() {
  const [period, setPeriod] = useState<'7d' | '30d' | '90d'>('30d')
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  const [analyticsData, setAnalyticsData] = useState<any>(null)
  const [metricsData, setMetricsData] = useState<any>(null)
  const [funnelData, setFunnelData] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  // Load analytics data
  useEffect(() => {
    loadAnalyticsData()
  }, [period])

  const loadAnalyticsData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Load all analytics data in parallel
      const [overviewRes, metricsRes, funnelRes] = await Promise.all([
        analyticsApi.getOverview(period),
        analyticsApi.getMetrics(period === '7d' ? 'week' : period === '30d' ? 'month' : 'today'),
        analyticsApi.getFunnelData(period === '7d' ? 'week' : period === '30d' ? 'month' : 'today')
      ])
      
      if (overviewRes.data) {
        setAnalyticsData(overviewRes.data)
      }
      
      if (metricsRes.data) {
        setMetricsData(metricsRes.data)
      }
      
      if (funnelRes.data && funnelRes.data.stages) {
        setFunnelData(funnelRes.data.stages)
      }
      
    } catch (error) {
      console.error('Error loading analytics data:', error)
      setError('No se pudieron cargar los datos de analytics')
      toast({
        title: "Error",
        description: "Usando datos de ejemplo - API no disponible",
        variant: "default",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      const response = await analyticsApi.exportData(period, 'csv')
      if (response.data) {
        // Handle file download
        const blob = new Blob([response.data], { type: 'text/csv' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `analytics-${period}-${new Date().toISOString().split('T')[0]}.csv`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        
        toast({
          title: "Exportado exitosamente",
          description: "Tu reporte se ha descargado",
        })
      }
    } catch (error) {
      toast({
        title: "Error al exportar",
        description: "No se pudo generar el reporte",
        variant: "destructive"
      })
    }
  }

  if (loading) {
    return (
      <div className="space-y-4 md:space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl md:text-3xl font-heading text-white">Analytics</h1>
            <p className="text-gray-400 mt-1">Cargando datos...</p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          {[1, 2, 3, 4].map(i => (
            <Card key={i} className="bg-glass border-white/10">
              <CardContent className="p-6">
                <div className="animate-pulse">
                  <div className="w-8 h-8 bg-gray-600 rounded mb-4"></div>
                  <div className="w-full h-4 bg-gray-600 rounded mb-2"></div>
                  <div className="w-20 h-6 bg-gray-600 rounded"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="space-y-4 md:space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl md:text-3xl font-heading text-white">Analytics</h1>
            <p className="text-red-400 mt-1">{error}</p>
          </div>
        </div>
        <Card className="bg-glass border-white/10">
          <CardContent className="p-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-white mb-4">Error al cargar los datos de analytics</p>
            <Button onClick={loadAnalyticsData} variant="outline">
              Reintentar
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-heading text-white">Analytics</h1>
          <p className="text-gray-400 mt-1">
            Analiza el rendimiento y optimiza tu estrategia de ventas
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={period} onValueChange={(v) => setPeriod(v as any)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">7 días</SelectItem>
              <SelectItem value="30d">30 días</SelectItem>
              <SelectItem value="90d">90 días</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleExport}>
            <Download className="w-4 h-4 mr-2" />
            Exportar
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4 max-w-2xl">
          <TabsTrigger value="overview">Vista General</TabsTrigger>
          <TabsTrigger value="conversions">Conversiones</TabsTrigger>
          <TabsTrigger value="sources">Fuentes</TabsTrigger>
          <TabsTrigger value="performance">Rendimiento</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {/* Metrics Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
            <AnalyticsMetricCard
              title="Tasa de Conversión"
              value={metricsData?.conversions?.rate ? `${metricsData.conversions.rate}%` : "59.1%"}
              change={metricsData?.conversions?.change || 12}
              icon={Percent}
              trend={metricsData?.conversions?.change >= 0 ? "up" : "down"}
            />
            <AnalyticsMetricCard
              title="Leads Totales"
              value={metricsData?.active_leads?.count || "1,245"}
              change={metricsData?.active_leads?.change || 8}
              icon={Users}
              trend={metricsData?.active_leads?.change >= 0 ? "up" : "down"}
            />
            <AnalyticsMetricCard
              title="Ingresos"
              value={metricsData?.revenue?.total ? `$${metricsData.revenue.total.toLocaleString()}` : "$45,280"}
              change={metricsData?.revenue?.change || 15}
              icon={DollarSign}
              trend={metricsData?.revenue?.change >= 0 ? "up" : "down"}
            />
            <AnalyticsMetricCard
              title="Tiempo Respuesta"
              value={metricsData?.response_time?.average ? `${metricsData.response_time.average.toFixed(1)}s` : "0.3s"}
              change={metricsData?.response_time?.change || -25}
              icon={Clock}
              trend={metricsData?.response_time?.change <= 0 ? "up" : "down"}
            />
          </div>

          {/* Conversion Trend */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LineChart className="w-5 h-5 text-electric-violet" />
                Tendencia de Conversiones
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={conversionTrendData}>
                  <defs>
                    <linearGradient id="colorConversions" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.8}/>
                      <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="date" stroke="#666" />
                  <YAxis stroke="#666" />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="conversions"
                    stroke={CHART_COLORS.primary}
                    fillOpacity={1}
                    fill="url(#colorConversions)"
                    name="Conversiones"
                  />
                  <Line
                    type="monotone"
                    dataKey="rate"
                    stroke={CHART_COLORS.success}
                    strokeWidth={2}
                    dot={{ fill: CHART_COLORS.success }}
                    name="Tasa %"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Activity Heatmap and Agent Performance */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
            {/* Hourly Activity */}
            <Card className="bg-glass border-white/10">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-electric-violet" />
                  Actividad por Hora
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={hourlyActivityData.filter((_, i) => i % 2 === 0)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="hour" stroke="#666" />
                    <YAxis stroke="#666" />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="conversations" fill={CHART_COLORS.primary} name="Conversaciones" />
                    <Bar dataKey="conversions" fill={CHART_COLORS.success} name="Conversiones" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Agent Performance Radar */}
            <Card className="bg-glass border-white/10">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5 text-electric-violet" />
                  Rendimiento del Agente
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <RadarChart data={agentPerformanceData}>
                    <PolarGrid stroke="#333" />
                    <PolarAngleAxis dataKey="metric" stroke="#666" />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#666" />
                    <Radar
                      name="Puntuación"
                      dataKey="score"
                      stroke={CHART_COLORS.primary}
                      fill={CHART_COLORS.primary}
                      fillOpacity={0.6}
                    />
                    <Tooltip content={<CustomTooltip />} />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Conversions Tab */}
        <TabsContent value="conversions" className="space-y-6">
          {/* Conversion Funnel */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-electric-violet" />
                Embudo de Conversión
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {(funnelData.length > 0 ? funnelData : conversionFunnelData).map((stage, index) => (
                  <motion.div
                    key={stage.stage}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-white">{stage.name || stage.stage}</span>
                      <span className="text-sm text-gray-400">{stage.count || stage.value} ({(stage.conversion_rate || stage.percentage)}%)</span>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-8 overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-electric-violet to-deep-purple flex items-center justify-end pr-3"
                        initial={{ width: 0 }}
                        animate={{ width: `${stage.conversion_rate || stage.percentage}%` }}
                        transition={{ duration: 1, delay: index * 0.1 }}
                      >
                        <span className="text-xs text-white font-medium">
                          {stage.conversion_rate || stage.percentage}%
                        </span>
                      </motion.div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Channel Performance */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle>Rendimiento por Canal</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={channelPerformanceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="channel" stroke="#666" />
                  <YAxis yAxisId="left" stroke="#666" />
                  <YAxis yAxisId="right" orientation="right" stroke="#666" />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar yAxisId="left" dataKey="conversions" fill={CHART_COLORS.primary} name="Conversiones" />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="satisfaction"
                    stroke={CHART_COLORS.success}
                    strokeWidth={2}
                    name="Satisfacción"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sources Tab */}
        <TabsContent value="sources" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
            {/* Lead Sources Pie Chart */}
            <Card className="bg-glass border-white/10">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-electric-violet" />
                  Fuentes de Leads
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <RechartsPieChart>
                    <Pie
                      data={leadSourcesData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {leadSourcesData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </RechartsPieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Source Details */}
            <Card className="bg-glass border-white/10">
              <CardHeader>
                <CardTitle>Detalles por Fuente</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {leadSourcesData.map((source) => (
                    <div key={source.name} className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: source.color }}
                        />
                        <span className="text-white">{source.name}</span>
                      </div>
                      <div className="text-right">
                        <p className="text-white font-medium">{source.value}%</p>
                        <p className="text-xs text-gray-400">
                          {Math.round((source.value / 100) * 1245)} leads
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Source Conversion Rates */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle>Tasa de Conversión por Fuente</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={leadSourcesData.map(s => ({
                    ...s,
                    conversionRate: Math.floor(Math.random() * 30) + 40
                  }))}
                  layout="horizontal"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="name" stroke="#666" />
                  <YAxis stroke="#666" />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="conversionRate" name="Tasa de Conversión %">
                    {leadSourcesData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-6">
          {/* Performance Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 md:gap-4">
            <Card className="bg-glass border-white/10">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <CheckCircle className="w-8 h-8 text-green-500" />
                  <span className="text-2xl font-bold text-white">87%</span>
                </div>
                <p className="text-sm text-gray-400">Tasa de Éxito</p>
                <p className="text-xs text-green-500 mt-1">+5% vs mes anterior</p>
              </CardContent>
            </Card>

            <Card className="bg-glass border-white/10">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <Clock className="w-8 h-8 text-blue-500" />
                  <span className="text-2xl font-bold text-white">2.3 min</span>
                </div>
                <p className="text-sm text-gray-400">Tiempo Promedio</p>
                <p className="text-xs text-blue-500 mt-1">-15s vs mes anterior</p>
              </CardContent>
            </Card>

            <Card className="bg-glass border-white/10">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <MessageSquare className="w-8 h-8 text-purple-500" />
                  <span className="text-2xl font-bold text-white">4.8/5</span>
                </div>
                <p className="text-sm text-gray-400">Satisfacción</p>
                <p className="text-xs text-purple-500 mt-1">+0.3 vs mes anterior</p>
              </CardContent>
            </Card>
          </div>

          {/* Response Time Distribution */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle>Distribución de Tiempos de Respuesta</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart
                  data={[
                    { time: '0-0.5s', count: 420 },
                    { time: '0.5-1s', count: 280 },
                    { time: '1-2s', count: 150 },
                    { time: '2-3s', count: 80 },
                    { time: '3s+', count: 30 },
                  ]}
                >
                  <defs>
                    <linearGradient id="colorTime" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.secondary} stopOpacity={0.8}/>
                      <stop offset="95%" stopColor={CHART_COLORS.secondary} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="time" stroke="#666" />
                  <YAxis stroke="#666" />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke={CHART_COLORS.secondary}
                    fillOpacity={1}
                    fill="url(#colorTime)"
                    name="Respuestas"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Error Analysis */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle>Análisis de Errores y Problemas</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                  <div className="flex items-center gap-3">
                    <XCircle className="w-5 h-5 text-red-500" />
                    <span className="text-white">Timeouts de Conexión</span>
                  </div>
                  <span className="text-red-500">12 (0.8%)</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                  <div className="flex items-center gap-3">
                    <AlertCircle className="w-5 h-5 text-yellow-500" />
                    <span className="text-white">Respuestas Lentas</span>
                  </div>
                  <span className="text-yellow-500">34 (2.3%)</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-white">Operaciones Exitosas</span>
                  </div>
                  <span className="text-green-500">1,434 (96.9%)</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}