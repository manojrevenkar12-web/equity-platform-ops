import type { Results } from "./types";
import { useResource } from "./api";

/** Every view reads the same report. */
export const useResults = () => useResource<Results>("/api/results");
