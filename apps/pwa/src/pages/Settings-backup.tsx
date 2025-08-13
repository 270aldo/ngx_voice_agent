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
    const hasChanges = JSON.stringify(settings) !== JSON.stringify(defaultSettings)
    setUnsavedChanges(hasChanges)
  }, [settings])

  const loadUserSettings = async () => {
    setLoading(true)
    try {
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
        // Merge API data with current settings
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
      setUser({
        ...getUser()!,
        email: settings.profile.email,
        full_name: settings.profile.full_name
      })

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
      // Create a data export
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

          {/* More tabs will be added in the next section... */}
        </Tabs>
      </motion.div>
    </motion.div>
  )
}