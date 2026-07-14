import { mockDelay } from "./api-client";
import { DIFFERENTIAL_PRIVACY } from "@/data/real-facts";

export async function getDpReport() {
  return mockDelay(DIFFERENTIAL_PRIVACY, 300);
}
