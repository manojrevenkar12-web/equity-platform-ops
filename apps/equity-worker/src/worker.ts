/** The worker process: runs in both regions against the same Temporal namespace and MongoDB cluster. */
import { NativeConnection, Worker } from "@temporalio/worker";
import { MongoClient } from "mongodb";
import { ensureIndexes } from "./activities";
import { boundActivities } from "./activities.entry";
import { TASK_QUEUE } from "./api";

async function main() {
  const mongo = await new MongoClient(process.env.MONGO_URL ?? "mongodb://localhost:27017").connect();
  const db = mongo.db(process.env.MONGO_DB ?? "equity");
  await ensureIndexes(db);
  const connection = await NativeConnection.connect({ address: process.env.TEMPORAL_ADDRESS ?? "localhost:7233" });
  const worker = await Worker.create({
    connection,
    namespace: process.env.TEMPORAL_NAMESPACE ?? "default",
    taskQueue: TASK_QUEUE,
    workflowsPath: require.resolve("./workflows"),
    activities: boundActivities(db),
  });
  await worker.run();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
