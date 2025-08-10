import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Sparkles, TrendingUp, AlertCircle, BarChart } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '../ui/input'
import { Button } from '../ui/button'
import { Card } from '../ui/card'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  data?: any
}

const quickQueries = [
  { icon: TrendingUp, text: "Conversiones de hoy", query: "Muéstrame las conversiones de hoy" },
  { icon: AlertCircle, text: "Objeciones comunes", query: "¿Cuáles son las objeciones más comunes?" },
  { icon: BarChart, text: "Comparar semanas", query: "Compara esta semana con la anterior" },
]

export function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '¡Hola! Soy tu asistente de analytics NGX. Puedo ayudarte a entender tus métricas, conversaciones y rendimiento. ¿Qué te gustaría saber?',
      timestamp: new Date(),
    }
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsTyping(true)

    // Simulate AI response
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Analizando tu consulta sobre "${input}". Aquí están los resultados...`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMessage])
      setIsTyping(false)
    }, 1500)
  }

  const handleQuickQuery = (query: string) => {
    setInput(query)
    handleSend()
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-deep-purple/20">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-electric-violet/20 rounded-lg">
            <Sparkles className="w-5 h-5 text-electric-violet" />
          </div>
          <div>
            <h2 className="font-heading text-lg">AI Assistant</h2>
            <p className="text-xs text-gray-400">Powered by NGX Intelligence</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence initial={false}>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className={cn(
                "flex",
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              <div
                className={cn(
                  "max-w-[80%] rounded-lg p-3",
                  message.role === 'user'
                    ? 'bg-electric-violet text-white'
                    : 'bg-black/50 border border-deep-purple/20'
                )}
              >
                <p className="text-sm">{message.content}</p>
                <p className="text-xs mt-1 opacity-50">
                  {message.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isTyping && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="bg-black/50 border border-deep-purple/20 rounded-lg p-3">
              <div className="loading-dots-ngx">
                <div></div>
                <div></div>
                <div></div>
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Queries */}
      {messages.length === 1 && (
        <div className="p-4 border-t border-deep-purple/20">
          <p className="text-xs text-gray-400 mb-2">Consultas rápidas:</p>
          <div className="space-y-2">
            {quickQueries.map((query, index) => (
              <button
                key={index}
                onClick={() => handleQuickQuery(query.query)}
                className="w-full text-left p-2 rounded-lg bg-black/30 border border-deep-purple/20 hover:border-electric-violet/30 transition-all duration-200 flex items-center space-x-2"
              >
                <query.icon className="w-4 h-4 text-electric-violet" />
                <span className="text-sm">{query.text}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-deep-purple/20">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex space-x-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Pregunta sobre tus métricas..."
            className="flex-1"
          />
          <Button type="submit" size="icon">
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}