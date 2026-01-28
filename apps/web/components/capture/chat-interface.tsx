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

function MessageBubble({ message }: { message: CaptureMessage }) {
  const isUser = message.role === "user"

  return (
    <div
      className={cn(
        "flex gap-3 mb-4",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback className={isUser ? "bg-primary text-primary-foreground" : "bg-muted"}>
          {isUser ? "U" : "C"}
        </AvatarFallback>
      </Avatar>
      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-2",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        )}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        {message.extracted_entities && message.extracted_entities.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {message.extracted_entities.map((entity) => (
              <Badge
                key={entity.id}
                variant={isUser ? "secondary" : "outline"}
                className="text-xs"
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
    <div className="flex flex-col h-full">
      {/* Messages */}
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center">
            <div>
              <p className="text-muted-foreground mb-2">
                Start a conversation to capture knowledge
              </p>
              <p className="text-sm text-muted-foreground">
                I&apos;ll help you document decisions, context, and rationale
              </p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}
        {isLoading && (
          <div className="flex gap-3 mb-4">
            <Avatar className="h-8 w-8 shrink-0">
              <AvatarFallback className="bg-muted">C</AvatarFallback>
            </Avatar>
            <div className="bg-muted rounded-lg px-4 py-2">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Entity suggestions */}
      {suggestedEntities && suggestedEntities.length > 0 && (
        <div className="px-4 py-2 border-t bg-muted/50">
          <p className="text-xs text-muted-foreground mb-2">
            Suggested entities to link:
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestedEntities.map((entity) => (
              <Badge
                key={entity.id}
                variant="outline"
                className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
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
      <form onSubmit={handleSubmit} className="p-4 border-t bg-background">
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={!input.trim() || isLoading}>
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
