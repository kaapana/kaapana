# Helm Chart Consumer: decisions for later releases

This document records what comes after Release 2 of the Helm Chart Consumer. Read [MVP.md](MVP.md) and [Release-2.md](Release-2.md) first. This document does not repeat them.

- A section that extends a section of the two documents starts with a link to it.
- **Added** marks a statement that is new. **Changed** marks a statement that replaces an earlier one.
- The sources and the markers *(proposed)* and *(to be decided)* are the same as in [MVP.md](MVP.md).

## The reconciler

**Added.** The consumer has two views of a release: its own record, and the helm release in the cluster. The two differ when someone changes the cluster with `helm` or `kubectl` and not through the consumer. The reconciler is a job of the consumer that compares the two views after a restart and marks the differences ([Story 12.3][s12.3]). See [Derive the state, do not store it][h-state].

| What the reconciler finds | What it does |
|---|---|
| A record whose helm release is gone | It sets `drift` of the release to `removed`. |
| A record whose helm release was changed outside the consumer | It sets `drift` of the release to `changed`. |
| A helm release of the consumer that has no record | It reports the helm release *(to be decided)*. |

- **The API.** A release returns the difference in its field `drift`, so that the UI can show that the release was changed or removed outside Kaapana. See `Drift` in [api-mock/app/models.py][models].
- **The first two rows need no labels.** The record stores the helm release name, so the consumer looks up each helm release directly.
- **The third row needs a label.** `helm list` shows every helm release of the cluster: the platform itself, the legacy releases of kube-helm, and the releases of the consumer. A helm release without a record can only be recognised as one of the consumer by its label. See [Labels on the helm release](Release-2.md#labels-on-the-helm-release-proposed).
- **How a change is recognised** *(to be decided)*. One way is to compare the revision of the helm release with the revision that the consumer stored after its last operation.
- **Without the reconciler.** The consumer reads the state of a release from the cluster on every request. It therefore does not show a release as ready when its helm release is gone, but it does not say that someone removed it.

## Authorization

Extends [Authorization](MVP.md#authorization) and [The origin of a release](MVP.md#the-origin-of-a-release).

- **Custom roles.** **Added.** The consumer checks the rights in the token and not the names of roles, so custom roles work without a change to the checks ([Story 5.4][s5.4]).
- **The audit log.** **Added.** The origin describes only the creation of a release. Who changed a release afterwards belongs to the audit log ([Story 5.6][s5.6]).

[s5.4]: concept.md#story-54-custom-access-control-model
[s5.6]: concept.md#story-56-audit-log
[s12.3]: concept.md#story-123-detecting-changes-made-outside-the-helm-chart-consumer
[h-state]: handoff.md#derive-the-state-do-not-store-it
[models]: api-mock/app/models.py
