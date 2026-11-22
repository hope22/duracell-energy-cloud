# Publishing and future updates

Repository target: `hope22/duracell-energy-cloud`. This checkout does not publish itself.

1. Create the public GitHub repository with issues enabled. Set its description to “Unofficial Home Assistant integration for Duracell Energy cloud monitoring” and topics `home-assistant`, `hacs`, `duracell`, `integration`, `energy`.
2. Push the reviewed source. Confirm the Tests, HACS and Hassfest jobs pass. HACS default-catalog inclusion is a separate submission, not needed for custom-repository installation.
3. Test installing the default branch through HACS on the existing Home Assistant instance: retained configuration and entities, new battery sensors, several polling cycles, restart, reconfigure, invalid-token reauthentication and rollback. Record the Home Assistant version and results.
4. Resolve all failures before advertising a stable release. Verify username/password setup and multi-inverter selection.
5. Update CHANGELOG.md from Unreleased to the release date. Keep manifest version `0.7.0`, create tag `v0.7.0` and publish a GitHub release with the changelog entry. HACS downloads the standard repository layout; no special ZIP asset is required.
6. For later updates, bump the manifest version (for example `0.7.1`), update the changelog, run the checks, verify on Home Assistant and publish the matching tag/release. Users install the update through HACS and restart Home Assistant.

References: [HACS integration requirements](https://www.hacs.xyz/docs/publish/integration/), [HACS validation action](https://www.hacs.xyz/docs/publish/action/), [Home Assistant manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/).
