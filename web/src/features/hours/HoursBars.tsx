/** Engineering hours lost per week for each design, split into where they go. */
import { motion } from "framer-motion";
import { NAME, one, tone } from "../../shared/format";
import type { DesignSummary, Parts } from "../../shared/types";
import { motionTokens } from "../../theme/motion";

export const PARTS: { key: keyof Parts; label: string; cls: string }[] = [
  { key: "waiting_for_ci", label: "Waiting for CI", cls: "bg-part1" },
  { key: "pages", label: "Pages", cls: "bg-part2" },
  { key: "flaky_reds", label: "Flaky red builds", cls: "bg-part3" },
  { key: "change_review", label: "Reviewing changes", cls: "bg-part4" },
  { key: "job_repairs", label: "Repairing job runs", cls: "bg-part5" },
  { key: "broken_main", label: "Broken main", cls: "bg-part6" },
];

export function HoursBars({ rows }: { rows: [string, DesignSummary][] }) {
  const max = Math.max(...rows.map(([, d]) => d.engineer_hours_per_week));
  return (
    <figure className="flex flex-col gap-4">
      <figcaption className="flex flex-wrap gap-x-5 gap-y-2 text-small text-copy sm:pl-[14rem]">
        {PARTS.map((p) => (
          <span key={p.key} className="inline-flex items-center gap-2">
            <span className={`inline-block h-swatch w-swatch rounded-soft ${p.cls}`} aria-hidden />
            {p.label}
          </span>
        ))}
      </figcaption>
      <ul className="flex flex-col gap-2">
        {rows.map(([name, d], i) => {
          const total = d.engineer_hours_per_week;
          return (
            <li key={name} className="grid grid-cols-1 items-center gap-1 sm:grid-cols-[13rem_1fr] sm:gap-4">
              <span className={`text-small font-semibold sm:text-right ${tone(name)}`}>{NAME[name] ?? d.label}</span>
              <div className="flex items-center gap-3">
                <motion.div
                  className="flex h-bar gap-px overflow-hidden rounded-soft"
                  role="img"
                  aria-label={`${NAME[name] ?? d.label}: ${one(total)} hours a week, ${PARTS.map((p) => `${p.label.toLowerCase()} ${one(d.hours_parts[p.key])}`).join(", ")}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${(total / max) * 88}%` }}
                  transition={{ duration: motionTokens.fill, delay: i * motionTokens.stagger, ease: motionTokens.ease }}
                >
                  {PARTS.map((p) => (
                    <div key={p.key} className={p.cls} style={{ width: `${(d.hours_parts[p.key] / total) * 100}%` }} />
                  ))}
                </motion.div>
                <span className="whitespace-nowrap text-small font-semibold text-ink">{one(total)} h</span>
              </div>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}
