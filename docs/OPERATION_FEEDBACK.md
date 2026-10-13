# Restart and speed-test feedback

The overview and map show a status banner for the latest restart or speed test.
Individual controls show the status of their own last request. Every request is
correlated with its network, point and action; a test on one point cannot mark
another point's restart as complete.

Home Assistant also provides an **Action status** sensor on each Google network
and point. Button attributes include the correlated request, target, timestamps
and last Google state. Interface text follows the HA user language.

| Status | Meaning |
| --- | --- |
| Queued / Sending request | HA is preparing or sending the explicit command. |
| Request accepted | Google acknowledged the operation; it is not yet complete. |
| Running | Google explicitly reported a running operation. |
| Completed | Google reported `DONE`. |
| Failed / Cancelled | Google rejected, failed or cancelled the operation. |
| Status not confirmed | Delivery or completion could not be confirmed. |

A completed restart command does not prove that the point has finished booting
or its clients have reconnected. Check connectivity and uptime separately.
Speed-test results may appear after the operation completes and are then read
back through the existing metrics endpoints. No progress percentage is invented.

Starting with 0.8.3, a mesh test prepares a measurement server on the discovered
primary point with `localSpeedTest`, waits for Google's preparation operation to
finish, then sends the selected point's `meshSpeedTest` with `serverApId` in the
query string. Both stages belong to the same user request. Server preparation
alone does not mean the mesh test completed. A failed or unconfirmed preparation
does not send the client test; an ambiguous client write is never repeated.
The interface explains which stage is pending. A missing or ambiguous primary,
or selecting the primary as its own mesh client, is rejected before any write.

Status reads run every five seconds only while an explicitly requested operation
is pending. They stop after ten minutes, respect Google's rate-limit window and
are cancelled when the entry unloads. Normal metric polling never starts a test
or restart. Ambiguous writes are not retried automatically, and a duplicate
pending command for the same action and target is rejected before another write.
Operation tracking is in memory and resets when HA or the integration restarts.

Some Google operations move directly from accepted to completed. The interface
does not fabricate a running state if Google does not supply one. A temporary
status-lookup error retains the last confirmed state with an explanatory message.
