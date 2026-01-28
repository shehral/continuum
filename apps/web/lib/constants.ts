/**
 * Shared constants used across the application.
 */

/**
 * Entity type styling with icons and Tailwind CSS classes.
 * Used for consistent visual differentiation of entity types.
 */
export const entityStyles: Record<
  string,
  { icon: string; bg: string; text: string; border: string }
> = {
  technology: {
    icon: "🔧",
    bg: "bg-blue-500/10",
    text: "text-blue-400",
    border: "border-blue-500/30",
  },
  concept: {
    icon: "💡",
    bg: "bg-purple-500/10",
    text: "text-purple-400",
    border: "border-purple-500/30",
  },
  system: {
    icon: "⚙️",
    bg: "bg-green-500/10",
    text: "text-green-400",
    border: "border-green-500/30",
  },
  pattern: {
    icon: "🧩",
    bg: "bg-orange-500/10",
    text: "text-orange-400",
    border: "border-orange-500/30",
  },
  person: {
    icon: "👤",
    bg: "bg-pink-500/10",
    text: "text-pink-400",
    border: "border-pink-500/30",
  },
  organization: {
    icon: "🏢",
    bg: "bg-indigo-500/10",
    text: "text-indigo-400",
    border: "border-indigo-500/30",
  },
}

/**
 * Get styling for an entity type, defaulting to concept style.
 */
export const getEntityStyle = (type: string) =>
  entityStyles[type] || entityStyles.concept
