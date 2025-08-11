import React from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus, LucideIcon } from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  change?: number
  changeLabel?: string
  icon: LucideIcon
  iconColor?: string
  loading?: boolean
}

export function MetricCard({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  iconColor = 'text-electric-violet',
  loading = false
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (!change) return null
    if (change > 0) return <TrendingUp className="w-4 h-4" />
    if (change < 0) return <TrendingDown className="w-4 h-4" />
    return <Minus className="w-4 h-4" />
  }

  const getTrendColor = () => {
    if (!change) return 'text-gray-400'
    if (change > 0) return 'text-green-500'
    if (change < 0) return 'text-red-500'
    return 'text-gray-400'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="group relative overflow-hidden">
        <CardContent className="p-6">
          {/* Background Glow Effect */}
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-electric-violet/10 rounded-full blur-3xl group-hover:bg-electric-violet/20 transition-all duration-500" />
          
          <div className="relative">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="p-2 bg-black/30 rounded-lg border border-deep-purple/20">
                <Icon className={cn("w-5 h-5", iconColor)} />
              </div>
              
              {change !== undefined && (
                <div className={cn("flex items-center space-x-1 text-sm", getTrendColor())}>
                  {getTrendIcon()}
                  <span>{Math.abs(change)}%</span>
                </div>
              )}
            </div>

            {/* Content */}
            <div>
              <p className="text-sm text-gray-400 mb-1">{title}</p>
              
              {loading ? (
                <div className="h-8 bg-deep-purple/20 rounded animate-pulse" />
              ) : (
                <motion.p
                  className="text-3xl font-heading font-bold"
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
                >
                  {value}
                </motion.p>
              )}
              
              {changeLabel && (
                <p className="text-xs text-gray-500 mt-2">{changeLabel}</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}