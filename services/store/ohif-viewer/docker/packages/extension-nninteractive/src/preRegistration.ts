import { Icons } from '@ohif/ui-next';

import ToolNninter from './icons/ToolNninter';
import ToolSam from './icons/ToolSam';
import ToolTarget from './icons/ToolTarget';
import ToolVoxTell from './icons/ToolVoxTell';

export default function preRegistration() {
  Icons.addIcon('tool-nninter', ToolNninter);
  Icons.addIcon('tool-sam', ToolSam);
  Icons.addIcon('tool-target', ToolTarget);
  Icons.addIcon('tool-voxtell', ToolVoxTell);
}
