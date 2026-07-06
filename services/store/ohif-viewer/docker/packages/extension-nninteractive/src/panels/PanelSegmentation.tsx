import React, { useEffect, useState } from 'react';
import { metaData } from '@cornerstonejs/core';
import { useSystem } from '@ohif/core/src';

import { useActiveViewportSegmentationRepresentations } from '../../../cornerstone/src/hooks/useActiveViewportSegmentationRepresentations';
import * as promptModel from '../model/promptModel';
import { toolboxState } from '../utils/toolboxState';
import { SegmentationTable } from './SegmentationTable';
import { SegmentationDropdownMenuContent } from './SegmentationTable/SegmentationDropdownMenuContent';

export default function PanelSegmentation({ children }: withAppTypes) {
  const { commandsManager, servicesManager } = useSystem();
  const {
    customizationService,
    displaySetService,
    measurementService,
    uiNotificationService,
    segmentationService,
  } = servicesManager.services;
  const [promptsVisible, setPromptsVisible] = useState(toolboxState.getPromptsVisible());

  useEffect(() => {
    const id = setInterval(() => {
      const current = toolboxState.getPromptsVisible();
      setPromptsVisible(prev => (prev !== current ? current : prev));
    }, 100);

    return () => clearInterval(id);
  }, []);

  const { segmentationsWithRepresentations, disabled } =
    useActiveViewportSegmentationRepresentations({
      servicesManager,
    });

  const segmentationTableMode = customizationService.getCustomization(
    'panelSegmentation.tableMode'
  ) as unknown as string;
  const onSegmentationAdd = customizationService.getCustomization(
    'panelSegmentation.onSegmentationAdd'
  );
  const disableEditing = customizationService.getCustomization('panelSegmentation.disableEditing');
  const showAddSegment = customizationService.getCustomization('panelSegmentation.showAddSegment');
  const CustomSegmentStatisticsHeader = customizationService.getCustomization(
    'panelSegmentation.customSegmentStatisticsHeader'
  );

  const handlers = {
    onSegmentationClick: (segmentationId: string) => {
      const seg = segmentationService.getSegmentation(segmentationId);
      const firstIndex =
        seg?.cachedStats?.nninteractiveManaged === true
          ? 1
          : seg?.segments
            ? Number(Object.keys(seg.segments)[0])
            : NaN;
      if (Number.isFinite(firstIndex)) {
        void commandsManager.run('loadSegmentForRefinement', { segmentationId, segmentIndex: firstIndex });
      }
    },
    onSegmentAdd: () => {
      commandsManager.run('armNextNninterObject');
    },
    onSegmentClick: (segmentationId, segmentIndex) => {
      void commandsManager.run('loadSegmentForRefinement', { segmentationId, segmentIndex });
    },
    onSegmentEdit: (segmentationId, segmentIndex) => {
      commandsManager.run('editSegmentLabel', { segmentationId, segmentIndex });
    },
    onSegmentationEdit: segmentationId => {
      commandsManager.run('editSegmentationLabel', { segmentationId });
    },
    onSegmentColorClick: (segmentationId, segmentIndex) => {
      commandsManager.run('editSegmentColor', { segmentationId, segmentIndex });
    },
    onSegmentReset: (segmentationId, segmentIndex) => {
      commandsManager.run('resetSegment', { segmentationId, segmentIndex });
    },
    onSegmentDelete: (segmentationId, segmentIndex) => {
      const deletePromise = new Promise<void>((resolve, reject) => {
        setTimeout(() => {
          try {
            // deleteSegment removes the object's prompt annotations and resets the
            // backend if it currently holds this object.
            commandsManager.run('deleteSegment', { segmentationId, segmentIndex });
            resolve();
          } catch (error) {
            reject(error);
          }
        }, 100);
      });

      uiNotificationService.show({
        title: `Deleting ${segmentIndex}`,
        message: `Deleting segment ${segmentIndex}...`,
        type: 'info',
        promise: deletePromise,
        promiseMessages: {
          loading: `Deleting ${segmentIndex}...`,
          success: () => `Deleted ${segmentIndex} successfully`,
          error: error => `Delete ${segmentIndex} failed: ${error?.message || 'Unknown error'}`,
        },
      });
    },
    onToggleSegmentVisibility: (segmentationId, segmentIndex, type) => {
      commandsManager.run('toggleSegmentVisibility', { segmentationId, segmentIndex, type });
    },
    onToggleSegmentMeasurement: (segmentationId, segmentIndex) => {
      commandsManager.run('toggleSegmentMeasurement', { segmentationId, segmentIndex });
    },
    onToggleSegmentLock: (segmentationId, segmentIndex) => {
      commandsManager.run('toggleSegmentLock', { segmentationId, segmentIndex });
    },
    onToggleSegmentationRepresentationVisibility: (segmentationId, type) => {
      commandsManager.run('toggleSegmentationVisibility', { segmentationId, type });
    },
    onSegmentationDownload: segmentationId => {
      commandsManager.run({
        commandName: 'downloadNninterSegmentation',
        commandOptions: { segmentationId },
        context: 'SEGMENTATION',
      });
    },
    setStyle: (segmentationId, type, key, value) => {
      commandsManager.run('setSegmentationStyle', { segmentationId, type, key, value });
    },
    toggleRenderInactiveSegmentations: () => {
      commandsManager.run('toggleRenderInactiveSegmentations');
    },
    onSegmentationRemoveFromViewport: segmentationId => {
      commandsManager.run('removeSegmentationFromViewport', { segmentationId });
    },
    onSegmentationDelete: segmentationId => {
      const seg = segmentationService.getSegmentation(segmentationId);
      if (seg?.cachedStats?.nninteractiveManaged === true) {
        commandsManager.run('deleteSegment', { segmentationId, segmentIndex: 1 });
        return;
      }
      commandsManager.run('deleteSegmentation', { segmentationId });
    },
    onTogglePromptsVisibility: () => {
      const next = !toolboxState.getPromptsVisible();
      toolboxState.setPromptsVisible(next);
      setPromptsVisible(next);
      // Prompts are Cornerstone annotations (not measurements) — toggle them directly.
      promptModel.setPromptsVisible(next);
    },
    setFillAlpha: ({ type }, value) => {
      commandsManager.run('setFillAlpha', { type, value });
    },
    setOutlineWidth: ({ type }, value) => {
      commandsManager.run('setOutlineWidth', { type, value });
    },
    setRenderFill: ({ type }, value) => {
      commandsManager.run('setRenderFill', { type, value });
    },
    setRenderOutline: ({ type }, value) => {
      commandsManager.run('setRenderOutline', { type, value });
    },
    setFillAlphaInactive: ({ type }, value) => {
      commandsManager.run('setFillAlphaInactive', { type, value });
    },
    getRenderInactiveSegmentations: () => {
      return commandsManager.run('getRenderInactiveSegmentations');
    },
  };

  const exportOptions = segmentationsWithRepresentations.map(({ segmentation }) => {
    const { representationData, segmentationId } = segmentation;
    const { Labelmap } = representationData;

    if (!Labelmap) {
      return { segmentationId, isExportable: true };
    }

    const referencedImageIds = Labelmap.referencedImageIds;
    const firstImageId = referencedImageIds[0];
    const instance = metaData.get('instance', firstImageId);

    if (!instance) {
      return { segmentationId, isExportable: false };
    }

    const SOPInstanceUID = instance.SOPInstanceUID || instance.SopInstanceUID;
    const SeriesInstanceUID = instance.SeriesInstanceUID;
    const displaySet = displaySetService.getDisplaySetForSOPInstanceUID(
      SOPInstanceUID,
      SeriesInstanceUID
    );

    return {
      segmentationId,
      isExportable: displaySet?.isReconstructable,
    };
  });

  const tableProps = {
    disabled,
    data: segmentationsWithRepresentations,
    mode: segmentationTableMode,
    title: 'Segmentations',
    exportOptions,
    disableEditing,
    onSegmentationAdd,
    showAddSegment,
    renderInactiveSegmentations: handlers.getRenderInactiveSegmentations(),
    promptsVisible,
    ...handlers,
  };

  const renderSegments = () => {
    return (
      <SegmentationTable.Segments>
        {CustomSegmentStatisticsHeader ? (
          <SegmentationTable.SegmentStatistics.Header>
            <CustomSegmentStatisticsHeader />
          </SegmentationTable.SegmentStatistics.Header>
        ) : null}
        <SegmentationTable.SegmentStatistics.Body />
      </SegmentationTable.Segments>
    );
  };

  const renderModeContent = () => {
    if (tableProps.mode === 'collapsed') {
      return (
        <SegmentationTable.Collapsed>
          <SegmentationTable.Collapsed.Header>
            <SegmentationTable.Collapsed.DropdownMenu>
              <SegmentationDropdownMenuContent />
            </SegmentationTable.Collapsed.DropdownMenu>
            <SegmentationTable.Collapsed.Selector />
            <SegmentationTable.Collapsed.Info />
          </SegmentationTable.Collapsed.Header>
          <SegmentationTable.Collapsed.Content>
            <SegmentationTable.AddSegmentRow />
            {renderSegments()}
          </SegmentationTable.Collapsed.Content>
        </SegmentationTable.Collapsed>
      );
    }

    return (
      <SegmentationTable.Expanded>
        <SegmentationTable.Expanded.Header>
          <SegmentationTable.Expanded.DropdownMenu>
            <SegmentationDropdownMenuContent />
          </SegmentationTable.Expanded.DropdownMenu>
          <SegmentationTable.Expanded.Label />
          <SegmentationTable.Expanded.Info />
        </SegmentationTable.Expanded.Header>

        <SegmentationTable.Expanded.Content>
          <SegmentationTable.AddSegmentRow />
          {renderSegments()}
        </SegmentationTable.Expanded.Content>
      </SegmentationTable.Expanded>
    );
  };

  return (
    <SegmentationTable {...tableProps}>
      {children}
      <SegmentationTable.Config />
      {renderModeContent()}
    </SegmentationTable>
  );
}
