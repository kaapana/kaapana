interface IPolicy {
  id: string;
  name: string;
  severity: 'UNSET' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  categories: string[];
}

interface ICommonEntityInfo {
  clusterName: string;
  namespace: string;
  resourceType: 'DEPLOYMENT' | 'SECRETS' | 'CONFIGMAPS'
}

interface IAlertDeployment {
  name: string;
  inactive: boolean;
}

export interface IPolicyViolation {
  id: string;
  lifecycleStage: 'DEPLOY' | 'BUILD' | 'RUNTIME';
  time: string;
  policy: IPolicy;
  state: 'ACTIVE' | 'SNOOZED' | 'RESOLVED' | 'ATTEMPTED'
  commonEntityInfo: ICommonEntityInfo;
  deployment: IAlertDeployment;
  externalUrl: string;
}

export interface IImage {
  id: string;
  name: string;
  registry: string;
  os?: string;
  cves?: number;
  fixableCves?: number;
  priority: string;
  riskScore: number;
  topCvss?: number;
  externalUrl: string;
}

export interface IDeployment {
  id: string;
  name: string;
  namespace: string;
  priority: string;
  riskScore: number;
  externalUrl: string;
}

interface SecretRelationship {
  id: string;
  name: string;
}

export interface ISecret {
  id: string;
  name: string;
  namespace: string;
  type: string;
  createdAt: string;
  containers: SecretRelationship[]
  deployments: SecretRelationship[]
  externalUrl: string;
}