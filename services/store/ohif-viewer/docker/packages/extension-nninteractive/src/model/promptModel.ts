// promptModel: the pending → submitted → committed lifecycle ledger for prompts.
//
// Prompts are Cornerstone annotations (never OHIF measurements). Their runtime truth is
// this ledger plus the annotation metadata; the accepted interaction history lives on the
// server session. Submitted prompts are locked and immutable; undo removes the last marker.

import { annotation as cornerstoneAnnotation } from '@cornerstonejs/tools';

import * as promptDisplay from './promptDisplay';
import { ObjectRef, PROMPT_TOOL_KIND, PromptKind, isPromptTool, objectKeyOf } from './types';

// Submitted prompt annotationUIDs in submission order (for undo marker removal).
let undoOrder: string[] = [];

function allPromptAnnotations(): any[] {
  const annotations = (cornerstoneAnnotation.state.getAllAnnotations() as any[]) ?? [];
  return annotations.filter(a => isPromptTool(a?.metadata?.toolName));
}

function promptsOf(object: ObjectRef): any[] {
  const key = objectKeyOf(object);
  return allPromptAnnotations().filter(a => a.metadata.objectKey === key);
}

export function kindOf(annotation: any): PromptKind | undefined {
  return PROMPT_TOOL_KIND[annotation?.metadata?.toolName];
}

/** Stamp a freshly-drawn prompt with its sign and owning object, and give it pending style. */
export function stampNew(annotation: any, neg: boolean, object: ObjectRef | null): void {
  annotation.metadata.neg = neg;
  if (object) {
    annotation.metadata.objectKey = objectKeyOf(object);
  }
  promptDisplay.applyPending(annotation.annotationUID, neg);
}

/** Every completed, unsubmitted prompt (the interaction being run, regardless of object). */
export function getAllUnsubmitted(): any[] {
  return allPromptAnnotations().filter(
    a => a.metadata.promptCompleted === true && a.metadata.submitted !== true
  );
}

/** Assign submitted prompts to the object they ran on, lock + darken them, record them for undo. */
export function markSubmitted(annotations: any[], object: ObjectRef): void {
  const key = objectKeyOf(object);
  for (const annotation of annotations) {
    annotation.metadata.objectKey = key;
    annotation.metadata.submitted = true;
    promptDisplay.commit(annotation.annotationUID, !!annotation.metadata.neg);
    undoOrder.push(annotation.annotationUID);
  }
}

/** Re-enable editing on prompts whose submission failed. */
export function markFailed(annotations: any[]): void {
  for (const annotation of annotations) {
    promptDisplay.unlock(annotation.annotationUID, !!annotation.metadata.neg);
  }
}

/** Remove the most recently submitted prompt marker (used after a successful backend undo). */
export function removeLastSubmitted(): void {
  const uid = undoOrder.pop();
  if (uid) {
    promptDisplay.remove(uid);
  }
}

/** Remove every prompt annotation belonging to an object (pending + submitted). */
export function clearForObject(object: ObjectRef): void {
  const removed = new Set<string>();
  for (const annotation of promptsOf(object)) {
    promptDisplay.remove(annotation.annotationUID);
    removed.add(annotation.annotationUID);
  }
  undoOrder = undoOrder.filter(uid => !removed.has(uid));
}

/** An object moved to another layer: re-point its prompts at the new object key. */
export function renameObject(from: ObjectRef, to: ObjectRef): void {
  const key = objectKeyOf(to);
  for (const annotation of promptsOf(from)) {
    annotation.metadata.objectKey = key;
  }
}

/** Remove every prompt annotation (new object armed). */
export function clearAll(): void {
  for (const annotation of allPromptAnnotations()) {
    promptDisplay.remove(annotation.annotationUID);
  }
  undoOrder = [];
}

export function setPromptsVisible(visible: boolean, object?: ObjectRef): void {
  for (const annotation of object ? promptsOf(object) : allPromptAnnotations()) {
    promptDisplay.setVisible(annotation.annotationUID, visible);
  }
}

export function countForObject(object: ObjectRef): { pending: number; submitted: number } {
  const prompts = promptsOf(object);
  const submitted = prompts.filter(a => a.metadata.submitted).length;
  const pending = prompts.filter(a => !a.metadata.submitted && a.metadata.promptCompleted).length;
  return { pending, submitted };
}

export function resetUndoOrder(): void {
  undoOrder = [];
}
