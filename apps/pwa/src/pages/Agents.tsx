import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Bot,
  Brain,
  Mic,
  MessageSquare,
  Globe,
  Zap,
  Shield,
  Settings,
  Save,
  RefreshCw,
  Volume2,
  Phone,
  Mail,
  ChevronRight,
  Sparkles,
  Target,
  Heart,
  BookOpen,
  TrendingUp,
  Users,
  Sliders,
  ToggleLeft,
  ToggleRight,
  Plus,
  Trash2,
  Copy,
  Check
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Textarea } from '../components/ui/textarea'
import { Switch } from '../components/ui/switch'
import { Slider } from '../components/ui/slider'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Badge } from '../components/ui/badge'
import { agentApi } from '../services/api'
import { useToast } from '../hooks/use-toast'

// NGX Agent features
const NGX_AGENT_FEATURES = [
  {
    id: 'empathy-engine',
    name: 'Motor de Empatía Avanzado',
    description: 'Detecta emociones y adapta respuestas para crear conexiones genuinas',
    icon: Heart,
    color: 'text-pink-500',
    category: 'emotional'
  },
  {
    id: 'sales-expert',
    name: 'Experto en Ventas',
    description: 'Técnicas de cierre probadas y manejo de objeciones',
    icon: TrendingUp,
    color: 'text-green-500',
    category: 'sales'
  },
  {
    id: 'lead-qualifier',
    name: 'Calificador de Leads',
    description: 'Identifica automáticamente leads de alto valor',
    icon: Target,
    color: 'text-orange-500',
    category: 'qualification'
  },
  {
    id: 'knowledge-base',
    name: 'Base de Conocimiento NGX',
    description: 'Información completa sobre todos los productos y servicios',
    icon: BookOpen,
    color: 'text-blue-500',
    category: 'knowledge'
  },
  {
    id: 'roi-calculator',
    name: 'Calculadora ROI',
    description: 'Calcula y presenta el retorno de inversión en tiempo real',
    icon: TrendingUp,
    color: 'text-purple-500',
    category: 'sales'
  },
  {
    id: 'multilingual',
    name: 'Soporte Multiidioma',
    description: 'Comunica fluidamente en español, inglés y portugués',
    icon: Globe,
    color: 'text-indigo-500',
    category: 'communication'
  },
  {
    id: 'voice-synthesis',
    name: 'Síntesis de Voz Natural',
    description: 'Voz realista para llamadas telefónicas',
    icon: Volume2,
    color: 'text-cyan-500',
    category: 'communication'
  },
  {
    id: 'ml-learning',
    name: 'Aprendizaje Continuo',
    description: 'Mejora automáticamente con cada conversación',
    icon: Brain,
    color: 'text-violet-500',
    category: 'ai'
  },
  {
    id: 'ab-testing',
    name: 'A/B Testing Automático',
    description: 'Optimiza mensajes y estrategias continuamente',
    icon: Zap,
    color: 'text-yellow-500',
    category: 'optimization'
  },
  {
    id: 'security',
    name: 'Seguridad Empresarial',
    description: 'Encriptación end-to-end y cumplimiento GDPR',
    icon: Shield,
    color: 'text-gray-500',
    category: 'security'
  },
  {
    id: 'integrations',
    name: 'Integraciones Nativas',
    description: 'Conecta con CRM, calendarios y herramientas de marketing',
    icon: Sparkles,
    color: 'text-electric-violet',
    category: 'integration'
  }
]

// Agent configuration interface
interface AgentConfig {
  general: {
    name: string
    description: string
    language: string
    timezone: string
    active: boolean
  }
  personality: {
    tone: string
    empathyLevel: number
    formalityLevel: number
    enthusiasmLevel: number
    customGreeting: string
    customClosing: string
  }
  sales: {
    aggressiveness: number
    objectionHandling: boolean
    priceDisclosure: string
    urgencyCreation: boolean
    socialProof: boolean
    followUpEnabled: boolean
    followUpDelay: number
  }
  channels: {
    voice: {
      enabled: boolean
      voiceId: string
      speed: number
      pitch: number
    }
    chat: {
      enabled: boolean
      typingSpeed: number
      maxResponseTime: number
    }
    email: {
      enabled: boolean
      responseTime: number
      signature: string
    }
  }
  features: string[]
  webhooks: {
    onConversionUrl: string
    onQualifiedLeadUrl: string
    onConversationEndUrl: string
  }
}

