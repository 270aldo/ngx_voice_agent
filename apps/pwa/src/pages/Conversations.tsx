import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  MessageSquare, 
  Users, 
  Clock, 
  PhoneCall,
  Mail,
  Globe,
  Search,
  Filter,
  ChevronRight,
  Circle,
  AlertCircle,
  CheckCircle,
  XCircle,
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Eye,
  Send
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { ScrollArea } from '../components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { conversationsApi } from '../services/api'
import webSocketService, { ConversationUpdate } from '../services/websocket'
import { useToast } from '../hooks/use-toast'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'

interface Conversation {
  id: string
  customer: {
    name: string
    email?: string
    phone?: string
    avatar?: string
  }
  status: 'active' | 'waiting' | 'ended'
  channel: 'voice' | 'chat' | 'email'
  startedAt: Date
  lastMessage?: {
    text: string
    timestamp: Date
    isAgent: boolean
  }
  metrics: {
    duration: number
    messageCount: number
    sentiment: 'positive' | 'neutral' | 'negative'
  }
  agent?: {
    name: string
    status: 'speaking' | 'listening' | 'typing'
  }
}

interface Message {
  id: string
  text: string
  timestamp: Date
  isAgent: boolean
  metadata?: {
    sentiment?: 'positive' | 'neutral' | 'negative'
    intent?: string
    confidence?: number
  }
}

// Mock data for development
const mockConversations: Conversation[] = [
  {
    id: '1',
    customer: {
      name: 'María García',
      email: 'maria@example.com',
      phone: '+52 555 1234',
    },
    status: 'active',
    channel: 'voice',
    startedAt: new Date(Date.now() - 5 * 60 * 1000),
    lastMessage: {
      text: 'Estoy interesada en el plan Pro para mi gimnasio',
      timestamp: new Date(),
      isAgent: false
    },
    metrics: {
      duration: 300,
      messageCount: 12,
      sentiment: 'positive'
    },
    agent: {
      name: 'NGX Agent',
      status: 'speaking'
    }
  },
  {
    id: '2',
    customer: {
      name: 'Carlos Mendoza',
      email: 'carlos@fitnesscenter.mx',
    },
    status: 'waiting',
    channel: 'chat',
    startedAt: new Date(Date.now() - 2 * 60 * 1000),
    lastMessage: {
      text: '¿Cuánto cuesta la integración con mi CRM actual?',
      timestamp: new Date(Date.now() - 30 * 1000),
      isAgent: false
    },
    metrics: {
      duration: 120,
      messageCount: 5,
      sentiment: 'neutral'
    }
  },
]

const mockMessages: Message[] = [
  {
    id: '1',
    text: 'Hola, bienvenida a NGX. Soy tu asistente especializado en soluciones para gimnasios. ¿En qué puedo ayudarte hoy?',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    isAgent: true
  },
  {
    id: '2',
    text: 'Hola! Tengo un gimnasio con 200 miembros y estoy buscando automatizar mi proceso de ventas',
    timestamp: new Date(Date.now() - 4 * 60 * 1000),
    isAgent: false,
    metadata: {
      sentiment: 'positive',
      intent: 'information_request'
    }
  },
  {
    id: '3',
    text: 'Excelente María! NGX es perfecto para gimnasios de tu tamaño. Nuestros clientes típicamente ven un aumento del 47% en conversiones. ¿Qué aspectos de tu proceso de ventas te gustaría mejorar más?',
    timestamp: new Date(Date.now() - 3 * 60 * 1000),
    isAgent: true
  },
  {
    id: '4',
    text: 'Principalmente quiero automatizar el seguimiento de leads y las llamadas de ventas. Pierdo muchas oportunidades por falta de tiempo',
    timestamp: new Date(Date.now() - 2 * 60 * 1000),
    isAgent: false,
    metadata: {
      sentiment: 'neutral',
      intent: 'problem_description'
    }
  },
  {
    id: '5',
    text: 'Entiendo perfectamente. NGX puede hacer llamadas automáticas a tus leads, calificarlos y agendar citas directamente en tu calendario. Estoy interesada en el plan Pro para mi gimnasio',
    timestamp: new Date(),
    isAgent: false,
    metadata: {
      sentiment: 'positive',
      intent: 'purchase_interest',
      confidence: 0.92
    }
  }
]

