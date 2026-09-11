### browser_artifact
Explicitly retrieve the full browser document retained by the Context Governor.

Use this only when the compact browser observation is insufficient and the exact retained page content is required. Pass the `browser://...` artifact reference returned in the latest browser observation as `ref`.

The artifact is temporary and may expire. Prefer the normal browser `content` or `detail` actions when targeted inspection is enough. Treat full artifact retrieval as an explicit context escalation because the returned content can be large.