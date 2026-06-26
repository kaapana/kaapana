import React, { useState, useEffect } from 'react';
import { SegmentationTable } from '@ohif/ui-next';
import { useActiveViewportSegmentationRepresentations } from '../hooks/useActiveViewportSegmentationRepresentations';
import { metaData } from '@cornerstonejs/core';
import { useSystem } from '@ohif/core/src';
import { toolboxState } from '@ohif/extension-default/src/stores/toolboxState';

const AI_PROMPT_TOOLS = ['Probe2', 'RectangleROI2', 'PlanarFreehandROI2', 'PlanarFreehandROI3'];

export default function PanelSegmentation({ children }: withAppTypes) {
  const { commandsManager, servicesManager } = useSystem();
  const { customizationService, displaySetService, measurementService, uiNotificationService } = servicesManager.services;
  const [promptsVisible, setPromptsVisible] = useState(toolboxState.getPromptsVisible());

  // Sync promptsVisible when changed externally (e.g. O hotkey updates toolboxState directly)
  useEffect(() => {
    const id = setInterval(() => {
      const current = toolboxState.getPromptsVisible();
      setPromptsVisible(prev => prev !== current ? current : prev);
    }, 100);
    return () => clearInterval(id);
  }, []);

  const { segmentationsWithRepresentations, disabled } =
    useActiveViewportSegmentationRepresentations({
      servicesManager,
    });

  // Extract customization options
  const segmentationTableMode = customizationService.getCustomization(
    'panelSegmentation.tableMode'
  ) as unknown as string;
  const onSegmentationAdd = customizationService.getCustomization(
    'panelSegmentation.onSegmentationAdd'
  );
  const disableEditing = customizationService.getCustomization('panelSegmentation.disableEditing');
  const showAddSegment = customizationService.getCustomization('panelSegmentation.showAddSegment');
  const CustomDropdownMenuContent = customizationService.getCustomization(
    'panelSegmentation.customDropdownMenuContent'
  );

  const CustomSegmentStatisticsHeader = customizationService.getCustomization(
    'panelSegmentation.customSegmentStatisticsHeader'
  );

  // Create handlers object for all command runs
  const handlers = {
    onSegmentationClick: (segmentationId: string) => {
      commandsManager.run('setActiveSegmentation', { segmentationId });
    },
    onSegmentAdd: segmentationId => {
      commandsManager.run('addSegment', { segmentationId });
      // Always start a new segment in positive (include) mode
      if (toolboxState.getPosNeg()) {
        toolboxState.setPosNeg(false);
      }
    },
    onSegmentClick: (segmentationId, segmentIndex) => {
      commandsManager.run('setActiveSegmentAndCenter', { segmentationId, segmentIndex });
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
            const measurementUIDs = measurementService
              .getMeasurements()
              .filter(
                e =>
                  e?.metadata?.segmentationId === segmentationId &&
                  e?.metadata?.SegmentNumber === segmentIndex
              )
              .map(e => e?.uid);
            if (measurementUIDs.length > 0) {
              measurementService.removeMany(measurementUIDs);
            }
            commandsManager.run('resetNninter', { clearMeasurements: false });

            // When loaded existing segDisplaySet, need to remove the segment from the displaySet
            const segDisplaySet = displaySetService.getDisplaySetByUID(segmentationId);
            const data = segDisplaySet?.segMetadata?.data;
            // Keep undefined entries; only remove matching segment objects
            if (Array.isArray(data)) {
              for (let i = data.length - 1; i >= 0; i--) {
                const e = data[i];
                if (e?.SegmentNumber === segmentIndex) {
                  data.splice(i, 1);
                }
              }
            }

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
      commandsManager.run('downloadSegmentation', { segmentationId });
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
      commandsManager.run('deleteSegmentation', { segmentationId });
    },
    onTogglePromptsVisibility: () => {
      const next = !toolboxState.getPromptsVisible();
      toolboxState.setPromptsVisible(next);
      setPromptsVisible(next);
      const uids = measurementService
        .getMeasurements()
        .filter(m => AI_PROMPT_TOOLS.includes(m.toolName))
        .map(m => m.uid);
      measurementService.toggleVisibilityMeasurementMany(uids, next);
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

  // Generate export options
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

  // Common props for SegmentationTable
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
        <SegmentationTable.SegmentStatistics.Header>
          <CustomSegmentStatisticsHeader />
        </SegmentationTable.SegmentStatistics.Header>
        <SegmentationTable.SegmentStatistics.Body />
      </SegmentationTable.Segments>
    );
  };

  // Render content based on mode
  const renderModeContent = () => {
    if (tableProps.mode === 'collapsed') {
      return (
        <SegmentationTable.Collapsed>
          <SegmentationTable.Collapsed.Header>
            <SegmentationTable.Collapsed.DropdownMenu>
              <CustomDropdownMenuContent />
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
      <>
        <SegmentationTable.Expanded>
          <SegmentationTable.Expanded.Header>
            <SegmentationTable.Expanded.DropdownMenu>
              <CustomDropdownMenuContent />
            </SegmentationTable.Expanded.DropdownMenu>
            <SegmentationTable.Expanded.Label />
            <SegmentationTable.Expanded.Info />
          </SegmentationTable.Expanded.Header>

          <SegmentationTable.Expanded.Content>
            <SegmentationTable.AddSegmentRow />
            {renderSegments()}
          </SegmentationTable.Expanded.Content>
        </SegmentationTable.Expanded>
      </>
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
