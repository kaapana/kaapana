import { toolboxState } from './utils/toolboxState';
import * as multipart from './utils/multipart';

export default function getUtilityModule() {
  return [
    {
      name: 'toolboxState',
      exports: {
        toolboxState,
      },
    },
    {
      name: 'multipart',
      exports: multipart,
    },
  ];
}
