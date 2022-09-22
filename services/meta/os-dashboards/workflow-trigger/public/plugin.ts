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

import { Schemas } from '../../../src/plugins/vis_default_editor/public/';
import { WorkflowTriggerOptions } from './components/workflow_trigger_options';


export class WorkflowTriggerPlugin
  implements Plugin<WorkflowTriggerPluginSetup, WorkflowTriggerPluginStart> {

  public setup(core: CoreSetup, {visualizations, data}: WorkflowTriggerSetupDependencies): WorkflowTriggerPluginSetup {

    const config: BaseVisTypeOptions = {
      name: PLUGIN_NAME,
      title: 'Start Process Button',
      icon: 'logstashIf',
      description: 'An actionable button',
      visualization: getWorkflowTriggerVisController(data, core.getStartServices),
      visConfig: {
        defaults: {
          fontSize: 30,
          margin: 10,
          buttonTitle: 'START',
        },
      },
      editorConfig: {
        optionsTemplate: WorkflowTriggerOptions,
        schemas: new Schemas([
          {
            group: 'metrics',
            name: 'metric',
            title: 'Metric',
            min: 1,
            aggFilter: ['!derivative', '!geo_centroid'],
            defaults: [
              { type: 'count', schema: 'metric' }
            ]
          }, {
            group: 'buckets',
            name: 'segment',
            title: 'Bucket Split',
            min: 0,
            max: 1,
            aggFilter: ['!geohash_grid', '!filter']
          }
        ]),
      }
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