export function Conversations() {
  const [conversations, setConversations] = useState<Conversation[]>(mockConversations)
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'waiting' | 'ended'>('all')
  const [loading, setLoading] = useState(false)
  const [messageInput, setMessageInput] = useState('')
  const { toast } = useToast()

  useEffect(() => {
    // Load conversations
    loadConversations()

    // WebSocket handlers
    const handleConversationUpdate = (update: ConversationUpdate) => {
      if (update.event_type === 'started') {
        // Add new conversation
        const newConversation: Conversation = {
          id: update.conversation_id,
          customer: update.data.customer,
          status: 'active',
          channel: 'chat',
          startedAt: new Date(update.timestamp),
          metrics: {
            duration: 0,
            messageCount: 0,
            sentiment: 'neutral'
          }
        }
        setConversations(prev => [newConversation, ...prev])
      } else if (update.event_type === 'message') {
        // Update conversation with new message
        setConversations(prev => prev.map(conv => {
          if (conv.id === update.conversation_id) {
            return {
              ...conv,
              lastMessage: {
                text: update.data.message.text,
                timestamp: new Date(update.timestamp),
                isAgent: update.data.is_agent
              },
              metrics: {
                ...conv.metrics,
                messageCount: conv.metrics.messageCount + 1
              }
            }
          }
          return conv
        }))

        // If this conversation is selected, add message to messages list
        if (selectedConversation?.id === update.conversation_id) {
          const newMessage: Message = {
            id: Date.now().toString(),
            text: update.data.message.text,
            timestamp: new Date(update.timestamp),
            isAgent: update.data.is_agent,
            metadata: update.data.message.metadata
          }
          setMessages(prev => [...prev, newMessage])
        }
      } else if (update.event_type === 'ended') {
        // Update conversation status
        setConversations(prev => prev.map(conv => {
          if (conv.id === update.conversation_id) {
            return { ...conv, status: 'ended' }
          }
          return conv
        }))
      }
    }

    webSocketService.on('conversation_update', handleConversationUpdate)

    return () => {
      webSocketService.off('conversation_update', handleConversationUpdate)
    }
  }, [selectedConversation])

  const loadConversations = async () => {
    setLoading(true)
    try {
      const response = await conversationsApi.list({ status: filterStatus === 'all' ? undefined : filterStatus })
      if (response.data) {
        setConversations(response.data)
      }
    } catch (error) {
      console.error('Error loading conversations:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadMessages = async (conversationId: string) => {
    try {
      const response = await conversationsApi.getMessages(conversationId)
      if (response.data) {
        setMessages(response.data)
      } else {
        // Use mock messages for now
        setMessages(mockMessages)
      }
    } catch (error) {
      console.error('Error loading messages:', error)
      // Use mock messages as fallback
      setMessages(mockMessages)
    }
  }

  const handleConversationSelect = (conversation: Conversation) => {
    setSelectedConversation(conversation)
    loadMessages(conversation.id)
  }

  const handleSendMessage = async () => {
    if (!messageInput.trim() || !selectedConversation) return

    try {
      const response = await conversationsApi.sendMessage(selectedConversation.id, messageInput)
      if (response.data) {
        // Message will be added via WebSocket
        setMessageInput('')
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudo enviar el mensaje",
        variant: "destructive"
      })
    }
  }

  const getStatusIcon = (status: Conversation['status']) => {
    switch (status) {
      case 'active':
        return <Circle className="w-3 h-3 fill-green-500 text-green-500" />
      case 'waiting':
        return <AlertCircle className="w-3 h-3 text-yellow-500" />
      case 'ended':
        return <CheckCircle className="w-3 h-3 text-gray-500" />
    }
  }

  const getChannelIcon = (channel: Conversation['channel']) => {
    switch (channel) {
      case 'voice':
        return <PhoneCall className="w-4 h-4" />
      case 'chat':
        return <MessageSquare className="w-4 h-4" />
      case 'email':
        return <Mail className="w-4 h-4" />
    }
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return 'text-green-500'
      case 'negative':
        return 'text-red-500'
      default:
        return 'text-gray-400'
    }
  }

  const filteredConversations = conversations.filter(conv => {
    const matchesSearch = conv.customer.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         conv.customer.email?.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesFilter = filterStatus === 'all' || conv.status === filterStatus
    return matchesSearch && matchesFilter
  })

  return (
    <div className="h-full flex flex-col lg:flex-row gap-4 md:gap-6">
      {/* Conversations List */}
      <div className="w-full lg:w-96 flex flex-col">
        <div className="mb-6">
          <h1 className="text-xl md:text-2xl font-heading text-white mb-4">Conversaciones</h1>
          
          {/* Search and Filter */}
          <div className="space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Buscar por nombre o email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            
            <Tabs value={filterStatus} onValueChange={(v) => setFilterStatus(v as any)}>
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="all">Todas</TabsTrigger>
                <TabsTrigger value="active">Activas</TabsTrigger>
                <TabsTrigger value="waiting">Esperando</TabsTrigger>
                <TabsTrigger value="ended">Finalizadas</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>

        {/* Conversations List */}
        <Card className="flex-1 overflow-hidden max-h-[50vh] lg:max-h-full">
          <ScrollArea className="h-full">
            <div className="p-2">
              <AnimatePresence>
                {filteredConversations.map((conversation) => (
                  <motion.div
                    key={conversation.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div
                      className={`p-4 rounded-lg cursor-pointer transition-colors mb-2 ${
                        selectedConversation?.id === conversation.id
                          ? 'bg-electric-violet/20 border border-electric-violet/50'
                          : 'bg-card hover:bg-card-hover'
                      }`}
                      onClick={() => handleConversationSelect(conversation)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-electric-violet to-deep-purple flex items-center justify-center text-white font-medium">
                            {conversation.customer.name.charAt(0)}
                          </div>
                          <div>
                            <h3 className="font-medium text-white">{conversation.customer.name}</h3>
                            <p className="text-sm text-gray-400">{conversation.customer.email}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(conversation.status)}
                          {getChannelIcon(conversation.channel)}
                        </div>
                      </div>
                      
                      {conversation.lastMessage && (
                        <p className="text-sm text-gray-300 mb-2 line-clamp-2">
                          {conversation.lastMessage.text}
                        </p>
                      )}
                      
                      <div className="flex items-center justify-between text-xs text-gray-400">
                        <span>{formatDistanceToNow(conversation.startedAt, { locale: es, addSuffix: true })}</span>
                        <div className="flex items-center gap-3">
                          <span className="flex items-center gap-1">
                            <MessageSquare className="w-3 h-3" />
                            {conversation.metrics.messageCount}
                          </span>
                          <span className={getSentimentColor(conversation.metrics.sentiment)}>
                            {conversation.metrics.sentiment === 'positive' ? '😊' : conversation.metrics.sentiment === 'negative' ? '😟' : '😐'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </ScrollArea>
        </Card>
      </div>

      {/* Conversation Detail */}
      {selectedConversation ? (
        <Card className="flex-1 flex flex-col">
          {/* Header */}
          <CardHeader className="border-b border-white/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-electric-violet to-deep-purple flex items-center justify-center text-white font-medium">
                  {selectedConversation.customer.name.charAt(0)}
                </div>
                <div>
                  <CardTitle className="text-base md:text-lg">{selectedConversation.customer.name}</CardTitle>
                  <div className="flex items-center gap-4 text-sm text-gray-400">
                    {selectedConversation.customer.email && <span>{selectedConversation.customer.email}</span>}
                    {selectedConversation.customer.phone && <span>{selectedConversation.customer.phone}</span>}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {selectedConversation.channel === 'voice' && (
                  <>
                    <Button size="sm" variant="ghost">
                      <MicOff className="w-4 h-4" />
                    </Button>
                    <Button size="sm" variant="ghost" className="text-red-500">
                      <PhoneOff className="w-4 h-4" />
                    </Button>
                  </>
                )}
                <Button size="sm" variant="ghost">
                  <Eye className="w-4 h-4" />
                  <span className="ml-2">Ver perfil</span>
                </Button>
              </div>
            </div>
          </CardHeader>

          {/* Messages */}
          <CardContent className="flex-1 p-0">
            <ScrollArea className="h-full p-6">
              <div className="space-y-4">
                <AnimatePresence>
                  {messages.map((message) => (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                      className={`flex ${message.isAgent ? 'justify-start' : 'justify-end'}`}
                    >
                      <div className={`max-w-[70%] ${message.isAgent ? 'order-2' : 'order-1'}`}>
                        <div
                          className={`p-4 rounded-2xl ${
                            message.isAgent
                              ? 'bg-glass text-white'
                              : 'bg-electric-violet text-white'
                          }`}
                        >
                          <p className="text-sm">{message.text}</p>
                          {message.metadata && (
                            <div className="mt-2 flex items-center gap-2 text-xs opacity-70">
                              {message.metadata.intent && (
                                <Badge variant="secondary" className="text-xs">
                                  {message.metadata.intent}
                                </Badge>
                              )}
                              {message.metadata.confidence && (
                                <span>Confianza: {Math.round(message.metadata.confidence * 100)}%</span>
                              )}
                            </div>
                          )}
                        </div>
                        <p className="text-xs text-gray-400 mt-1 px-2">
                          {formatDistanceToNow(message.timestamp, { locale: es, addSuffix: true })}
                        </p>
                      </div>
                      {message.isAgent && (
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-electric-violet to-deep-purple flex items-center justify-center text-white text-xs font-bold order-1 mr-3">
                          AI
                        </div>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </ScrollArea>
          </CardContent>

          {/* Input */}
          {selectedConversation.status === 'active' && (
            <div className="p-4 border-t border-white/10">
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Escribe un mensaje..."
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  className="flex-1"
                />
                <Button 
                  onClick={handleSendMessage}
                  size="icon"
                  className="bg-electric-violet hover:bg-electric-violet/80"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </Card>
      ) : (
        <Card className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <MessageSquare className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-400">Selecciona una conversación para ver los detalles</p>
          </div>
        </Card>
      )}
    </div>
  )
}