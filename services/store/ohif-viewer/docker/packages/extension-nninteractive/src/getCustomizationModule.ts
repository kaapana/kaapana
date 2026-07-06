import { Enums } from '@cornerstonejs/tools';

export default function getCustomizationModule() {
  return [
    {
      name: 'default',
      value: {
        'cornerstone.overlayViewportTools': {
          active: [
            {
              toolName: 'WindowLevel',
              bindings: [{ mouseButton: Enums.MouseBindings.Primary }],
            },
            {
              toolName: 'Pan',
              bindings: [{ mouseButton: Enums.MouseBindings.Auxiliary }],
            },
            {
              toolName: 'Zoom',
              bindings: [{ mouseButton: Enums.MouseBindings.Secondary }],
            },
            {
              toolName: 'StackScroll',
              bindings: [{ mouseButton: Enums.MouseBindings.Wheel }],
            },
          ],
          enabled: [
            {
              toolName: 'PlanarFreehandContourSegmentation',
              configuration: {
                displayOnePointAsCrosshairs: true,
              },
            },
          ],
        },
      },
    },
  ];
}
