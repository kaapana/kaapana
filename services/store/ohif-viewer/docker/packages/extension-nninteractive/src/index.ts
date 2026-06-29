import { Types } from '@ohif/core';

import getCommandsModule from './commandsModule';
import getCustomizationModule from './getCustomizationModule';
import getPanelModule from './getPanelModule';
import getUtilityModule from './getUtilityModule';
import { id } from './id';
import preRegistration from './preRegistration';

const extension: Types.Extensions.Extension = {
  id,
  preRegistration,
  getCommandsModule,
  getCustomizationModule,
  getPanelModule,
  getUtilityModule,
};

export default extension;
