/** The counters the SLO rules in ops/prometheus read: requests, and requests slower than one second. */
import { Counter, Registry } from "prom-client";

export const registry = new Registry();
export const requests = new Counter({ name: "trpc_requests_total", help: "tRPC requests", labelNames: ["path", "code"], registers: [registry] });
export const slow = new Counter({ name: "trpc_requests_slow_total", help: "tRPC requests slower than 1 s", labelNames: ["path"], registers: [registry] });

export async function observed<T>(path: string, fn: () => Promise<T>): Promise<T> {
  const t0 = performance.now();
  try {
    const out = await fn();
    requests.inc({ path, code: "OK" });
    return out;
  } catch (e) {
    requests.inc({ path, code: (e as { code?: string }).code ?? "INTERNAL_SERVER_ERROR" });
    throw e;
  } finally {
    if (performance.now() - t0 > 1000) slow.inc({ path });
  }
}
