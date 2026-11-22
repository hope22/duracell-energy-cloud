# Estimated battery energy

Home Assistant's Energy Dashboard needs cumulative kWh; the integration supplies instantaneous W.

Create two **Integral** helpers under Settings → Devices & services → Helpers, one using Battery charging power and the other Battery discharging power. Choose hours as the integration time, kilo as the metric prefix, and the left integration method. Where supported, set a maximum sub-interval of five minutes so steady values continue to accumulate.

Use the resulting kWh helpers as energy into and out of the battery in the Energy Dashboard. Entity names may vary with your device's configured name.

These are estimates from cloud samples, not billing meters. Outages and stale cloud readings affect accuracy. Compare totals against the manufacturer's portal before relying on them. Solar DC power is not a verified AC generation meter. Grid import/export direction is not yet verified, so this integration does not claim grid-energy support.
