# City GO — Event Storming v2

Date: 2026-07-02
Parent: CITYGO-149

## Legend

Command: user or system intent.
Event: immutable fact that happened.
Aggregate: owner of state transition.
Read model: projection used by UI or route/search.
Policy: reaction to event.

## Destination

Commands:

- CreateDestination
- ConfigureImportScope
- StartDestinationImport
- MarkDestinationReadyForReview
- PublishDestination
- HideDestination

Events:

- DestinationCreated
- ImportScopeConfigured
- DestinationImportStarted
- DestinationReadyForReview
- DestinationPublished
- DestinationHidden

Aggregate:

- Destination

Read models:

- DestinationWorkspace
- DestinationReadinessDashboard

Policies:

- when import finished, update readiness;
- when destination published, rebuild projections.

## Import

Commands:

- StartImportRun
- RecordSourceObservation
- CompleteImportBatch
- ReplayDeadLetterItem
- RegisterImportConflict

Events:

- ImportRunStarted
- SourceObservationRecorded
- ImportBatchCompleted
- ImportDeadLetterCreated
- ImportConflictDetected
- ImportRunCompleted

Aggregate:

- ImportRun
- ImportBatch

Read models:

- ImportMonitor
- ImportRunSummary

Policies:

- failed payload creates dead letter item;
- conflict creates reviewable candidate;
- import does not publish.

## Intelligence

Commands:

- RegisterPromptVersion
- RunModelTask
- CreateCandidate
- RunRegressionGate
- EnforceCostBudget

Events:

- PromptVersionRegistered
- ModelTaskCompleted
- CandidateCreated
- RegressionGatePassed
- RegressionGateFailed
- CostBudgetExceeded

Aggregate:

- PromptVersion
- AiTaskRun
- AiCandidate

Read models:

- AiOperationsDashboard
- CandidateReviewQueue

Policies:

- failed regression blocks rollout;
- over-budget blocks run;
- candidate requires review.

## Publication

Commands:

- ApproveFact
- RejectFact
- PublishPlace
- HidePlace
- RollbackPlace
- RebuildSnapshot

Events:

- FactApproved
- FactRejected
- PlacePublished
- PlaceHidden
- PlaceRolledBack
- SnapshotBuilt

Aggregate:

- PlacePublication
- ReviewDecision
- PublicationEvent

Read models:

- PublishedPlaceSnapshot
- PublicationAuditLog

Policies:

- publish builds snapshot;
- rollback builds previous snapshot;
- public projections rebuild after snapshot.

## Search and Routing

Commands:

- RebuildSearchProjection
- RebuildRoutingProjection
- BuildRoute
- ReplaceRoutePlace
- RebuildRoute

Events:

- SearchProjectionRebuilt
- RoutingProjectionRebuilt
- RouteBuildRequested
- RouteBuilt
- RoutePartiallyBuilt
- RouteBuildFailed
- RouteRebuilt

Aggregates:

- ProjectionRebuildJob
- RouteGenerationRun
- RouteSession

Read models:

- SearchPlaceDocument
- RoutingPlaceNode
- RouteCandidateSet
- RoutePreview

Policies:

- stale projection warns or blocks route;
- route failure emits explicit reason.

## Admin

Commands:

- RunDryRunBulkOperation
- ApplyBulkOperation
- ActivateKillSwitch
- DeactivateKillSwitch
- CreateRollbackRequest

Events:

- BulkOperationDryRunCompleted
- BulkOperationApplied
- KillSwitchActivated
- KillSwitchDeactivated
- RollbackRequested

Aggregate:

- AdminBulkOperation
- AdminKillSwitch

Read models:

- AdminOperationsLog
- AdminHealthDashboard

Policies:

- apply requires dry run;
- kill switch blocks high-risk actions;
- destructive action requires reason.
