import { defineStore } from "pinia";
import type { IAgentInformation, IAgentSCAPolicy, IAgentVulnerability, IAgentFileIntegrityAlert } from "../types/wazuh";

export type AgentInformationMap = Map<IAgentInformation['id'], IAgentInformation>;

export type PolicyInformationMap = Map<IAgentSCAPolicy['id'], IAgentSCAPolicy>;
export type AgentPolicyInformationMap = Map<IAgentInformation['id'], PolicyInformationMap>;
// export type PolicyCheckInformationMap = Map<IAgentSCAPolicy['id'], IAgentSCAPolicyCheck[]>;
//export type AgentPolicyCheckInformationMap = Map<IAgentSCAPolicy['id'], PolicyCheckInformationMap>;

export type VulnerabilityInformationMap = Map<IAgentVulnerability['title'], IAgentVulnerability>
export type AgentVulnerabilityInformationMap = Map<IAgentInformation['id'], VulnerabilityInformationMap>;

export type FileIntegrityInformationMap = Map<IAgentFileIntegrityAlert['id'], IAgentFileIntegrityAlert>
export type AgentFileIntegrityInformationMap = Map<IAgentInformation['id'], FileIntegrityInformationMap>;

interface WazuhState {
  agentInformation: AgentInformationMap | null;
  policyInformation: AgentPolicyInformationMap | null;
  //policyCheckInformation: Record<IAgentSCAPolicy['id'], IAgentSCAPolicyCheck[]> | null;
  vulnerabilityInformation: AgentVulnerabilityInformationMap | null;
  fileIntegrityInformation: AgentFileIntegrityInformationMap | null;
}

export const useWazuhStore = defineStore("wazuh", {
  state: (): WazuhState => {
    return {
      agentInformation: null,
      policyInformation: null,
      //policyCheckInformation: null
      vulnerabilityInformation: null,
      fileIntegrityInformation: null
    }
  }
});