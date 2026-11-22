# Energy Dashboard: built-in battery sensors

Version 0.6.0 automatically adds **Battery energy charged** and **Battery energy discharged** to each configured inverter. No helpers or new integration setup are required.

After updating through HACS and restarting Home Assistant, open the Energy Dashboard's battery configuration:

| Field | Duracell sensor |
| --- | --- |
| Energy discharged from the battery | Battery energy discharged |
| Energy charged into the battery | Battery energy charged |
| Type of power measurement | Two sensors |
| Charging power | Battery charging power |
| Discharging power | Battery discharging power |
| Battery state of charge | Battery state of charge |

The energy sensors report kWh with the energy device class and total-increasing state class. Let Home Assistant receive successful readings and record statistics; if they do not appear immediately, wait several minutes and refresh the configuration page. Check that the entities are enabled and not excluded from Recorder.

## What the totals mean

These are **estimated energy totals from cloud power samples**, not the manufacturer's cumulative meter readings. They start at zero when first installed and retain their totals across normal restarts/reloads. They do not backfill earlier history, import old helper totals or accumulate while Home Assistant is stopped.

A left-sum calculation uses the previous sample's charging/discharging watts multiplied by the elapsed time until the next successful sample, divided by 3,600,000 to obtain kWh. Every successful poll updates the total even when the power reading is unchanged. No additional cloud calls or timers are needed.

Failed polls and invalid/missing battery-power values break the sampling interval; accumulation resumes after two valid samples. Gaps longer than twice the configured polling interval plus 20 seconds are skipped. Totals remain stored while the sensors are unavailable. This deliberately avoids estimating unknown outages and may undercount energy during them. Successful but stale provider readings cannot be detected without a reliable provider timestamp. Cloud sampling and reporting delays also affect accuracy.

## If you already made Integral helpers

You can keep using the old helpers to retain their existing history, or switch the Energy Dashboard to the new built-in sensors. Do not configure a second battery entry for the same physical battery using both sets of totals. Keep old helpers until you are satisfied with the change; new sensors do not inherit their historical totals.

Solar and grid energy sensors are outside this update. Solar DC power is not a verified AC generation meter, and grid import/export direction remains unverified.
