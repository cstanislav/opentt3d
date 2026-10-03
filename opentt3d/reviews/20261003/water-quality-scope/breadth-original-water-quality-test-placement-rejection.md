# Retained misplaced test-block failure

The first nineteen-test focused quality run fails with `KeyError: object_ground`:
the new water tests were inserted before the last six assertions of the existing
partial-HQ test, moving those assertions into the new water-scope test. The rejected
snapshot and failure log remain retained. Restore all six assertions to their
original HQ test and rerun the full scope, without deleting or weakening any check.
This failure is in offline test organization, not water/HQ artwork, runtime, saves
or source observations; none of those are modified by the repair.
