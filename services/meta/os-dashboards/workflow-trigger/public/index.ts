import { WorkflowTriggerPlugin } from './plugin';

// This exports static code and TypeScript types,
// as well as, OpenSearch Dashboards Platform `plugin()` initializer.
export function plugin() {
  return new WorkflowTriggerPlugin();
}
export { WorkflowTriggerPluginSetup, WorkflowTriggerPluginStart } from './types';
