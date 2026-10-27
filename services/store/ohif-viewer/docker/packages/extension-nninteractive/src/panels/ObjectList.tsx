import React, { useEffect, useState } from 'react';
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  Icons,
} from '@ohif/ui-next';

export interface ObjectRow {
  segmentationId: string;
  segmentIndex: number;
  label: string;
  color: string;
  visible: boolean;
  active: boolean;
}

interface SortableRow extends ObjectRow {
  ordinal: number;
}

/**
 * One row per object. nnInteractive objects are segments packed into shared layer
 * segmentations, and an object can move between layers, so rows are ordered by the object's
 * creation ordinal rather than by layer. Segmentations no viewport shows (e.g. an imported
 * SEG already split into objects) are not listed.
 */
function readObjects(servicesManager: any): ObjectRow[] {
  const { segmentationService, viewportGridService } = servicesManager.services;
  const viewportId = viewportGridService.getActiveViewportId();
  const active = viewportId ? segmentationService.getActiveSegmentation(viewportId) : null;
  const rows: SortableRow[] = [];

  for (const segmentation of segmentationService.getSegmentations() ?? []) {
    const { segmentationId } = segmentation;
    const managed = segmentation.cachedStats?.nninteractiveManaged === true;
    if (!managed && !segmentationService.getViewportIdsWithSegmentation(segmentationId)?.length) {
      continue;
    }
    const representation = viewportId
      ? segmentationService.getSegmentationRepresentations(viewportId, { segmentationId })?.[0]
      : undefined;
    for (const [key, segment] of Object.entries<any>(segmentation.segments ?? {})) {
      if (!segment) {
        continue;
      }
      const segmentIndex = Number(key);
      let color = 'rgb(128,128,128)';
      try {
        const [r, g, b] = segmentationService.getSegmentColor(
          viewportId,
          segmentationId,
          segmentIndex
        );
        color = `rgb(${r},${g},${b})`;
      } catch {
        // not shown in the active viewport — keep the neutral swatch
      }
      const ordinal = Number(segment.cachedStats?.objectOrdinal);
      rows.push({
        segmentationId,
        segmentIndex,
        label: segment.label || `Object ${segmentIndex}`,
        color,
        visible: representation?.segments?.[segmentIndex]?.visible !== false,
        active: active?.segmentationId === segmentationId && !!segment.active,
        ordinal: Number.isInteger(ordinal) && ordinal > 0 ? ordinal : Number.MAX_SAFE_INTEGER,
      });
    }
  }
  return rows.sort((a, b) => a.ordinal - b.ordinal).map(({ ordinal, ...row }) => row);
}

export function useObjects(servicesManager: any): ObjectRow[] {
  const [objects, setObjects] = useState<ObjectRow[]>(() => readObjects(servicesManager));

  useEffect(() => {
    const { segmentationService, viewportGridService } = servicesManager.services;
    const update = () => setObjects(readObjects(servicesManager));
    const subscriptions = [
      ...[
        'SEGMENTATION_ADDED',
        'SEGMENTATION_MODIFIED',
        'SEGMENTATION_REMOVED',
        'SEGMENTATION_REPRESENTATION_MODIFIED',
        'SEGMENTATION_REPRESENTATION_REMOVED',
      ].map(key => segmentationService.subscribe(segmentationService.EVENTS[key], update)),
      viewportGridService.subscribe(viewportGridService.EVENTS.ACTIVE_VIEWPORT_ID_CHANGED, update),
    ];
    update();
    return () => subscriptions.forEach(sub => sub?.unsubscribe?.());
  }, [servicesManager]);

  return objects;
}

/** Show or hide an object in every viewport that displays it (MPR has three). */
export function setObjectVisible(servicesManager: any, object: ObjectRow, visible: boolean) {
  const { segmentationService } = servicesManager.services;
  for (const viewportId of segmentationService.getViewportIdsWithSegmentation(
    object.segmentationId
  )) {
    for (const representation of segmentationService.getSegmentationRepresentations(viewportId, {
      segmentationId: object.segmentationId,
    })) {
      segmentationService.setSegmentVisibility(
        viewportId,
        object.segmentationId,
        object.segmentIndex,
        visible,
        representation.type
      );
    }
  }
}

export function ObjectList({
  objects,
  onSelect,
  onToggleVisible,
  onRename,
  onColor,
  onDelete,
}: {
  objects: ObjectRow[];
  onSelect: (object: ObjectRow) => void;
  onToggleVisible: (object: ObjectRow) => void;
  onRename: (object: ObjectRow) => void;
  onColor: (object: ObjectRow) => void;
  onDelete: (object: ObjectRow) => void;
}) {
  if (!objects.length) {
    return (
      <div
        className="text-muted-foreground text-xs"
        style={{ padding: '6px 2px' }}
      >
        No objects yet. Draw a prompt on the image to create the first one.
      </div>
    );
  }

  return (
    <div
      className="flex flex-col"
      style={{ gap: 1 }}
    >
      {objects.map(object => (
        <div
          key={`${object.segmentationId}#${object.segmentIndex}`}
          role="button"
          aria-pressed={object.active}
          className={`flex cursor-pointer items-center rounded ${
            object.active ? 'bg-popover' : 'bg-muted'
          }`}
          style={{
            minHeight: 28,
            paddingLeft: 6,
            borderLeft: `2px solid ${object.active ? '#5acce6' : 'transparent'}`,
            fontWeight: object.active ? 600 : undefined,
            opacity: object.visible ? 1 : 0.6,
          }}
          onClick={() => onSelect(object)}
        >
          <span
            className="rounded-full"
            style={{ width: 10, height: 10, flexShrink: 0, backgroundColor: object.color }}
          />
          <span
            className={`flex-1 text-sm ${object.active ? 'text-highlight' : 'text-muted-foreground'}`}
            style={{
              marginLeft: 8,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={object.label}
          >
            {object.label}
          </span>
          <Button
            size="icon"
            variant="ghost"
            className="h-6 w-6"
            aria-label={object.visible ? 'Hide object' : 'Show object'}
            title={object.visible ? 'Hide' : 'Show'}
            onClick={e => {
              e.stopPropagation();
              onToggleVisible(object);
            }}
          >
            {object.visible ? (
              <Icons.Hide className="h-6 w-6" />
            ) : (
              <Icons.Show className="h-6 w-6" />
            )}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="icon"
                variant="ghost"
                className="h-6 w-6"
                aria-label="Object actions"
                onClick={e => e.stopPropagation()}
              >
                <Icons.More className="h-6 w-6" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              onCloseAutoFocus={e => e.preventDefault()}
            >
              <DropdownMenuItem onClick={() => onRename(object)}>
                <Icons.Rename className="text-foreground" />
                <span className="pl-2">Rename</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onColor(object)}>
                <Icons.ColorChange className="text-foreground" />
                <span className="pl-2">Change color</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onDelete(object)}>
                <Icons.Delete className="text-foreground" />
                <span className="pl-2">Delete</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ))}
    </div>
  );
}
