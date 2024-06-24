import { VisualizationsSetup, VisualizationsStart } from 'src/plugins/visualizations/public/';
import { DataPublicPluginSetup, DataPublicPluginStart } from 'src/plugins/data/public/';

// eslint-disable-next-line @typescript-eslint/no-empty-interface
export interface WorkflowTriggerPluginSetup {}
// eslint-disable-next-line @typescript-eslint/no-empty-interface
export interface WorkflowTriggerPluginStart {}

export interface WorkflowTriggerSetupDependencies {
    visualizations: VisualizationsSetup;
    data: DataPublicPluginSetup;
}

export interface WorkflowTriggerOptionProps {
    fontSize: number;
    margin: number;
    buttonTitle: string;
}
