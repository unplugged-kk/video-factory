# Frontend architecture decision

## Recommendation

Extend `contentos/dashboard.py` and serve a frontend of semantic HTML, CSS, and vanilla ES modules from `contentos/ui/`. Do not add React, Vite, or a web framework for v1.

This is a single-owner local application with about ten screens, a small JSON API, and a Python core that already owns the workflow. A build step would add a second toolchain without removing any of the pipeline's complexity.

## Comparison

| Concern | Vanilla ES modules | React, Vite, and TypeScript |
|---|---|---|
| Repository fit | Matches the existing dashboard and the absence of a frontend build | New dependency and build chain |
| Serving | The Python server serves static modules directly | Requires a build artifact or a second dev server |
| Components | Explicit render functions and a shared contract | Built-in composition |
| Types | JSDoc plus runtime validation at the API boundary | Stronger static checking |
| Complex editors | Manual | Better suited to a timeline editor or many shared forms |
| Tests | `node --test` for pure modules, already used in the repo | Adds a frontend test runner |
| Local and future VPS use | The same built files can be served later | Also possible, after the build |

Visual polish, accessibility, and a coherent workbench do not require React.

## Module boundaries

```text
contentos/ui/
  index.html
  styles.css
  main.js                 application shell and routing
  api.js                  token, errors, response checks
  state.js                ledger and manifest to UI state
  components/
    next-action.js
    timeline.js
    approval.js
    review.js
    health.js
    logs.js
    tables.js
    dialog.js
    forms.js
  pages/
    jobs.js
    job.js
    queue.js
    health.js
    help.js
```

`main.js` may route and compose pages. It must not contain stage rules, digest logic, or HTML for every screen. Shared components receive data and return DOM nodes. Pages fetch through `api.js` and map responses through `state.js`.

## State mapping

`state.js` is a view model, not a workflow engine. It translates existing records into the labels in `product-and-user-journeys.md`. It must not advance a stage locally or store an approval that the ledger does not contain.

The API client treats a missing token, a non-JSON `production run` exit, and a 409 digest mismatch as different errors. Pages render those errors. They do not retry them automatically.

## When to reconsider React

Reconsider only after the fixture prototype or the M4 implementation shows at least one of these:

- several editors whose state changes depend on one another
- a custom timeline that native controls and the stage list cannot express
- component tests becoming larger than the behavior they protect
- more than one person regularly editing the same UI modules

A wish for a more polished visual is not one of those conditions.

## VPS note

Either frontend can be served remotely. Remote access requires a separate authentication, HTTPS, and process-isolation design. It is not a reason to choose React, and it is not permission to bind this server on `0.0.0.0`.
