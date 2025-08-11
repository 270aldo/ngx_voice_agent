import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Header } from './Header'
import { AIAssistant } from '../chat/AIAssistant'
import { MobileNavigation } from '../mobile/MobileNavigation'
import { cn } from '@/lib/utils'
import { useIsDesktop } from '@/hooks/use-media-query'

export function LayoutNGX() {
  const isDesktop = useIsDesktop()
  const [isAssistantExpanded, setIsAssistantExpanded] = useState(false) // Default to closed on mobile

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Header */}
      <Header />
      
      {/* Main Content Area */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Main Content */}
        <main className={cn(
          "flex-1 transition-all duration-300",
          isAssistantExpanded ? "lg:mr-96" : "mr-0"
        )}>
          <div className="h-full overflow-y-auto">
            <div className="container mx-auto p-4 md:p-6">
              <Outlet />
            </div>
          </div>
        </main>

        {/* AI Assistant Sidebar */}
        <motion.aside
          initial={{ x: 0 }}
          animate={{ x: isAssistantExpanded ? 0 : (isDesktop ? 384 : window.innerWidth) }}
          transition={{ type: "spring", damping: 30, stiffness: 300 }}
          className="fixed right-0 top-16 bottom-0 w-full lg:w-96 bg-black/95 lg:bg-black/30 backdrop-blur-xl border-l border-deep-purple/20 z-40"
        >
          {/* Toggle Button */}
          <button
            onClick={() => setIsAssistantExpanded(!isAssistantExpanded)}
            className={cn(
              "absolute -left-8 top-1/2 -translate-y-1/2",
              "w-8 h-16 bg-deep-purple/50 hover:bg-deep-purple/70",
              "border border-deep-purple/30 rounded-l-lg",
              "flex items-center justify-center transition-all duration-200",
              "hover:shadow-lg hover:shadow-deep-purple/25"
            )}
          >
            <svg
              className={cn(
                "w-4 h-4 text-white transition-transform duration-200",
                isAssistantExpanded ? "rotate-0" : "rotate-180"
              )}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>

          {/* AI Assistant Content */}
          <AIAssistant />
        </motion.aside>
      </div>

      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none">
        {/* Grid Pattern */}
        <div 
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `linear-gradient(rgba(139, 92, 246, 0.1) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(139, 92, 246, 0.1) 1px, transparent 1px)`,
            backgroundSize: '50px 50px'
          }}
        />
        
        {/* Gradient Orbs */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-electric-violet/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-deep-purple/10 rounded-full blur-3xl" />
      </div>

      {/* Mobile Navigation */}
      <MobileNavigation />
    </div>
  )
}