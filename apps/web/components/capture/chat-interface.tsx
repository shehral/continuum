"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { type CaptureMessage, type Entity } from "@/lib/api"
import { cn } from "@/lib/utils"

interface ChatInterfaceProps {
  messages: CaptureMessage[]
  onSendMessage: (content: string) => Promise<void>
  isLoading: boolean
  suggestedEntities?: Entity[]
  onLinkEntity?: (entity: Entity) => void
}

function MessageBubble({ message, isNew = false }: { message: CaptureMessage; isNew?: boolean }) {
  const isUser = message.role === "user"

  return (
    <div
      className={cn(
        "flex gap-3 mb-4",
        isUser ? "flex-row-reverse" : "flex-row",
        isNew && "animate-in fade-in slide-in-from-bottom-2 duration-300"
      )}
    >
      <Avatar className="h-8 w-8 shrink-0" aria-hidden="true">
        <AvatarFallback className={cn(
          "text-sm font-medium",
          isUser
            ? "bg-gradient-to-br from-cyan-500 to-teal-400 text-slate-900"
            : "bg-purple-500/20 text-purple-400"
        )}>
          {isUser ? "U" : "🤖"}
        </AvatarFallback>
      </Avatar>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3",
          isUser
            ? "bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900"
            : "bg-white/[0.05] border border-white/[0.08] text-slate-200"
        )}
      >
        <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
        {message.extracted_entities && message.extracted_entities.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {message.extracted_entities.map((entity) => (
              <Badge
                key={entity.id}
                variant="outline"
                className={cn(
                  "text-xs",
                  isUser
                    ? "bg-white/20 border-white/30 text-slate-900"
                    : "bg-purple-500/10 border-purple-500/30 text-purple-400"
                )}
              >
                {entity.name}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Typing indicator with animated dots
function TypingIndicator() {
  return (
    <div className="flex gap-3 mb-4 animate-in fade-in duration-300" role="status" aria-label="AI is typing">
      <Avatar className="h-8 w-8 shrink-0" aria-hidden="true">
        <AvatarFallback className="bg-purple-500/20 text-purple-400">🤖</AvatarFallback>
      </Avatar>
      <div className="bg-white/[0.05] border border-white/[0.08] rounded-2xl px-4 py-3">
        <div className="flex gap-1" aria-hidden="true">
          <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="sr-only">AI is typing a response</span>
      </div>
    </div>
  )
}

export function ChatInterface({
  messages,
  onSendMessage,
  isLoading,
  suggestedEntities,
  onLinkEntity,
}: ChatInterfaceProps) {
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const message = input.trim()
    setInput("")
    await onSendMessage(message)
    inputRef.current?.focus()
  }

  return (
    <div className="flex flex-col h-full bg-slate-900/50">
      {/* Messages */}
      <ScrollArea ref={scrollRef} className="flex-1 p-6" role="log" aria-label="Chat messages" aria-live="polite">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center">
            <div className="animate-in fade-in duration-500">
              <div className="mx-auto mb-4 h-16 w-16 rounded-2xl bg-purple-500/10 flex items-center justify-center">
                <span className="text-3xl">💬</span>
              </div>
              <p className="text-slate-300 mb-2 font-medium">
                Start a conversation to capture knowledge
              </p>
              <p className="text-sm text-slate-500">
                I&apos;ll help you document decisions, context, and rationale
              </p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <MessageBubble
              key={message.id}
              message={message}
              isNew={index === messages.length - 1}
            />
          ))
        )}
        {isLoading && <TypingIndicator />}
      </ScrollArea>

      {/* Entity suggestions */}
      {suggestedEntities && suggestedEntities.length > 0 && (
        <div className="px-6 py-3 border-t border-white/[0.06] bg-white/[0.02]">
          <p className="text-xs text-slate-500 mb-2">
            Extracted entities:
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestedEntities.map((entity) => (
              <Badge
                key={entity.id}
                variant="outline"
                className="cursor-pointer bg-purple-500/10 border-purple-500/30 text-purple-400 hover:bg-purple-500/20 hover:scale-105 transition-all"
                onClick={() => onLinkEntity?.(entity)}
              >
                {entity.name}
                <span className="ml-1 opacity-60">({entity.type})</span>
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-white/[0.06] bg-slate-900/80 backdrop-blur-xl">
        <div className="flex gap-3">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading}
            aria-label="Type your message"
            className="flex-1 bg-white/[0.05] border-white/[0.1] text-slate-200 placeholder:text-slate-500 focus:border-cyan-500/50 focus:ring-cyan-500/20"
          />
          <Button
            type="submit"
            disabled={!input.trim() || isLoading}
            aria-label={isLoading ? "Sending message" : "Send message"}
            className="bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 hover:shadow-[0_0_20px_rgba(34,211,238,0.3)] transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
