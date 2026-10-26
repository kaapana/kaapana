import React from 'react';

import NnInteractivePanel from './panels/NnInteractivePanel';
import PanelSegmentation from './panels/PanelSegmentation';

export default function getPanelModule() {
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
