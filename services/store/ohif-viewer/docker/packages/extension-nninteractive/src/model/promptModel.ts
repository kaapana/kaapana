// promptModel: the pending → submitted → committed lifecycle ledger for prompts.
//
// Prompts are Cornerstone annotations (never OHIF measurements). Their runtime truth is
// this ledger plus the annotation metadata; the accepted interaction history lives on the
// server session. Submitted prompts are locked and immutable; undo removes the last marker.

import { annotation as cornerstoneAnnotation } from '@cornerstonejs/tools';

import * as promptDisplay from './promptDisplay';
import { PROMPT_TOOL_KIND, PROMPT_TOOL_NAMES, PromptKind } from './types';

const PROMPT_NAME_SET = new Set<string>(PROMPT_TOOL_NAMES as unknown as string[]);

// Submitted prompt annotationUIDs in submission order (for undo marker removal).
let undoOrder: string[] = [];

function allPromptAnnotations(): any[] {
  let annotations: any[] = [];
  try {
    annotations = (cornerstoneAnnotation.state.getAllAnnotations?.() as any[]) ?? [];
  } catch {
    annotations = [];
  }
  return annotations.filter(a => PROMPT_NAME_SET.has(a?.metadata?.toolName));
}

export function kindOf(annotation: any): PromptKind | undefined {
  return PROMPT_TOOL_KIND[annotation?.metadata?.toolName];
}

/** Stamp a freshly-drawn prompt with its sign and owning object, and give it pending style. */
export function stampNew(annotation: any, opts: { neg: boolean; objectKey?: string }): void {
  if (!annotation?.metadata) {
    return;
  }
  annotation.metadata.neg = opts.neg;
  if (opts.objectKey) {
    annotation.metadata.objectKey = opts.objectKey;
  }
  promptDisplay.applyPending(annotation.annotationUID, opts.neg);
}

/** Unsubmitted, completed prompts for the given object (what the next submit should send). */
export function getUnsubmittedForObject(objectKey: string): any[] {
  return allPromptAnnotations().filter(
    a =>
      a.metadata?.objectKey === objectKey &&
      a.metadata?.promptCompleted === true &&
      a.metadata?.submitted !== true
  );
}

export function hasUnsubmitted(objectKey: string): boolean {
  return getUnsubmittedForObject(objectKey).length > 0;
}

/** Every completed, unsubmitted prompt (the interaction being run, regardless of object). */
export function getAllUnsubmitted(): any[] {
  return allPromptAnnotations().filter(
    a => a.metadata?.promptCompleted === true && a.metadata?.submitted !== true
  );
}

/** Lock + darken submitted prompts and record them for undo. */
export function markSubmitted(annotations: any[]): void {
  for (const annotation of annotations) {
    if (!annotation?.metadata) {
      continue;
    }
    annotation.metadata.submitted = true;
    promptDisplay.commit(annotation.annotationUID, !!annotation.metadata.neg);
    undoOrder.push(annotation.annotationUID);
  }
}

/** Re-enable editing on prompts whose submission failed. */
export function markFailed(annotations: any[]): void {
  for (const annotation of annotations) {
    if (!annotation?.metadata) {
      continue;
    }
    promptDisplay.unlock(annotation.annotationUID, !!annotation.metadata.neg);
  }
}

/** Remove the most recently submitted prompt marker (used after a successful backend undo). */
export function removeLastSubmitted(): boolean {
  const uid = undoOrder.pop();
  if (!uid) {
    return false;
  }
  promptDisplay.remove(uid);
  return true;
}

/** Remove every prompt annotation belonging to an object (pending + submitted). */
export function clearForObject(objectKey: string): void {
  for (const annotation of allPromptAnnotations()) {
    if (annotation.metadata?.objectKey === objectKey) {
      promptDisplay.remove(annotation.annotationUID);
      undoOrder = undoOrder.filter(uid => uid !== annotation.annotationUID);
    }
  }
}

/** Remove every prompt annotation (session reset / mode exit). */
export function clearAll(): void {
  for (const annotation of allPromptAnnotations()) {
    promptDisplay.remove(annotation.annotationUID);
  }
  undoOrder = [];
}

export function setPromptsVisible(visible: boolean, objectKey?: string): void {
  for (const annotation of allPromptAnnotations()) {
    if (objectKey && annotation.metadata?.objectKey !== objectKey) {
      continue;
    }
    promptDisplay.setVisible(annotation.annotationUID, visible);
  }
}

export function countForObject(objectKey: string): { pending: number; submitted: number } {
  let pending = 0;
  let submitted = 0;
  for (const annotation of allPromptAnnotations()) {
    if (annotation.metadata?.objectKey !== objectKey) {
      continue;
    }
    if (annotation.metadata?.submitted) {
      submitted += 1;
    } else if (annotation.metadata?.promptCompleted) {
      pending += 1;
    }
  }
  return { pending, submitted };
}

export function resetUndoOrder(): void {
  undoOrder = [];
}
