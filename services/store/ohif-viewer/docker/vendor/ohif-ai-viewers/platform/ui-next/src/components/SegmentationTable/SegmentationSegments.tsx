import React, { useState, useEffect } from 'react';
import { ScrollArea, DataRow } from '../../components';
import { Button } from '../Button/Button';
import { Icons } from '../Icons/Icons';
import { HoverCard, HoverCardTrigger, HoverCardContent } from '../../components/HoverCard';
import { useSystem } from '@ohif/core';
import { useSegmentationTableContext, useSegmentationExpanded } from './contexts';
import { SegmentStatistics } from './SegmentStatistics';

// Helper function to get measurement visibility
const getMeasurementVisibility = (servicesManager: any, segmentationId: string, segmentIndex: number) => {
  return (servicesManager.services as any).segmentationService.getSegmentMeasurementVisibility(
    segmentationId,
    segmentIndex
  );
};
import { useDynamicMaxHeight } from '../../hooks/useDynamicMaxHeight';

export const SegmentationSegments = ({ children = null }: { children?: React.ReactNode }) => {
  const { servicesManager } = useSystem();
  const [forceUpdate, setForceUpdate] = useState(0);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const {
    activeSegmentationId,
    disableEditing,
    onSegmentColorClick,
    onToggleSegmentVisibility,
    onToggleSegmentMeasurement,
    onToggleSegmentLock,
    onSegmentClick,
    onSegmentEdit,
    onSegmentDelete,
    data,
  } = useSegmentationTableContext('SegmentationSegments');

  // Continuous polling to check for measurement visibility changes
  useEffect(() => {
    const interval = setInterval(() => {
      setForceUpdate(prev => prev + 1);
    }, 500); // Check every 500ms

    return () => clearInterval(interval);
  }, []);

  // Listen for measurement visibility changes to force re-render
  useEffect(() => {
    const handleMeasurementVisibilityChange = () => {
      setForceUpdate(prev => prev + 1);
    };

    document.addEventListener('measurement-state-changed', handleMeasurementVisibilityChange);
    
    return () => {
      document.removeEventListener('measurement-state-changed', handleMeasurementVisibilityChange);
    };
  }, []);

  // Try to get segmentation data from expanded context first, then fall back to table context
  let segmentation;
  let representation;

  try {
    // Try to use the SegmentationExpanded context if available
    const segmentationInfo = useSegmentationExpanded('SegmentationSegments');
    segmentation = segmentationInfo.segmentation;
    representation = segmentationInfo.representation;
  } catch (e) {
    // Not within SegmentationExpanded context, get from active segmentation
    const segmentationInfo = data.find(
      entry => entry.segmentation.segmentationId === activeSegmentationId
    );
    segmentation = segmentationInfo?.segmentation;
    representation = segmentationInfo?.representation;
  }

  const segments = Object.values(representation.segments);
  const isActiveSegmentation = segmentation.segmentationId === activeSegmentationId;

  const { ref: scrollableContainerRef, maxHeight } = useDynamicMaxHeight(segments);

  if (!representation || !segmentation) {
    return null;
  }

  const handleDeleteSelected = () => {
    const indices = Array.from(selectedIndices).sort((a, b) => b - a); // descending to avoid index shift
    setSelectedIndices(new Set());
    indices.forEach(idx => onSegmentDelete(segmentation.segmentationId, idx));
  };

  return (
    <>
    <ScrollArea
      className={`bg-bkg-low space-y-px`}
      showArrows={true}
    >
      <div
        ref={scrollableContainerRef}
        style={{ maxHeight: maxHeight }}
      >
        {segments.map(segment => {
          if (!segment) {
            return null;
          }
          const { segmentIndex, color, visible } = segment as {
            segmentIndex: number;
            color: number[];
            visible: boolean;
          };
          const segmentFromSegmentation = segmentation.segments[segmentIndex];

          if (!segmentFromSegmentation) {
            return null;
          }

          const { locked, active, label, displayText } = segmentFromSegmentation;
          const cssColor = `rgb(${color[0]},${color[1]},${color[2]})`;

          const hasStats = segmentFromSegmentation.cachedStats?.namedStats;
          
          // Get measurement visibility state for this segment
          const isMeasurementVisible = getMeasurementVisibility(servicesManager, segmentation.segmentationId, segmentIndex);
          
          const DataRowComponent = (
            <DataRow
              key={segmentIndex}
              number={segmentIndex}
              title={label}
              description={displayText}
              colorHex={cssColor}
              isSelected={active}
              isMultiSelected={selectedIndices.has(segmentIndex)}
              isVisible={visible}
              isMeasurementVisible={isMeasurementVisible}
              isLocked={locked}
              disableEditing={disableEditing}
              className={!isActiveSegmentation ? 'opacity-80' : ''}
              onColor={() => onSegmentColorClick(segmentation.segmentationId, segmentIndex)}
              onToggleVisibility={() =>
                onToggleSegmentVisibility(
                  segmentation.segmentationId,
                  segmentIndex,
                  representation.type
                )
              }
              onToggleMeasurement={() => onToggleSegmentMeasurement(segmentation.segmentationId, segmentIndex)}
              onToggleLocked={() => onToggleSegmentLock(segmentation.segmentationId, segmentIndex)}
              onSelect={() => {
                setSelectedIndices(new Set());
                onSegmentClick(segmentation.segmentationId, segmentIndex);
              }}
              onToggleMultiSelect={() => {
                setSelectedIndices(prev => {
                  const next = new Set(prev);
                  next.has(segmentIndex) ? next.delete(segmentIndex) : next.add(segmentIndex);
                  return next;
                });
              }}
              onRename={() => onSegmentEdit(segmentation.segmentationId, segmentIndex)}
              onDelete={() => onSegmentDelete(segmentation.segmentationId, segmentIndex)}
            />
          );

          return hasStats ? (
            <HoverCard
              key={`hover-${segmentIndex}`}
              openDelay={300}
            >
              <HoverCardTrigger asChild>
                <div>{DataRowComponent}</div>
              </HoverCardTrigger>
              <HoverCardContent
                side="left"
                align="start"
                className="w-72 border"
              >
                <div className="mb-4 flex items-center space-x-2">
                  <div
                    className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                    style={{ backgroundColor: cssColor }}
                  ></div>
                  <h3 className="text-muted-foreground break-words font-semibold">{label}</h3>
                </div>

                <SegmentStatistics
                  segment={{
                    ...segmentFromSegmentation,
                    segmentIndex,
                  }}
                  segmentationId={segmentation.segmentationId}
                >
                  {children}
                </SegmentStatistics>
              </HoverCardContent>
            </HoverCard>
          ) : (
            DataRowComponent
          );
        })}
      </div>
    </ScrollArea>
    {selectedIndices.size > 0 && (
      <div className="flex items-center justify-between px-1 py-0.5">
        <span className="text-muted-foreground text-xs">{selectedIndices.size} selected</span>
        <div className="flex gap-1">
          <Button
            size="sm"
            variant="ghost"
            className="h-6 px-1.5 text-xs"
            onClick={() => setSelectedIndices(new Set())}
          >
            Clear
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-destructive hover:text-destructive h-6 px-1.5 text-xs"
            onClick={handleDeleteSelected}
          >
            <Icons.Delete className="mr-1 h-3 w-3" />
            Delete
          </Button>
        </div>
      </div>
    )}
    </>
  );
};

SegmentationSegments.displayName = 'SegmentationTable.Segments';
