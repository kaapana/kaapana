import NnInteractivePanel from './panels/NnInteractivePanel';

export default function getPanelModule() {
  return [
    {
      // Name kept for the mode's layout reference.
      name: 'panelSegmentationWithTools',
      iconName: 'tool-nninter',
      iconLabel: 'Segmentation',
      label: 'Segmentation',
      component: NnInteractivePanel,
    },
  ];
}
