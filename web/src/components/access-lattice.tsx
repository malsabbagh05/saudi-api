import { cn } from "@/lib/utils";
import { ACCESS_LEVELS, type AccessLevel } from "@/lib/api";

/**
 * The carved access lattice: five apertures in a rawashin screen. Light comes through as
 * many apertures as the API is open: all five for open access, one for restricted. In
 * right-to-left pages the screen mirrors, so the scale still starts at the reading edge.
 */
export function AccessLattice({
  level,
  label,
  lit = false,
  className,
}: {
  level: AccessLevel;
  label: string;
  /** The access filter selects this level: the screen glows. */
  lit?: boolean;
  className?: string;
}) {
  const open = ACCESS_LEVELS.length - ACCESS_LEVELS.indexOf(level);
  return (
    <svg
      role="img"
      aria-label={label}
      viewBox="0 0 56 14"
      className={cn(
        "h-3.5 w-14 shrink-0 rtl:-scale-x-100 transition-[filter] duration-200",
        lit && "drop-shadow-[0_0_4px_var(--lattice-open)]",
        className,
      )}
    >
      <title>{label}</title>
      <rect
        x="0.5"
        y="0.5"
        width="55"
        height="13"
        rx="1"
        className="fill-none stroke-teak/40"
        strokeWidth="1"
      />
      {ACCESS_LEVELS.map((_, index) => (
        <rect
          key={index}
          x={6 + index * 11 - 3}
          y={7 - 3}
          width="6"
          height="6"
          transform={`rotate(45 ${6 + index * 11} 7)`}
          className={index < open ? "fill-lattice-open" : "fill-lattice-shut"}
        />
      ))}
    </svg>
  );
}

export function accessPosition(level: AccessLevel): number {
  return ACCESS_LEVELS.indexOf(level) + 1;
}
