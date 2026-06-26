import React from 'react';
import { Button, Icons } from '@ohif/ui-next';
import { useSegmentationTableContext, useSegmentationExpanded } from './contexts';

export const AddSegmentRow: React.FC<{ children?: React.ReactNode }> = ({ children = null }) => {
  const {
    activeRepresentation,
    activeSegmentation,
    disableEditing,
    activeSegmentationId,
    onSegmentAdd,
    onSegmentReset,
    onToggleSegmentationRepresentationVisibility,
    onTogglePromptsVisibility,
    promptsVisible,
    data,
    showAddSegment,
  } = useSegmentationTableContext('AddSegmentRow');

  // Try to get from expanded context first, then fall back to active segmentation
  let segmentationId = activeSegmentationId;
  let representation = activeRepresentation;

  try {
    const expandedContext = useSegmentationExpanded('AddSegmentRow');
    if (expandedContext.isActive) {
      segmentationId = expandedContext.segmentation.segmentationId;
      representation = expandedContext.representation;
    }
  } catch (e) {
    // Use the default values from table context
  }

  // If no segmentations, don't render
  if (!data?.length) {
    return null;
  }

  // Check if all segments are visible
  const allSegmentsVisible = Object.values(representation?.segments || {}).every(
    segment => segment?.visible !== false
  );

  const Icon = allSegmentsVisible ? (
    <Icons.Hide className="h-6 w-6" />
  ) : (
    <Icons.Show className="h-6 w-6" />
  );

  const allowAddSegment = showAddSegment && !disableEditing;

  // Find the active segment index for reset
  const activeSegmentIndex = activeSegmentation
    ? Number(Object.keys(activeSegmentation.segments).find(
        k => (activeSegmentation.segments as any)[k]?.active
      ))
    : NaN;
  const canReset = !disableEditing && onSegmentReset && !isNaN(activeSegmentIndex);

  return (
    <div className="my-px flex min-h-7 w-full items-center justify-between rounded pl-0.5 pr-7">
      <div className="mt-1 flex flex-row items-center gap-1">
        {allowAddSegment ? (
          <Button
            size="sm"
            variant="ghost"
            className="pr pl-0.5"
            onClick={() => onSegmentAdd(segmentationId)}
          >
            <Icons.Add />
            Add Segment <span className="ml-1 opacity-50 text-xs">[M]</span>
          </Button>
        ) : null}
        {canReset ? (
          <Button
            size="sm"
            variant="ghost"
            className="pr pl-0.5"
            onClick={() => onSegmentReset(segmentationId, activeSegmentIndex)}
          >
            <Icons.Refresh className="h-4 w-4" />
            Reset Segment <span className="ml-1 opacity-50 text-xs">[R]</span>
          </Button>
        ) : null}
        {onTogglePromptsVisibility ? (
          <Button
            size="sm"
            variant="ghost"
            className="pr pl-0.5"
            onClick={() => onTogglePromptsVisibility()}
          >
            <Icons.Pencil className="h-4 w-4" />
            {promptsVisible ? 'Hide Prompts' : 'Show Prompts'} <span className="ml-1 opacity-50 text-xs">[O]</span>
          </Button>
        ) : null}
      </div>
      <Button
        size="icon"
        variant="ghost"
        onClick={() =>
          onToggleSegmentationRepresentationVisibility(segmentationId, representation?.type)
        }
      >
        {Icon}
      </Button>
      {children}
    </div>
  );
};