// Default configuration
const defaultConfig: AgentConfig = {
  general: {
    name: 'NGX Sales Agent',
    description: 'Tu asistente especializado en ventas para gimnasios y fitness',
    language: 'es',
    timezone: 'America/Mexico_City',
    active: true
  },
  personality: {
    tone: 'friendly',
    empathyLevel: 80,
    formalityLevel: 50,
    enthusiasmLevel: 70,
    customGreeting: 'Hola! Soy tu asistente NGX. Estoy aquí para ayudarte a transformar tu gimnasio con tecnología de vanguardia. ¿En qué puedo ayudarte hoy?',
    customClosing: 'Gracias por tu tiempo. Estoy aquí cuando necesites continuar nuestra conversación. ¡Que tengas un excelente día!'
  },
  sales: {
    aggressiveness: 60,
    objectionHandling: true,
    priceDisclosure: 'after_qualification',
    urgencyCreation: true,
    socialProof: true,
    followUpEnabled: true,
    followUpDelay: 24
  },
  channels: {
    voice: {
      enabled: true,
      voiceId: 'es-MX-DarioNeural',
      speed: 1.0,
      pitch: 1.0
    },
    chat: {
      enabled: true,
      typingSpeed: 50,
      maxResponseTime: 3
    },
    email: {
      enabled: false,
      responseTime: 60,
      signature: 'El equipo NGX'
    }
  },
  features: [
    'empathy-engine',
    'sales-expert',
    'lead-qualifier',
    'knowledge-base',
    'roi-calculator',
    'ml-learning',
    'ab-testing',
    'security'
  ],
  webhooks: {
    onConversionUrl: '',
    onQualifiedLeadUrl: '',
    onConversationEndUrl: ''
  }
}

