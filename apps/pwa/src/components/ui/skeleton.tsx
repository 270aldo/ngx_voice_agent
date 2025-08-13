import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'pulse' | 'wave'
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'full'
}

const skeletonVariants = {
  default: "bg-gray-600 animate-pulse",
  pulse: "bg-gradient-to-r from-gray-600 via-gray-500 to-gray-600 bg-[length:200%_100%] animate-[shimmer_2s_infinite]",
  wave: "bg-gray-600 relative overflow-hidden before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_infinite] before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent"
}

const roundedVariants = {
  none: '',
  sm: 'rounded-sm',
  md: 'rounded',
  lg: 'rounded-lg',
  full: 'rounded-full'
}

export function Skeleton({ 
  className, 
  variant = 'default', 
  rounded = 'md',
  ...props 
}: SkeletonProps) {
  return (
    <div
      className={cn(
        skeletonVariants[variant],
        roundedVariants[rounded],
        className
      )}
      {...props}
    />
  )
}

// Preset skeleton components
export function SkeletonText({ 
  lines = 1, 
  className,
  ...props 
}: { lines?: number } & SkeletonProps) {
  return (
    <div className={cn("space-y-2", className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            "h-4",
            i === lines - 1 && lines > 1 ? "w-3/4" : "w-full"
          )}
          {...props}
        />
      ))}
    </div>
  )
}

export function SkeletonCard({ className, ...props }: SkeletonProps) {
  return (
    <div className={cn("p-6 space-y-4 bg-glass border border-white/10 rounded-lg", className)}>
      <div className="flex items-center space-x-4">
        <Skeleton className="h-12 w-12" rounded="full" {...props} />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-4 w-1/2" {...props} />
          <Skeleton className="h-3 w-3/4" {...props} />
        </div>
      </div>
      <SkeletonText lines={3} {...props} />
    </div>
  )
}

export function SkeletonTable({ 
  rows = 5, 
  columns = 4, 
  className,
  ...props 
}: { rows?: number; columns?: number } & SkeletonProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {/* Header */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-full" {...props} />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div 
          key={rowIndex} 
          className="grid gap-4" 
          style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton 
              key={colIndex} 
              className={cn(
                "h-3",
                colIndex === 0 ? "w-full" : "w-3/4"
              )} 
              {...props} 
            />
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonChart({ className, ...props }: SkeletonProps) {
  return (
    <div className={cn("space-y-4", className)}>
      {/* Chart area */}
      <div className="h-64 flex items-end justify-between space-x-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton
            key={i}
            className="w-8"
            style={{ height: `${Math.random() * 80 + 20}%` }}
            {...props}
          />
        ))}
      </div>
      {/* Legend */}
      <div className="flex justify-center space-x-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center space-x-2">
            <Skeleton className="h-3 w-3" rounded="full" {...props} />
            <Skeleton className="h-3 w-16" {...props} />
          </div>
        ))}
      </div>
    </div>
  )
}

// Animated skeleton with stagger effect
export function SkeletonGroup({ 
  children, 
  stagger = 0.1,
  className 
}: { 
  children: React.ReactNode
  stagger?: number
  className?: string 
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: {
            staggerChildren: stagger
          }
        }
      }}
    >
      {React.Children.map(children, (child, index) => (
        <motion.div
          key={index}
          variants={{
            hidden: { opacity: 0, y: 20 },
            visible: { opacity: 1, y: 0 }
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  )
}