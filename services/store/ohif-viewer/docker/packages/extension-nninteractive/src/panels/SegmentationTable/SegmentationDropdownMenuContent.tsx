import React from 'react';
import { DropdownMenuContent, DropdownMenuItem, Icons } from '@ohif/ui-next';
import { useSegmentationExpanded, useSegmentationTableContext } from './contexts';

export const SegmentationDropdownMenuContent = () => {
  const {
    disableEditing,
    exportOptions,
    onSegmentationDelete,
    onSegmentationDownload,
    onSegmentationEdit,
    onSegmentationRemoveFromViewport,
    onToggleSegmentationRepresentationVisibility,
    setShowConfig,
    showConfig,
  } = useSegmentationTableContext('SegmentationDropdownMenuContent');
  const { segmentation, representation } = useSegmentationExpanded(
    'SegmentationDropdownMenuContent'
  );

  const segmentationId = segmentation.segmentationId;
  const representationType = representation?.type;
  const exportOption = exportOptions?.find(option => option.segmentationId === segmentationId);
  const canExport = exportOption?.isExportable ?? true;

  return (
    <DropdownMenuContent
      align="start"
      onCloseAutoFocus={event => event.preventDefault()}
    >
      {setShowConfig && (
        <DropdownMenuItem onClick={() => setShowConfig(!showConfig)}>
          <Icons.Settings className="text-foreground" />
          <span className="pl-2">Appearance</span>
        </DropdownMenuItem>
      )}
      {onSegmentationEdit && !disableEditing && (
        <DropdownMenuItem onClick={() => onSegmentationEdit(segmentationId)}>
          <Icons.Rename className="text-foreground" />
          <span className="pl-2">Rename</span>
        </DropdownMenuItem>
      )}
      {onToggleSegmentationRepresentationVisibility && representationType && (
        <DropdownMenuItem
          onClick={() =>
            onToggleSegmentationRepresentationVisibility(segmentationId, representationType)
          }
        >
          {representation?.visible ? (
            <Icons.Hide className="text-foreground" />
          ) : (
            <Icons.Show className="text-foreground" />
          )}
          <span className="pl-2">{representation?.visible ? 'Hide' : 'Show'}</span>
        </DropdownMenuItem>
      )}
      {onSegmentationDownload && canExport && (
        <DropdownMenuItem onClick={() => onSegmentationDownload(segmentationId)}>
          <Icons.Download className="text-foreground" />
          <span className="pl-2">Download</span>
        </DropdownMenuItem>
      )}
      {onSegmentationRemoveFromViewport && (
        <DropdownMenuItem onClick={() => onSegmentationRemoveFromViewport(segmentationId)}>
          <Icons.Close className="text-foreground" />
          <span className="pl-2">Remove from viewport</span>
        </DropdownMenuItem>
      )}
      {onSegmentationDelete && !disableEditing && (
        <DropdownMenuItem onClick={() => onSegmentationDelete(segmentationId)}>
          <Icons.Delete className="text-foreground" />
          <span className="pl-2">Delete</span>
        </DropdownMenuItem>
      )}
    </DropdownMenuContent>
  );
};
