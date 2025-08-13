import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Settings as SettingsIcon,
  User,
  Shield,
  Bell,
  Moon,
  Sun,
  Monitor,
  Key,
  CreditCard,
  Download,
  Upload,
  Globe,
  Save,
  Eye,
  EyeOff,
  Mail,
  Phone,
  Building,
  Lock,
  Trash2,
  AlertTriangle,
  Check,
  X,
  Edit3,
  Camera,
  Loader2,
  Palette,
  Volume2,
  VolumeX,
  Smartphone,
  Monitor as MonitorIcon,
  Zap,
  Calendar,
  Clock,
  MapPin,
  Languages,
  Database
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Textarea } from '../components/ui/textarea'
import { Switch } from '../components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Badge } from '../components/ui/badge'
import { Separator } from '../components/ui/separator'
import { useToast } from '../hooks/use-toast'
import { authApi } from '../services/api'
import { getUser, setUser } from '../services/auth'

// Animation variants
const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 }
}

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
}

// Theme options
const THEME_OPTIONS = [
  { value: 'dark', label: 'Oscuro', icon: Moon },
  { value: 'light', label: 'Claro', icon: Sun },
  { value: 'system', label: 'Sistema', icon: Monitor }
]

// Language options
const LANGUAGE_OPTIONS = [
  { value: 'es', label: 'Español', flag: '🇪🇸' },
  { value: 'en', label: 'English', flag: '🇺🇸' },
  { value: 'pt', label: 'Português', flag: '🇧🇷' }
]

// Timezone options
const TIMEZONE_OPTIONS = [
  { value: 'America/Mexico_City', label: 'Ciudad de México (GMT-6)' },
  { value: 'America/New_York', label: 'Nueva York (GMT-5)' },
  { value: 'America/Los_Angeles', label: 'Los Ángeles (GMT-8)' },
  { value: 'Europe/Madrid', label: 'Madrid (GMT+1)' },
  { value: 'America/Sao_Paulo', label: 'São Paulo (GMT-3)' }
]

// User settings interface
interface UserSettings {
  profile: {
    email: string
    full_name: string
    organization_name: string
    phone: string
    avatar: string
    bio: string
    timezone: string
    language: string
  }
  notifications: {
    email_enabled: boolean
    sms_enabled: boolean
    push_enabled: boolean
    marketing_emails: boolean
    conversion_alerts: boolean
    lead_alerts: boolean
    system_updates: boolean
    weekly_reports: boolean
  }
  appearance: {
    theme: string
    sidebar_collapsed: boolean
    density: string
    animations_enabled: boolean
    sound_enabled: boolean
  }
  security: {
    two_factor_enabled: boolean
    session_timeout: number
    login_alerts: boolean
    api_access_enabled: boolean
    password_last_changed: string
  }
  billing: {
    plan: string
    billing_email: string
    payment_method: string
    next_billing_date: string
    usage_alerts: boolean
  }
  privacy: {
    analytics_enabled: boolean
    data_retention_days: number
    allow_data_export: boolean
    cookie_consent: boolean
  }
}

// Default settings
const defaultSettings: UserSettings = {
  profile: {
    email: '',
    full_name: '',
    organization_name: '',
    phone: '',
    avatar: '',
    bio: '',
    timezone: 'America/Mexico_City',
    language: 'es'
  },
  notifications: {
    email_enabled: true,
    sms_enabled: false,
    push_enabled: true,
    marketing_emails: false,
    conversion_alerts: true,
    lead_alerts: true,
    system_updates: true,
    weekly_reports: true
  },
  appearance: {
    theme: 'dark',
    sidebar_collapsed: false,
    density: 'comfortable',
    animations_enabled: true,
    sound_enabled: true
  },
  security: {
    two_factor_enabled: false,
    session_timeout: 30,
    login_alerts: true,
    api_access_enabled: false,
    password_last_changed: new Date().toISOString()
  },
  billing: {
    plan: 'Pro',
    billing_email: '',
    payment_method: '••••4242',
    next_billing_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    usage_alerts: true
  },
  privacy: {
    analytics_enabled: true,
    data_retention_days: 365,
    allow_data_export: true,
    cookie_consent: true
  }
}

