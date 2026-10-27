import { Types } from '@ohif/core';

import getCommandsModule from './commandsModule';
import getPanelModule from './getPanelModule';
import { id } from './id';
import preRegistration from './preRegistration';

const extension: Types.Extensions.Extension = {
  id,
  preRegistration,
  getCommandsModule,
  getPanelModule,
};

export default extension;
