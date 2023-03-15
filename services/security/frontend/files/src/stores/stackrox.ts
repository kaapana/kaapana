import { defineStore } from "pinia";
import type { IImage, IDeployment, IPolicyViolation, ISecret } from "@/types/stackrox";

interface StackRoxState {
  policyViolations: IPolicyViolation[] | null;
  images: IImage[] | null;
  deployments: IDeployment[] | null;
  secrets: ISecret[] | null;
}

export const useStackRoxStore = defineStore("stackrox", {
  state: (): StackRoxState => {
    return {
      policyViolations: null,
      images: null,
      deployments: null,
      secrets: null,
    }
  }
});