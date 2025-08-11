import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Settings as SettingsIcon } from 'lucide-react'

export function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-heading text-white">Configuración</h1>
        <p className="text-gray-400 mt-1">
          Gestiona tu cuenta y preferencias del sistema
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <SettingsIcon className="w-5 h-5 text-electric-violet" />
            <span>Configuración General</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-400">
            Las opciones de configuración aparecerán aquí...
          </p>
        </CardContent>
      </Card>
    </div>
  )
}