export function Agents() {
  const [config, setConfig] = useState<AgentConfig>(defaultConfig)
  const [activeTab, setActiveTab] = useState('general')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState<string | null>(null)
  const { toast } = useToast()

  // Load agent configuration on mount
  useEffect(() => {
    loadAgentConfig()
  }, [])

  const loadAgentConfig = async () => {
    setLoading(true)
    try {
      const response = await agentApi.getConfig()
      if (response.data) {
        // Merge with default config to ensure all fields are present
        setConfig({
          ...defaultConfig,
          ...response.data
        })
      }
    } catch (error) {
      console.error('Error loading agent config:', error)
      toast({
        title: "Aviso",
        description: "Usando configuración predeterminada - API no disponible",
        variant: "default",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const response = await agentApi.updateConfig(config)
      if (response.error) {
        throw new Error(response.error)
      }
      
      toast({
        title: "Configuración guardada",
        description: "Los cambios se han aplicado correctamente",
      })
    } catch (error) {
      console.error('Error saving config:', error)
      toast({
        title: "Error",
        description: "No se pudo guardar la configuración (API no disponible)",
        variant: "destructive"
      })
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    setConfig(defaultConfig)
    toast({
      title: "Configuración restaurada",
      description: "Se han restaurado los valores predeterminados",
    })
    
    // Save the reset configuration
    await handleSave()
  }

  const toggleFeature = (featureId: string) => {
    setConfig(prev => ({
      ...prev,
      features: prev.features.includes(featureId)
        ? prev.features.filter(f => f !== featureId)
        : [...prev.features, featureId]
    }))
  }

  const copyWebhook = (webhook: string) => {
    navigator.clipboard.writeText(webhook)
    setCopied(webhook)
    setTimeout(() => setCopied(null), 2000)
  }

  if (loading) {
    return (
      <div className="space-y-4 md:space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl md:text-3xl font-heading text-white">Configuración del Agente</h1>
            <p className="text-gray-400 mt-1">Cargando configuración...</p>
          </div>
        </div>
        <Card className="bg-glass border-white/10">
          <CardContent className="p-6">
            <div className="animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gray-600 rounded-lg"></div>
                <div className="space-y-2">
                  <div className="w-48 h-6 bg-gray-600 rounded"></div>
                  <div className="w-64 h-4 bg-gray-600 rounded"></div>
                </div>
              </div>
            </div>
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
          <h1 className="text-2xl md:text-3xl font-heading text-white">Configuración del Agente</h1>
          <p className="text-gray-400 mt-1">
            Personaliza el comportamiento y capacidades de tu agente NGX
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={handleReset}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Restaurar
          </Button>
          <Button 
            onClick={handleSave}
            disabled={saving}
            className="bg-electric-violet hover:bg-electric-violet/80"
          >
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Guardando...' : 'Guardar cambios'}
          </Button>
        </div>
      </div>

      {/* Agent Status Card */}
      <Card className="bg-glass border-white/10">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-br from-electric-violet to-deep-purple rounded-lg">
                <Bot className="w-8 h-8 text-white" />
              </div>
              <div>
                <h3 className="text-lg md:text-xl font-semibold text-white">{config.general.name}</h3>
                <p className="text-gray-400">{config.general.description}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-400">
                {config.general.active ? 'Activo' : 'Inactivo'}
              </span>
              <Switch
                checked={config.general.active}
                onCheckedChange={(checked) => 
                  setConfig(prev => ({
                    ...prev,
                    general: { ...prev.general, active: checked }
                  }))
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-1">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="personality">Personalidad</TabsTrigger>
          <TabsTrigger value="sales">Ventas</TabsTrigger>
          <TabsTrigger value="channels">Canales</TabsTrigger>
          <TabsTrigger value="features">Características</TabsTrigger>
        </TabsList>

        {/* General Tab */}
        <TabsContent value="general" className="space-y-6">
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle>Información General</CardTitle>
              <CardDescription>
                Configura los datos básicos de tu agente
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                <div className="space-y-2">
                  <Label htmlFor="agent-name">Nombre del Agente</Label>
                  <Input
                    id="agent-name"
                    value={config.general.name}
                    onChange={(e) => 
                      setConfig(prev => ({
                        ...prev,
                        general: { ...prev.general, name: e.target.value }
                      }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="language">Idioma Principal</Label>
                  <Select
                    value={config.general.language}
                    onValueChange={(value) =>
                      setConfig(prev => ({
                        ...prev,
                        general: { ...prev.general, language: value }
                      }))
                    }
                  >
                    <SelectTrigger id="language">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="es">Español</SelectItem>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="pt">Português</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="description">Descripción</Label>
                <Textarea
                  id="description"
                  value={config.general.description}
                  onChange={(e) =>
                    setConfig(prev => ({
                      ...prev,
                      general: { ...prev.general, description: e.target.value }
                    }))
                  }
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="timezone">Zona Horaria</Label>
                <Select
                  value={config.general.timezone}
                  onValueChange={(value) =>
                    setConfig(prev => ({
                      ...prev,
                      general: { ...prev.general, timezone: value }
                    }))
                  }
                >
                  <SelectTrigger id="timezone">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="America/Mexico_City">Ciudad de México</SelectItem>
                    <SelectItem value="America/New_York">Nueva York</SelectItem>
                    <SelectItem value="America/Los_Angeles">Los Ángeles</SelectItem>
                    <SelectItem value="Europe/Madrid">Madrid</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Webhooks */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle>Webhooks</CardTitle>
              <CardDescription>
                Configura URLs para recibir notificaciones de eventos
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="conversion-webhook">Webhook de Conversión</Label>
                <div className="flex gap-2">
                  <Input
                    id="conversion-webhook"
                    placeholder="https://tu-servidor.com/webhook/conversion"
                    value={config.webhooks.onConversionUrl}
                    onChange={(e) =>
                      setConfig(prev => ({
                        ...prev,
                        webhooks: { ...prev.webhooks, onConversionUrl: e.target.value }
                      }))
                    }
                  />
                  <Button
                    size="icon"
                    variant="outline"
                    onClick={() => copyWebhook(config.webhooks.onConversionUrl)}
                  >
                    {copied === config.webhooks.onConversionUrl ? 
                      <Check className="w-4 h-4" /> : 
                      <Copy className="w-4 h-4" />
                    }
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="lead-webhook">Webhook de Lead Calificado</Label>
                <div className="flex gap-2">
                  <Input
                    id="lead-webhook"
                    placeholder="https://tu-servidor.com/webhook/qualified-lead"
                    value={config.webhooks.onQualifiedLeadUrl}
                    onChange={(e) =>
                      setConfig(prev => ({
                        ...prev,
                        webhooks: { ...prev.webhooks, onQualifiedLeadUrl: e.target.value }
                      }))
                    }
                  />
                  <Button
                    size="icon"
                    variant="outline"
                    onClick={() => copyWebhook(config.webhooks.onQualifiedLeadUrl)}
                  >
                    {copied === config.webhooks.onQualifiedLeadUrl ? 
                      <Check className="w-4 h-4" /> : 
                      <Copy className="w-4 h-4" />
                    }
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Personality Tab */}
        <TabsContent value="personality" className="space-y-6">
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle>Personalidad del Agente</CardTitle>
              <CardDescription>
                Define cómo se comunica y comporta tu agente
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="tone">Tono de Comunicación</Label>
                <Select
                  value={config.personality.tone}
                  onValueChange={(value) =>
                    setConfig(prev => ({
                      ...prev,
                      personality: { ...prev.personality, tone: value }
                    }))
                  }
                >
                  <SelectTrigger id="tone">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="friendly">Amigable</SelectItem>
                    <SelectItem value="professional">Profesional</SelectItem>
                    <SelectItem value="enthusiastic">Entusiasta</SelectItem>
                    <SelectItem value="casual">Casual</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Nivel de Empatía</Label>
                    <span className="text-sm text-gray-400">{config.personality.empathyLevel}%</span>
                  </div>
                  <Slider
                    value={[config.personality.empathyLevel]}
                    onValueChange={([value]) =>
                      setConfig(prev => ({
                        ...prev,
                        personality: { ...prev.personality, empathyLevel: value }
                      }))
                    }
                    max={100}
                    step={5}
                    className="w-full"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Nivel de Formalidad</Label>
                    <span className="text-sm text-gray-400">{config.personality.formalityLevel}%</span>
                  </div>
                  <Slider
                    value={[config.personality.formalityLevel]}
                    onValueChange={([value]) =>
                      setConfig(prev => ({
                        ...prev,
                        personality: { ...prev.personality, formalityLevel: value }
                      }))
                    }
                    max={100}
                    step={5}
                    className="w-full"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Nivel de Entusiasmo</Label>
                    <span className="text-sm text-gray-400">{config.personality.enthusiasmLevel}%</span>
                  </div>
                  <Slider
                    value={[config.personality.enthusiasmLevel]}
                    onValueChange={([value]) =>
                      setConfig(prev => ({
                        ...prev,
                        personality: { ...prev.personality, enthusiasmLevel: value }
                      }))
                    }
                    max={100}
                    step={5}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="greeting">Saludo Personalizado</Label>
                <Textarea
                  id="greeting"
                  value={config.personality.customGreeting}
                  onChange={(e) =>
                    setConfig(prev => ({
                      ...prev,
                      personality: { ...prev.personality, customGreeting: e.target.value }
                    }))
                  }
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="closing">Despedida Personalizada</Label>
                <Textarea
                  id="closing"
                  value={config.personality.customClosing}
                  onChange={(e) =>
                    setConfig(prev => ({
                      ...prev,
                      personality: { ...prev.personality, customClosing: e.target.value }
                    }))
                  }
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sales Tab */}
        <TabsContent value="sales" className="space-y-6">
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle>Estrategia de Ventas</CardTitle>
              <CardDescription>
                Configura el comportamiento de ventas del agente
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Nivel de Agresividad en Ventas</Label>
                  <span className="text-sm text-gray-400">{config.sales.aggressiveness}%</span>
                </div>
                <Slider
                  value={[config.sales.aggressiveness]}
                  onValueChange={([value]) =>
                    setConfig(prev => ({
                      ...prev,
                      sales: { ...prev.sales, aggressiveness: value }
                    }))
                  }
                  max={100}
                  step={5}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <Label>Divulgación de Precios</Label>
                <Select
                  value={config.sales.priceDisclosure}
                  onValueChange={(value) =>
                    setConfig(prev => ({
                      ...prev,
                      sales: { ...prev.sales, priceDisclosure: value }
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="immediate">Inmediata</SelectItem>
                    <SelectItem value="after_qualification">Después de Calificar</SelectItem>
                    <SelectItem value="on_request">Solo si lo Solicitan</SelectItem>
                    <SelectItem value="never">Nunca (Referir a Humano)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Manejo de Objeciones</Label>
                    <p className="text-sm text-gray-400">
                      Responde activamente a objeciones comunes
                    </p>
                  </div>
                  <Switch
                    checked={config.sales.objectionHandling}
                    onCheckedChange={(checked) =>
                      setConfig(prev => ({
                        ...prev,
                        sales: { ...prev.sales, objectionHandling: checked }
                      }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Creación de Urgencia</Label>
                    <p className="text-sm text-gray-400">
                      Usa técnicas de escasez y tiempo limitado
                    </p>
                  </div>
                  <Switch
                    checked={config.sales.urgencyCreation}
                    onCheckedChange={(checked) =>
                      setConfig(prev => ({
                        ...prev,
                        sales: { ...prev.sales, urgencyCreation: checked }
                      }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Prueba Social</Label>
                    <p className="text-sm text-gray-400">
                      Menciona casos de éxito y testimonios
                    </p>
                  </div>
                  <Switch
                    checked={config.sales.socialProof}
                    onCheckedChange={(checked) =>
                      setConfig(prev => ({
                        ...prev,
                        sales: { ...prev.sales, socialProof: checked }
                      }))
                    }
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Seguimiento Automático</Label>
                  <Switch
                    checked={config.sales.followUpEnabled}
                    onCheckedChange={(checked) =>
                      setConfig(prev => ({
                        ...prev,
                        sales: { ...prev.sales, followUpEnabled: checked }
                      }))
                    }
                  />
                </div>
                {config.sales.followUpEnabled && (
                  <div className="space-y-2">
                    <Label>Tiempo de Espera para Seguimiento (horas)</Label>
                    <Input
                      type="number"
                      value={config.sales.followUpDelay}
                      onChange={(e) =>
                        setConfig(prev => ({
                          ...prev,
                          sales: { ...prev.sales, followUpDelay: parseInt(e.target.value) || 24 }
                        }))
                      }
                      min={1}
                      max={168}
                    />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Channels Tab */}
        <TabsContent value="channels" className="space-y-6">
          {/* Voice Channel */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Phone className="w-5 h-5" />
                Canal de Voz
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Habilitado</Label>
                <Switch
                  checked={config.channels.voice.enabled}
                  onCheckedChange={(checked) =>
                    setConfig(prev => ({
                      ...prev,
                      channels: {
                        ...prev.channels,
                        voice: { ...prev.channels.voice, enabled: checked }
                      }
                    }))
                  }
                />
              </div>

              {config.channels.voice.enabled && (
                <>
                  <div className="space-y-2">
                    <Label>Voz</Label>
                    <Select
                      value={config.channels.voice.voiceId}
                      onValueChange={(value) =>
                        setConfig(prev => ({
                          ...prev,
                          channels: {
                            ...prev.channels,
                            voice: { ...prev.channels.voice, voiceId: value }
                          }
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="es-MX-DarioNeural">Darío (México)</SelectItem>
                        <SelectItem value="es-MX-MarinaNeural">Marina (México)</SelectItem>
                        <SelectItem value="es-ES-AlvaroNeural">Álvaro (España)</SelectItem>
                        <SelectItem value="es-ES-ElviraNeural">Elvira (España)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Velocidad</Label>
                      <span className="text-sm text-gray-400">{config.channels.voice.speed}x</span>
                    </div>
                    <Slider
                      value={[config.channels.voice.speed * 100]}
                      onValueChange={([value]) =>
                        setConfig(prev => ({
                          ...prev,
                          channels: {
                            ...prev.channels,
                            voice: { ...prev.channels.voice, speed: value / 100 }
                          }
                        }))
                      }
                      min={50}
                      max={150}
                      step={10}
                    />
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Chat Channel */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5" />
                Canal de Chat
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Habilitado</Label>
                <Switch
                  checked={config.channels.chat.enabled}
                  onCheckedChange={(checked) =>
                    setConfig(prev => ({
                      ...prev,
                      channels: {
                        ...prev.channels,
                        chat: { ...prev.channels.chat, enabled: checked }
                      }
                    }))
                  }
                />
              </div>

              {config.channels.chat.enabled && (
                <>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Velocidad de Escritura</Label>
                      <span className="text-sm text-gray-400">{config.channels.chat.typingSpeed} cpm</span>
                    </div>
                    <Slider
                      value={[config.channels.chat.typingSpeed]}
                      onValueChange={([value]) =>
                        setConfig(prev => ({
                          ...prev,
                          channels: {
                            ...prev.channels,
                            chat: { ...prev.channels.chat, typingSpeed: value }
                          }
                        }))
                      }
                      min={20}
                      max={100}
                      step={10}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Tiempo Máximo de Respuesta (segundos)</Label>
                    <Input
                      type="number"
                      value={config.channels.chat.maxResponseTime}
                      onChange={(e) =>
                        setConfig(prev => ({
                          ...prev,
                          channels: {
                            ...prev.channels,
                            chat: { ...prev.channels.chat, maxResponseTime: parseInt(e.target.value) || 3 }
                          }
                        }))
                      }
                      min={1}
                      max={10}
                    />
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Email Channel */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mail className="w-5 h-5" />
                Canal de Email
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Habilitado</Label>
                <Switch
                  checked={config.channels.email.enabled}
                  onCheckedChange={(checked) =>
                    setConfig(prev => ({
                      ...prev,
                      channels: {
                        ...prev.channels,
                        email: { ...prev.channels.email, enabled: checked }
                      }
                    }))
                  }
                />
              </div>

              {config.channels.email.enabled && (
                <>
                  <div className="space-y-2">
                    <Label>Tiempo de Respuesta (minutos)</Label>
                    <Input
                      type="number"
                      value={config.channels.email.responseTime}
                      onChange={(e) =>
                        setConfig(prev => ({
                          ...prev,
                          channels: {
                            ...prev.channels,
                            email: { ...prev.channels.email, responseTime: parseInt(e.target.value) || 60 }
                          }
                        }))
                      }
                      min={5}
                      max={1440}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Firma de Email</Label>
                    <Input
                      value={config.channels.email.signature}
                      onChange={(e) =>
                        setConfig(prev => ({
                          ...prev,
                          channels: {
                            ...prev.channels,
                            email: { ...prev.channels.email, signature: e.target.value }
                          }
                        }))
                      }
                    />
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Features Tab */}
        <TabsContent value="features" className="space-y-6">
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle>Características del Agente</CardTitle>
              <CardDescription>
                Activa o desactiva las capacidades avanzadas de NGX
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                {NGX_AGENT_FEATURES.map((feature) => (
                  <motion.div
                    key={feature.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`p-4 rounded-lg border cursor-pointer transition-all ${
                      config.features.includes(feature.id)
                        ? 'bg-electric-violet/20 border-electric-violet/50'
                        : 'bg-white/5 border-white/10 opacity-60'
                    }`}
                    onClick={() => toggleFeature(feature.id)}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg bg-black/20`}>
                        <feature.icon className={`w-5 h-5 ${feature.color}`} />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-white flex items-center gap-2">
                          {feature.name}
                          {config.features.includes(feature.id) && (
                            <Check className="w-4 h-4 text-electric-violet" />
                          )}
                        </h4>
                        <p className="text-sm text-gray-400 mt-1">
                          {feature.description}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Feature Categories Summary */}
          <Card className="bg-glass border-white/10">
            <CardHeader>
              <CardTitle>Resumen de Capacidades</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(
                  NGX_AGENT_FEATURES.reduce((acc, feature) => {
                    if (config.features.includes(feature.id)) {
                      acc[feature.category] = (acc[feature.category] || 0) + 1
                    }
                    return acc
                  }, {} as Record<string, number>)
                ).map(([category, count]) => (
                  <div key={category} className="flex items-center justify-between">
                    <span className="text-sm capitalize text-gray-300">
                      {category.replace('_', ' ')}
                    </span>
                    <Badge variant="secondary">{count} activas</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}