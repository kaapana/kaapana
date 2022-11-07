import { CoreSetup, CoreStart, Plugin } from '../../../src/core/public';
import {
  WorkflowTriggerPluginSetup,
  WorkflowTriggerPluginStart,
  WorkflowTriggerSetupDependencies
} from './types';
import { BaseVisTypeOptions } from 'src/plugins/visualizations/public/';

import { PLUGIN_NAME } from '../common';
// @ts-expect-error
import { getWorkflowTriggerVisController } from './components/workflow_trigger_controller'
import { opensearchQuery } from '../../../src/plugins/data/public';


export class WorkflowTriggerPlugin
  implements Plugin<WorkflowTriggerPluginSetup, WorkflowTriggerPluginStart> {

  public setup(core: CoreSetup, {visualizations, data}: WorkflowTriggerSetupDependencies): WorkflowTriggerPluginSetup {

    const config: BaseVisTypeOptions = {
      name: PLUGIN_NAME,
      title: 'Create Cohort',
      icon: 'logstashIf',
      description: 'To manage cohort queries',
      visualization: getWorkflowTriggerVisController(data, core.getStartServices, opensearchQuery.buildOpenSearchQuery),
    };
  
    visualizations.createBaseVisualization(config);

    // Return methods that should be available to other plugins
    return {};
  }

  public start(_core: CoreStart): WorkflowTriggerPluginStart {
    return {};
  }

  public stop() {}
}
