import { AreaView } from "./features/areas/AreaView";
import { ChangesView } from "./features/changes/ChangesView";
import { HoursView } from "./features/hours/HoursView";
import { type View, go, useRoute } from "./shared/route";

const TABS: { view: View; label: string }[] = [
  { view: "hours", label: "Hours" },
  { view: "delivery", label: "Delivery" },
  { view: "oncall", label: "On-call" },
  { view: "changes", label: "Infrastructure changes" },
  { view: "jobs", label: "Vesting runs" },
];

export function App() {
  const view = useRoute();
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-sheet">
        <div className="mx-auto flex max-w-page flex-wrap items-end justify-between gap-4 px-6 pt-5">
          <div className="pb-4">
            <p className="text-lead font-bold text-ink">Equity platform ops</p>
            <p className="text-small text-muted">CI, on-call, infrastructure changes and vesting runs for an equity-management product, on simulated orgs</p>
          </div>
          <nav aria-label="Views" className="flex flex-wrap gap-1">
            {TABS.map((t) => (
              <button
                key={t.view}
                type="button"
                onClick={() => go(t.view)}
                aria-current={view === t.view ? "page" : undefined}
                className={`border-b-rule px-3 pb-3 pt-2 font-semibold transition-colors ${
                  view === t.view ? "border-focus text-ink" : "border-transparent text-muted hover:text-ink"
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-page px-6 py-7">
        {view === "hours" && <HoursView />}
        {(view === "delivery" || view === "oncall" || view === "jobs") && <AreaView key={view} area={view} />}
        {view === "changes" && <ChangesView />}
      </main>
    </div>
  );
}
