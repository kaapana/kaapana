export interface IAgentInformation {
  id: string;
  ip: string;
  name: string;
  status: string;
}

export interface IAgentSCAPolicy {
  failed: number;
  passed: number;
  unapplicable: number;
  name: string;
  id: string;
}

export interface  IAgentSCAPolicyCheck {
  description: string;
  directory?: string;
  file?: string;
  command?: string;
  rationale: string;
  references?: string;
  remediation?: string;
  result: string;
  title: string;
}

export interface IAgentVulnerability {
  severity: string;
  // updated: string;
  version: string;
  type: string;
  name: string;
  external_references: string[];
  condition: string;
  detection_time: string;
  cvss3_score: number;
  cvss2_score: number;
  published: string;
  architecture: string;
  cve: string;
  status: string;
  title: string;
}

export interface IAgentFileIntegrityAlert {
  id: string;
  path: string;
  rule: {
    level: number;
    description: string;
  };
  full_log: string;
}

export function agentStatusGate(agent: IAgentInformation, fn: CallableFunction) {
  // non-active agents can not check policies
  if (agent.status === "active") {
    fn();
  }
}