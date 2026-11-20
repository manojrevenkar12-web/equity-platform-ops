/** The API process: tRPC over HTTP, /metrics for Prometheus, /healthz for Kubernetes. */
import { createServer } from "node:http";
import { Client, Connection } from "@temporalio/client";
import { createHTTPHandler } from "@trpc/server/adapters/standalone";
import { router } from "./api";
import { registry } from "./metrics";

async function main() {
  const temporal = new Client({
    connection: await Connection.connect({ address: process.env.TEMPORAL_ADDRESS ?? "localhost:7233" }),
    namespace: process.env.TEMPORAL_NAMESPACE ?? "default",
  });
  const trpc = createHTTPHandler({ router, createContext: () => ({ temporal }) });
  createServer(async (req, res) => {
    if (req.url === "/metrics") {
      res.setHeader("content-type", registry.contentType);
      res.end(await registry.metrics());
    } else if (req.url === "/healthz") {
      res.end("ok");
    } else {
      trpc(req, res);
    }
  }).listen(Number(process.env.PORT ?? 3000));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