export function Settings() {
  const [settings, setSettings] = useState<UserSettings>(defaultSettings)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')
  const [showPasswordChange, setShowPasswordChange] = useState(false)
  const [passwordData, setPasswordData] = useState({
    current: '',
    new: '',
    confirm: ''
  })
  const [showPassword, setShowPassword] = useState({
    current: false,
    new: false,
    confirm: false
  })
  const [unsavedChanges, setUnsavedChanges] = useState(false)
  const { toast } = useToast()

  // Load user settings on mount
  useEffect(() => {
    loadUserSettings()
  }, [])

  // Track unsaved changes
  useEffect(() => {
    const storedSettings = localStorage.getItem('ngx_user_settings')
    const baseSettings = storedSettings ? JSON.parse(storedSettings) : defaultSettings
    const hasChanges = JSON.stringify(settings) !== JSON.stringify(baseSettings)
    setUnsavedChanges(hasChanges)
  }, [settings])

  const loadUserSettings = async () => {
    setLoading(true)
    try {
      // Load from localStorage first
      const storedSettings = localStorage.getItem('ngx_user_settings')
      if (storedSettings) {
        setSettings(JSON.parse(storedSettings))
      }

      // Load user data from auth service
      const user = getUser()
      if (user) {
        setSettings(prev => ({
          ...prev,
          profile: {
            ...prev.profile,
            email: user.email,
            full_name: user.full_name,
            organization_name: user.organization_id || ''
          },
          billing: {
            ...prev.billing,
            billing_email: user.email
          }
        }))
      }

      // Load additional settings from API
      const response = await authApi.getMe()
      if (response.data) {
        const userData = response.data
        setSettings(prev => ({
          ...prev,
          profile: {
            ...prev.profile,
            ...userData.profile
          }
        }))
      }
    } catch (error) {
      console.error('Error loading user settings:', error)
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
      // Save to local storage
      localStorage.setItem('ngx_user_settings', JSON.stringify(settings))
      
      // Update user data in auth service
      const currentUser = getUser()
      if (currentUser) {
        setUser({
          ...currentUser,
          email: settings.profile.email,
          full_name: settings.profile.full_name
        })
      }

      // Apply theme changes immediately
      if (settings.appearance.theme === 'light') {
        document.documentElement.classList.remove('dark')
      } else if (settings.appearance.theme === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        // System theme
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        document.documentElement.classList.toggle('dark', prefersDark)
      }

      setUnsavedChanges(false)
      toast({
        title: "Configuración guardada",
        description: "Tus cambios se han aplicado correctamente",
      })
    } catch (error) {
      console.error('Error saving settings:', error)
      toast({
        title: "Error",
        description: "No se pudo guardar la configuración",
        variant: "destructive"
      })
    } finally {
      setSaving(false)
    }
  }

  const handlePasswordChange = async () => {
    if (passwordData.new !== passwordData.confirm) {
      toast({
        title: "Error",
        description: "Las contraseñas no coinciden",
        variant: "destructive"
      })
      return
    }

    if (passwordData.new.length < 8) {
      toast({
        title: "Error",
        description: "La contraseña debe tener al menos 8 caracteres",
        variant: "destructive"
      })
      return
    }

    try {
      // Here you would call the password change API
      // await authApi.changePassword(passwordData.current, passwordData.new)
      
      setPasswordData({ current: '', new: '', confirm: '' })
      setShowPasswordChange(false)
      setSettings(prev => ({
        ...prev,
        security: {
          ...prev.security,
          password_last_changed: new Date().toISOString()
        }
      }))
      
      toast({
        title: "Contraseña actualizada",
        description: "Tu contraseña ha sido cambiada exitosamente",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudo cambiar la contraseña",
        variant: "destructive"
      })
    }
  }

  const handleExportData = async () => {
    try {
      const exportData = {
        settings,
        exported_at: new Date().toISOString(),
        version: '1.0'
      }
      
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ngx-settings-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      toast({
        title: "Datos exportados",
        description: "Tu configuración se ha descargado exitosamente",
      })
    } catch (error) {
      toast({
        title: "Error al exportar",
        description: "No se pudieron exportar los datos",
        variant: "destructive"
      })
    }
  }

  const handleImportData = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const importedData = JSON.parse(e.target?.result as string)
        if (importedData.settings) {
          setSettings(importedData.settings)
          toast({
            title: "Datos importados",
            description: "Tu configuración ha sido restaurada",
          })
        }
      } catch (error) {
        toast({
          title: "Error al importar",
          description: "El archivo no es válido",
          variant: "destructive"
        })
      }
    }
    reader.readAsText(file)
  }

  const updateSettings = (section: keyof UserSettings, key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }))
  }

  if (loading) {
    return (
      <div className="space-y-4 md:space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="w-48 h-8 bg-gray-600 rounded animate-pulse mb-2"></div>
            <div className="w-64 h-4 bg-gray-600 rounded animate-pulse"></div>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-6">
          {[1, 2, 3].map(i => (
            <Card key={i} className="bg-glass border-white/10">
              <CardContent className="p-6">
                <div className="animate-pulse space-y-4">
                  <div className="w-full h-6 bg-gray-600 rounded"></div>
                  <div className="w-3/4 h-4 bg-gray-600 rounded"></div>
                  <div className="w-1/2 h-4 bg-gray-600 rounded"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <motion.div 
      className="space-y-4 md:space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Header */}
      <motion.div 
        className="flex flex-col md:flex-row md:items-center justify-between gap-4"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div>
          <h1 className="text-2xl md:text-3xl font-heading text-white">Configuración</h1>
          <p className="text-gray-400 mt-1">
            Gestiona tu cuenta y preferencias del sistema
            {unsavedChanges && (
              <Badge variant="secondary" className="ml-2">
                Cambios sin guardar
              </Badge>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            variant="outline" 
            onClick={loadUserSettings}
            disabled={loading}
          >
            <Loader2 className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Recargar
          </Button>
          <Button 
            onClick={handleSave}
            disabled={saving || !unsavedChanges}
            className="bg-electric-violet hover:bg-electric-violet/80"
          >
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Guardando...' : 'Guardar cambios'}
          </Button>
        </div>
      </motion.div>

      {/* Settings Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-1">
            <TabsTrigger value="profile">Perfil</TabsTrigger>
            <TabsTrigger value="notifications">Notificaciones</TabsTrigger>
            <TabsTrigger value="appearance">Apariencia</TabsTrigger>
            <TabsTrigger value="security">Seguridad</TabsTrigger>
            <TabsTrigger value="billing">Facturación</TabsTrigger>
            <TabsTrigger value="privacy">Privacidad</TabsTrigger>
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile" className="space-y-6">
            <AnimatePresence mode="wait">
              <motion.div
                key="profile"
                variants={staggerContainer}
                initial="initial"
                animate="animate"
                className="space-y-6"
              >
                {/* Personal Information */}
                <motion.div variants={fadeInUp}>
                  <Card className="bg-glass border-white/10">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <User className="w-5 h-5 text-electric-violet" />
                        Información Personal
                      </CardTitle>
                      <CardDescription>
                        Gestiona tu información de perfil y datos de contacto
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Avatar Section */}
                      <div className="flex items-center gap-6">
                        <div className="relative">
                          <div className="w-20 h-20 bg-gradient-to-br from-electric-violet to-deep-purple rounded-full flex items-center justify-center">
                            {settings.profile.avatar ? (
                              <img 
                                src={settings.profile.avatar} 
                                alt="Avatar" 
                                className="w-full h-full rounded-full object-cover"
                              />
                            ) : (
                              <User className="w-8 h-8 text-white" />
                            )}
                          </div>
                          <Button
                            size="sm"
                            className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full p-0"
                            variant="secondary"
                          >
                            <Camera className="w-4 h-4" />
                          </Button>
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-white">{settings.profile.full_name || 'Usuario NGX'}</h3>
                          <p className="text-gray-400">{settings.profile.email}</p>
                          <Badge variant="secondary" className="mt-1">
                            {settings.billing.plan}
                          </Badge>
                        </div>
                      </div>

                      <Separator />

                      {/* Form Fields */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                          <Label htmlFor="full_name">Nombre completo</Label>
                          <Input
                            id="full_name"
                            value={settings.profile.full_name}
                            onChange={(e) => updateSettings('profile', 'full_name', e.target.value)}
                            placeholder="Tu nombre completo"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="email">Correo electrónico</Label>
                          <Input
                            id="email"
                            type="email"
                            value={settings.profile.email}
                            onChange={(e) => updateSettings('profile', 'email', e.target.value)}
                            placeholder="tu@email.com"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="phone">Teléfono</Label>
                          <Input
                            id="phone"
                            value={settings.profile.phone}
                            onChange={(e) => updateSettings('profile', 'phone', e.target.value)}
                            placeholder="+52 55 1234 5678"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="organization">Organización</Label>
                          <Input
                            id="organization"
                            value={settings.profile.organization_name}
                            onChange={(e) => updateSettings('profile', 'organization_name', e.target.value)}
                            placeholder="Nombre de tu empresa"
                          />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="bio">Biografía</Label>
                        <Textarea
                          id="bio"
                          value={settings.profile.bio}
                          onChange={(e) => updateSettings('profile', 'bio', e.target.value)}
                          placeholder="Cuéntanos un poco sobre ti..."
                          rows={3}
                        />
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                          <Label htmlFor="language">Idioma</Label>
                          <Select
                            value={settings.profile.language}
                            onValueChange={(value) => updateSettings('profile', 'language', value)}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {LANGUAGE_OPTIONS.map(lang => (
                                <SelectItem key={lang.value} value={lang.value}>
                                  <div className="flex items-center gap-2">
                                    <span>{lang.flag}</span>
                                    {lang.label}
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="timezone">Zona horaria</Label>
                          <Select
                            value={settings.profile.timezone}
                            onValueChange={(value) => updateSettings('profile', 'timezone', value)}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {TIMEZONE_OPTIONS.map(tz => (
                                <SelectItem key={tz.value} value={tz.value}>
                                  {tz.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>
            </AnimatePresence>
          </TabsContent>

          {/* Notifications Tab */}
          <TabsContent value="notifications" className="space-y-6">
            <AnimatePresence mode="wait">
              <motion.div
                key="notifications"
                variants={staggerContainer}
                initial="initial"
                animate="animate"
                className="space-y-6"
              >
                <motion.div variants={fadeInUp}>
                  <Card className="bg-glass border-white/10">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Bell className="w-5 h-5 text-electric-violet" />
                        Preferencias de Notificación
                      </CardTitle>
                      <CardDescription>
                        Configura cómo y cuándo quieres recibir notificaciones
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Channel Settings */}
                      <div className="space-y-4">
                        <h4 className="text-sm font-medium text-white">Canales de Notificación</h4>
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <div className="flex items-center gap-2">
                                <Mail className="w-4 h-4 text-blue-500" />
                                <Label>Notificaciones por Email</Label>
                              </div>
                              <p className="text-sm text-gray-400">
                                Recibe notificaciones importantes en tu correo
                              </p>
                            </div>
                            <Switch
                              checked={settings.notifications.email_enabled}
                              onCheckedChange={(checked) => updateSettings('notifications', 'email_enabled', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <div className="flex items-center gap-2">
                                <Smartphone className="w-4 h-4 text-green-500" />
                                <Label>Notificaciones SMS</Label>
                              </div>
                              <p className="text-sm text-gray-400">
                                Alertas críticas por mensaje de texto
                              </p>
                            </div>
                            <Switch
                              checked={settings.notifications.sms_enabled}
                              onCheckedChange={(checked) => updateSettings('notifications', 'sms_enabled', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <div className="flex items-center gap-2">
                                <MonitorIcon className="w-4 h-4 text-purple-500" />
                                <Label>Notificaciones Push</Label>
                              </div>
                              <p className="text-sm text-gray-400">
                                Notificaciones en tiempo real en el navegador
                              </p>
                            </div>
                            <Switch
                              checked={settings.notifications.push_enabled}
                              onCheckedChange={(checked) => updateSettings('notifications', 'push_enabled', checked)}
                            />
                          </div>
                        </div>
                      </div>

                      <Separator />

                      {/* Notification Types */}
                      <div className="space-y-4">
                        <h4 className="text-sm font-medium text-white">Tipos de Notificación</h4>
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Alertas de Conversión</Label>
                              <p className="text-sm text-gray-400">
                                Notifica cuando se complete una venta
                              </p>
                            </div>
                            <Switch
                              checked={settings.notifications.conversion_alerts}
                              onCheckedChange={(checked) => updateSettings('notifications', 'conversion_alerts', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Alertas de Leads</Label>
                              <p className="text-sm text-gray-400">
                                Notifica sobre nuevos leads calificados
                              </p>
                            </div>
                            <Switch
                              checked={settings.notifications.lead_alerts}
                              onCheckedChange={(checked) => updateSettings('notifications', 'lead_alerts', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Actualizaciones del Sistema</Label>
                              <p className="text-sm text-gray-400">
                                Información sobre mantenimiento y actualizaciones
                              </p>
                            </div>
                            <Switch
                              checked={settings.notifications.system_updates}
                              onCheckedChange={(checked) => updateSettings('notifications', 'system_updates', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Reportes Semanales</Label>
                              <p className="text-sm text-gray-400">
                                Resumen semanal de rendimiento
                              </p>
                            </div>
                            <Switch
                              checked={settings.notifications.weekly_reports}
                              onCheckedChange={(checked) => updateSettings('notifications', 'weekly_reports', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Emails de Marketing</Label>
                              <p className="text-sm text-gray-400">
                                Tips, novedades y ofertas especiales
                              </p>
                            </div>
                            <Switch
                              checked={settings.notifications.marketing_emails}
                              onCheckedChange={(checked) => updateSettings('notifications', 'marketing_emails', checked)}
                            />
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>
            </AnimatePresence>
          </TabsContent>

          {/* Appearance Tab */}
          <TabsContent value="appearance" className="space-y-6">
            <AnimatePresence mode="wait">
              <motion.div
                key="appearance"
                variants={staggerContainer}
                initial="initial"
                animate="animate"
                className="space-y-6"
              >
                <motion.div variants={fadeInUp}>
                  <Card className="bg-glass border-white/10">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Palette className="w-5 h-5 text-electric-violet" />
                        Apariencia y Tema
                      </CardTitle>
                      <CardDescription>
                        Personaliza la interfaz según tus preferencias
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Theme Selection */}
                      <div className="space-y-4">
                        <Label>Tema de la Aplicación</Label>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          {THEME_OPTIONS.map(theme => (
                            <motion.div
                              key={theme.value}
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                            >
                              <Card 
                                className={`cursor-pointer transition-all ${
                                  settings.appearance.theme === theme.value
                                    ? 'bg-electric-violet/20 border-electric-violet/50'
                                    : 'bg-white/5 border-white/10 hover:bg-white/10'
                                }`}
                                onClick={() => updateSettings('appearance', 'theme', theme.value)}
                              >
                                <CardContent className="p-4 text-center">
                                  <theme.icon className="w-8 h-8 mx-auto mb-2 text-electric-violet" />
                                  <p className="text-sm font-medium text-white">{theme.label}</p>
                                </CardContent>
                              </Card>
                            </motion.div>
                          ))}
                        </div>
                      </div>

                      <Separator />

                      {/* Interface Settings */}
                      <div className="space-y-4">
                        <h4 className="text-sm font-medium text-white">Configuración de Interfaz</h4>
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Animaciones</Label>
                              <p className="text-sm text-gray-400">
                                Habilitar transiciones y efectos visuales
                              </p>
                            </div>
                            <Switch
                              checked={settings.appearance.animations_enabled}
                              onCheckedChange={(checked) => updateSettings('appearance', 'animations_enabled', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Sonidos del Sistema</Label>
                              <p className="text-sm text-gray-400">
                                Reproducir sonidos para notificaciones
                              </p>
                            </div>
                            <Switch
                              checked={settings.appearance.sound_enabled}
                              onCheckedChange={(checked) => updateSettings('appearance', 'sound_enabled', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Sidebar Contraído</Label>
                              <p className="text-sm text-gray-400">
                                Mostrar solo íconos en la barra lateral
                              </p>
                            </div>
                            <Switch
                              checked={settings.appearance.sidebar_collapsed}
                              onCheckedChange={(checked) => updateSettings('appearance', 'sidebar_collapsed', checked)}
                            />
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label>Densidad de la Interfaz</Label>
                        <Select
                          value={settings.appearance.density}
                          onValueChange={(value) => updateSettings('appearance', 'density', value)}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="compact">Compacta</SelectItem>
                            <SelectItem value="comfortable">Cómoda</SelectItem>
                            <SelectItem value="spacious">Espaciosa</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>
            </AnimatePresence>
          </TabsContent>

          {/* Security Tab */}
          <TabsContent value="security" className="space-y-6">
            <AnimatePresence mode="wait">
              <motion.div
                key="security"
                variants={staggerContainer}
                initial="initial"
                animate="animate"
                className="space-y-6"
              >
                <motion.div variants={fadeInUp}>
                  <Card className="bg-glass border-white/10">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Shield className="w-5 h-5 text-electric-violet" />
                        Seguridad de la Cuenta
                      </CardTitle>
                      <CardDescription>
                        Protege tu cuenta con configuraciones de seguridad avanzadas
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Password Section */}
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="text-sm font-medium text-white">Contraseña</h4>
                            <p className="text-sm text-gray-400">
                              Última actualización: {new Date(settings.security.password_last_changed).toLocaleDateString()}
                            </p>
                          </div>
                          <Button 
                            variant="outline" 
                            onClick={() => setShowPasswordChange(!showPasswordChange)}
                          >
                            <Key className="w-4 h-4 mr-2" />
                            Cambiar contraseña
                          </Button>
                        </div>

                        {showPasswordChange && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="space-y-4 p-4 bg-white/5 rounded-lg"
                          >
                            <div className="space-y-2">
                              <Label htmlFor="current-password">Contraseña actual</Label>
                              <div className="relative">
                                <Input
                                  id="current-password"
                                  type={showPassword.current ? 'text' : 'password'}
                                  value={passwordData.current}
                                  onChange={(e) => setPasswordData(prev => ({ ...prev, current: e.target.value }))}
                                  placeholder="Introduce tu contraseña actual"
                                />
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="absolute right-0 top-0 h-full px-3"
                                  onClick={() => setShowPassword(prev => ({ ...prev, current: !prev.current }))}
                                >
                                  {showPassword.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </Button>
                              </div>
                            </div>
                            
                            <div className="space-y-2">
                              <Label htmlFor="new-password">Nueva contraseña</Label>
                              <div className="relative">
                                <Input
                                  id="new-password"
                                  type={showPassword.new ? 'text' : 'password'}
                                  value={passwordData.new}
                                  onChange={(e) => setPasswordData(prev => ({ ...prev, new: e.target.value }))}
                                  placeholder="Introduce tu nueva contraseña"
                                />
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="absolute right-0 top-0 h-full px-3"
                                  onClick={() => setShowPassword(prev => ({ ...prev, new: !prev.new }))}
                                >
                                  {showPassword.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </Button>
                              </div>
                            </div>
                            
                            <div className="space-y-2">
                              <Label htmlFor="confirm-password">Confirmar nueva contraseña</Label>
                              <div className="relative">
                                <Input
                                  id="confirm-password"
                                  type={showPassword.confirm ? 'text' : 'password'}
                                  value={passwordData.confirm}
                                  onChange={(e) => setPasswordData(prev => ({ ...prev, confirm: e.target.value }))}
                                  placeholder="Confirma tu nueva contraseña"
                                />
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="absolute right-0 top-0 h-full px-3"
                                  onClick={() => setShowPassword(prev => ({ ...prev, confirm: !prev.confirm }))}
                                >
                                  {showPassword.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </Button>
                              </div>
                            </div>
                            
                            <div className="flex justify-end gap-2">
                              <Button variant="outline" onClick={() => setShowPasswordChange(false)}>
                                Cancelar
                              </Button>
                              <Button onClick={handlePasswordChange}>
                                Actualizar contraseña
                              </Button>
                            </div>
                          </motion.div>
                        )}
                      </div>

                      <Separator />

                      {/* Security Settings */}
                      <div className="space-y-4">
                        <h4 className="text-sm font-medium text-white">Configuraciones de Seguridad</h4>
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Autenticación de Dos Factores</Label>
                              <p className="text-sm text-gray-400">
                                Añade una capa extra de seguridad a tu cuenta
                              </p>
                            </div>
                            <Switch
                              checked={settings.security.two_factor_enabled}
                              onCheckedChange={(checked) => updateSettings('security', 'two_factor_enabled', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Alertas de Inicio de Sesión</Label>
                              <p className="text-sm text-gray-400">
                                Notificar sobre nuevos inicios de sesión
                              </p>
                            </div>
                            <Switch
                              checked={settings.security.login_alerts}
                              onCheckedChange={(checked) => updateSettings('security', 'login_alerts', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Acceso API</Label>
                              <p className="text-sm text-gray-400">
                                Permitir acceso a la API para integraciones
                              </p>
                            </div>
                            <Switch
                              checked={settings.security.api_access_enabled}
                              onCheckedChange={(checked) => updateSettings('security', 'api_access_enabled', checked)}
                            />
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label>Tiempo de Sesión (minutos)</Label>
                        <Select
                          value={settings.security.session_timeout.toString()}
                          onValueChange={(value) => updateSettings('security', 'session_timeout', parseInt(value))}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="15">15 minutos</SelectItem>
                            <SelectItem value="30">30 minutos</SelectItem>
                            <SelectItem value="60">1 hora</SelectItem>
                            <SelectItem value="120">2 horas</SelectItem>
                            <SelectItem value="480">8 horas</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>
            </AnimatePresence>
          </TabsContent>

          {/* Billing Tab */}
          <TabsContent value="billing" className="space-y-6">
            <AnimatePresence mode="wait">
              <motion.div
                key="billing"
                variants={staggerContainer}
                initial="initial"
                animate="animate"
                className="space-y-6"
              >
                <motion.div variants={fadeInUp}>
                  <Card className="bg-glass border-white/10">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <CreditCard className="w-5 h-5 text-electric-violet" />
                        Facturación y Suscripción
                      </CardTitle>
                      <CardDescription>
                        Gestiona tu plan, método de pago y facturación
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Current Plan */}
                      <div className="p-4 bg-gradient-to-r from-electric-violet/20 to-deep-purple/20 rounded-lg border border-electric-violet/30">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="text-lg font-semibold text-white">Plan {settings.billing.plan}</h4>
                            <p className="text-gray-400">
                              Próxima facturación: {new Date(settings.billing.next_billing_date).toLocaleDateString()}
                            </p>
                          </div>
                          <Badge className="bg-electric-violet text-white">
                            Activo
                          </Badge>
                        </div>
                      </div>

                      {/* Payment Method */}
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="text-sm font-medium text-white">Método de Pago</h4>
                            <p className="text-sm text-gray-400">
                              **** **** **** {settings.billing.payment_method.slice(-4)}
                            </p>
                          </div>
                          <Button variant="outline" size="sm">
                            <Edit3 className="w-4 h-4 mr-2" />
                            Actualizar
                          </Button>
                        </div>
                      </div>

                      <Separator />

                      {/* Billing Settings */}
                      <div className="space-y-4">
                        <h4 className="text-sm font-medium text-white">Configuración de Facturación</h4>
                        <div className="space-y-4">
                          <div className="space-y-2">
                            <Label htmlFor="billing-email">Email de facturación</Label>
                            <Input
                              id="billing-email"
                              type="email"
                              value={settings.billing.billing_email}
                              onChange={(e) => updateSettings('billing', 'billing_email', e.target.value)}
                              placeholder="facturas@tuempresa.com"
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Alertas de Uso</Label>
                              <p className="text-sm text-gray-400">
                                Notificar cuando se acerque al límite del plan
                              </p>
                            </div>
                            <Switch
                              checked={settings.billing.usage_alerts}
                              onCheckedChange={(checked) => updateSettings('billing', 'usage_alerts', checked)}
                            />
                          </div>
                        </div>
                      </div>

                      {/* Plan Actions */}
                      <div className="flex gap-3">
                        <Button variant="outline">
                          <Zap className="w-4 h-4 mr-2" />
                          Mejorar Plan
                        </Button>
                        <Button variant="outline">
                          <Download className="w-4 h-4 mr-2" />
                          Descargar Facturas
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>
            </AnimatePresence>
          </TabsContent>

          {/* Privacy Tab */}
          <TabsContent value="privacy" className="space-y-6">
            <AnimatePresence mode="wait">
              <motion.div
                key="privacy"
                variants={staggerContainer}
                initial="initial"
                animate="animate"
                className="space-y-6"
              >
                <motion.div variants={fadeInUp}>
                  <Card className="bg-glass border-white/10">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Database className="w-5 h-5 text-electric-violet" />
                        Privacidad y Datos
                      </CardTitle>
                      <CardDescription>
                        Controla cómo se utilizan y almacenan tus datos
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Data Control */}
                      <div className="space-y-4">
                        <h4 className="text-sm font-medium text-white">Control de Datos</h4>
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Análisis de Uso</Label>
                              <p className="text-sm text-gray-400">
                                Permitir recopilación de datos para mejorar el servicio
                              </p>
                            </div>
                            <Switch
                              checked={settings.privacy.analytics_enabled}
                              onCheckedChange={(checked) => updateSettings('privacy', 'analytics_enabled', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Exportación de Datos</Label>
                              <p className="text-sm text-gray-400">
                                Permitir la descarga de todos tus datos
                              </p>
                            </div>
                            <Switch
                              checked={settings.privacy.allow_data_export}
                              onCheckedChange={(checked) => updateSettings('privacy', 'allow_data_export', checked)}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <Label>Consentimiento de Cookies</Label>
                              <p className="text-sm text-gray-400">
                                Acepto el uso de cookies para funcionalidad básica
                              </p>
                            </div>
                            <Switch
                              checked={settings.privacy.cookie_consent}
                              onCheckedChange={(checked) => updateSettings('privacy', 'cookie_consent', checked)}
                            />
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label>Retención de Datos (días)</Label>
                        <Select
                          value={settings.privacy.data_retention_days.toString()}
                          onValueChange={(value) => updateSettings('privacy', 'data_retention_days', parseInt(value))}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="30">30 días</SelectItem>
                            <SelectItem value="90">90 días</SelectItem>
                            <SelectItem value="180">180 días</SelectItem>
                            <SelectItem value="365">1 año</SelectItem>
                            <SelectItem value="730">2 años</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <Separator />

                      {/* Data Actions */}
                      <div className="space-y-4">
                        <h4 className="text-sm font-medium text-white">Acciones de Datos</h4>
                        <div className="flex flex-wrap gap-3">
                          <Button variant="outline" onClick={handleExportData}>
                            <Download className="w-4 h-4 mr-2" />
                            Exportar Datos
                          </Button>
                          <label>
                            <Button variant="outline" asChild>
                              <span>
                                <Upload className="w-4 h-4 mr-2" />
                                Importar Configuración
                              </span>
                            </Button>
                            <input
                              type="file"
                              accept=".json"
                              onChange={handleImportData}
                              className="hidden"
                            />
                          </label>
                        </div>
                      </div>

                      {/* Danger Zone */}
                      <div className="p-4 bg-red-500/10 rounded-lg border border-red-500/30">
                        <div className="flex items-start gap-3">
                          <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5" />
                          <div className="flex-1">
                            <h4 className="text-sm font-medium text-white">Zona de Peligro</h4>
                            <p className="text-sm text-gray-400 mt-1">
                              Estas acciones son permanentes y no se pueden deshacer.
                            </p>
                            <div className="flex gap-2 mt-3">
                              <Button variant="outline" size="sm" className="text-red-400 border-red-400 hover:bg-red-500/10">
                                <Trash2 className="w-4 h-4 mr-2" />
                                Eliminar todos los datos
                              </Button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>
            </AnimatePresence>
          </TabsContent>
        </Tabs>
      </motion.div>
    </motion.div>
  )
}