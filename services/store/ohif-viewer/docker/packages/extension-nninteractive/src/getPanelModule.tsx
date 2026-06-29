import React from 'react';

import NnInteractivePanel from './panels/NnInteractivePanel';

export default function getPanelModule({ extensionManager }) {
  const cornerstoneSegmentationPanel = extensionManager.getModuleEntry(
    '@ohif/extension-cornerstone.panelModule.panelSegmentation'
  );

  const PanelSegmentation = cornerstoneSegmentationPanel.component;
  const PanelSegmentationWithTools = ({ configuration }) => {
    return (
      <>
        <NnInteractivePanel
          buttonSectionId="aiToolBox"
          title="nnInteractive OHIF"
          defaultOpen={true}
        />
        <PanelSegmentation configuration={configuration} />
      </>
    );
  };

  return [
    {
      name: 'aiToolBox',
      iconName: 'tool-nninter',
      iconLabel: 'AI',
      label: 'AI',
      component: props => (
        <NnInteractivePanel
          buttonSectionId="aiToolBox"
          title="nnInteractive OHIF"
          {...props}
        />
      ),
    },
    {
      name: 'panelSegmentationWithTools',
      iconName: 'tab-segmentation',
      iconLabel: 'Segmentation',
      label: 'Segmentation',
      component: PanelSegmentationWithTools,
    },
  ];
}
