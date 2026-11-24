# Cutting Room / Creator Studio R0

Fixture interaction prototype only, authorized in the [decision log](../../docs/ui-discovery/creator-studio-redesign/DECISION-LOG.md#owner-authorization-d1d6). [Specification](../../docs/ui-discovery/creator-studio-redesign/R0-PROTOTYPE-SPEC.md).

From this directory run `node serve.mjs`, then open `http://127.0.0.1:4786/`. Stop only this process with Ctrl-C. Reload resets all session state. No install, live API, credential or production server required. There is no R1 switch.

Isolation plan: bind IPv4 loopback only and require the exact Host. Serve GET/HEAD for `/`, `/app.mjs`, `/fixtures.mjs`, `/style.css`, `/icon.svg` only, from regular file descriptors opened with no-follow. No dynamic routing, redirects or directory listings. Posters are original inline SVG in the fixture app. No source-tree imports in the browser module graph. Use a fresh headless browser, route interception, CSP violation and navigation checks, and an out-of-repo screenshot directory. The harness owns and closes its fixture server and refuses to run if the live Studio default port is occupied or an identifiable dashboard process is running; it neither probes nor stops live HTTP services. No cleanup of user data. Discarding this prototype requires only stopping its server; the production application has no reference to it.

## Owner review walkthrough

1. Open the composition review from Mission Control. Scrub three illustrated frames and open the transcript. In the exact-subject dialog simulate a newer revision; the original confirmation disables.
2. In Universal Create, compare the blocked long-form handoff with a Shorts draft. Add production detail, then simulate validation and save.
3. In Batch Studio, validate the 20-row independent slate. Fix an invalid row, select ready rows, and simulate an interrupted response. Recover the receipt and revalidate only unaccepted rows. In Series, compare episode 01's r2 pin with episode 04's proposed rebase.
4. In Video Library, filter technical and creative results separately, then choose cuts for a simulated export preflight. In Creative Library, expand capability evidence before selecting a fixture look.
5. In Operations & Agents, inspect the failed alignment attempt and preview a scoped retry. Reset clears the simulated attempt, grants, and receipts.

See [verification](VERIFICATION.md) for the browser command, screenshot manifest, exact outcomes, and remaining manual review. This does not authorize or implement R1.
