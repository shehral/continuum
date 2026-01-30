import { cn } from "@/lib/utils"

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-slate-700/50", className)}
      {...props}
    />
  )
}

/**
 * Skeleton for decision card lists
 */
function DecisionCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "rounded-lg border border-white/[0.06] bg-white/[0.03] p-4 space-y-3",
        className
      )}
    >
      {/* Title and badge row */}
      <div className="flex items-start justify-between gap-3">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-5 w-12 shrink-0" />
      </div>
      {/* Description */}
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
      {/* Entity badges */}
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-6 w-20 rounded-full" />
        <Skeleton className="h-6 w-24 rounded-full" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
    </div>
  )
}

/**
 * Skeleton for stat cards on dashboard
 */
function StatCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "rounded-lg border border-white/[0.06] bg-white/[0.03] p-6 space-y-3",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <Skeleton className="h-6 w-6 rounded" />
        <Skeleton className="h-4 w-24" />
      </div>
      <Skeleton className="h-10 w-16" />
      <Skeleton className="h-3 w-32" />
    </div>
  )
}

/**
 * Skeleton for graph loading state
 */
function GraphSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "h-full w-full flex items-center justify-center bg-slate-900/50",
        className
      )}
    >
      <div className="text-center space-y-4">
        {/* Animated graph representation */}
        <div className="relative mx-auto h-32 w-48">
          {/* Nodes */}
          <Skeleton className="absolute top-0 left-1/2 -translate-x-1/2 h-8 w-24 rounded-lg" />
          <Skeleton className="absolute top-16 left-0 h-6 w-16 rounded-full" />
          <Skeleton className="absolute top-20 right-0 h-6 w-14 rounded-full" />
          <Skeleton className="absolute bottom-0 left-1/4 h-6 w-18 rounded-full" />
          {/* Connection lines (using gradient borders) */}
          <div className="absolute top-8 left-1/2 h-8 w-px bg-gradient-to-b from-slate-600 to-slate-700" />
          <div className="absolute top-12 left-1/4 h-6 w-px bg-gradient-to-b from-slate-600 to-slate-700 rotate-45" />
          <div className="absolute top-12 right-1/4 h-6 w-px bg-gradient-to-b from-slate-600 to-slate-700 -rotate-45" />
        </div>
        <Skeleton className="h-4 w-40 mx-auto" />
      </div>
    </div>
  )
}

/**
 * List of skeleton cards
 */
function DecisionListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-4" role="status" aria-label="Loading decisions">
      {Array.from({ length: count }).map((_, i) => (
        <DecisionCardSkeleton key={i} />
      ))}
      <span className="sr-only">Loading decision list...</span>
    </div>
  )
}

export {
  Skeleton,
  DecisionCardSkeleton,
  StatCardSkeleton,
  GraphSkeleton,
  DecisionListSkeleton,
}
