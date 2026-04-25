# DO / DON'T Worked Examples

## Example 1 — Concept before code

**DO:**

````markdown
## How do I authenticate a request?

The client library signs every request with your API key. The flow is: initialize the client with your key, then call any method — signing is automatic.

```typescript
// typescript 5.4, @widget/client 2.1.0
import { WidgetClient } from "@widget/client";

const client = new WidgetClient({ apiKey: process.env.WIDGET_API_KEY! });
const me = await client.accounts.me();
console.log(me.email);
```

The `apiKey` is read once on construction. Rotate keys by constructing a new client; the existing one continues using its original key.
````

Prose frames the governing question ("how do I authenticate?"), code shows the complete flow with imports and version pinned, prose after the sample answers a secondary question the reader will have.

**DON'T:**

````markdown
## Authentication

Authentication is the process by which the client library verifies your identity to the Widget API server using a cryptographic credential known as an API key. The `WidgetClient` class accepts an options object which includes an `apiKey` field of type `string`. When you invoke methods on the client, the library automatically signs each outbound request using the provided key. For code examples, see the API reference.
````

Heading is a noun, not a question. Four sentences of concept before any code. Jargon ("cryptographic credential") without definition. Reader is told to look elsewhere for samples — the doc that is supposed to answer the question offloads the actual answer. Confused Developer Test: fails.

---

## Example 2 — Comparison verdict

**DO:**

````markdown
### State management — verdict

Use Vuex if you're already invested in the Vue ecosystem and want tight integration with devtools. Use Pinia for new projects — it's the officially recommended path in Vue 3 and has better TypeScript ergonomics. Neither is strictly faster than the other at typical app scale; pick on developer experience, not runtime performance.
````

Three sentences, concrete recommendation, names the condition under which each wins, explicitly rejects the performance-benchmark framing as a tiebreaker. Reader knows how to choose.

**DON'T:**

````markdown
### State management

Both Vuex and Pinia are powerful state management solutions for Vue applications. Each has its own strengths and the right choice depends on your specific needs and preferences.
````

No verdict. False balance. Marketing voice ("powerful"). "Depends on your specific needs" is the author surrendering to the reader. If the reader knew their needs well enough to pick, they wouldn't be reading a comparison doc.

---

## Example 3 — Unverified code sample

**DO:**

````markdown
> **Version Note:** I was not able to verify this against a running `@widget/client` v2.1.0 at the time of writing. The signature is taken from the library's published types; behaviour under concurrent calls has not been confirmed.

```typescript
// typescript 5.4, @widget/client 2.1.0 (signature per published types; behaviour unverified)
await client.batch.submit({ ids: [1, 2, 3] });
```
````

The limitation is flagged loudly. The reader knows what has and hasn't been verified. If the sample later breaks, the flag proves the claim was not overstated.

**DON'T:**

````markdown
The batch submit method is fast and handles thousands of IDs in parallel:

```typescript
await client.batch.submit({ ids: [1, 2, 3] });
```
````

Unverified claim ("is fast", "thousands of IDs in parallel") presented as fact. No version pin. No flag. Marketing voice. If the claim is wrong, the doc loses the reader permanently. Code samples carry more authority than prose — shipping an unverified sample without a flag is a trust violation.

---

## Example 4 — Turning SCOOP research into a doc

**DO:**

> SCOOP returns a research packet on "how OAuth2 PKCE works in single-page apps". The packet has: flow diagram (prose), 7-step sequence, threat-model notes, browser support caveats, links to 3 RFCs.
>
> QUILL's output: a developer guide titled "How do I set up OAuth2 PKCE in a React SPA?". Opens with audience (implementer, React 18, using `oidc-client-ts`). Section 1: the 60-second version — one code sample showing the end state. Section 2: setup (install, configure). Section 3: the flow, with the diagram and a running snippet per step (3 of the 7 steps need code; the other 4 are described in prose). Section 4: gotchas from SCOOP's threat-model notes, framed as "if you see X, fix Y". Section 5: browser support caveats. Links to RFCs live in a "Further reading" footer — not interleaved in the main flow.

Research is turned into reader-facing docs. SCOOP's structure (by topic) becomes QUILL's structure (by reader task). Nothing fabricated, nothing left un-flagged, nothing decided.

**DON'T:**

> SCOOP's packet is reformatted section-for-section into the doc with the same headings SCOOP used. "Threat model" becomes a section titled "Threat model". RFCs are quoted at length inline. No code sample appears until section 4.

Research structure ≠ documentation structure. Readers don't come to a React guide to read threat-model analysis from an RFC — they come to implement. QUILL's job is to *transform*, not relay.
