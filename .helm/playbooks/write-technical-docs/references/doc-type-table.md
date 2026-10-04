# Doc-Type Decision Table

Pick one primary type before drafting. A single document may borrow elements from another type (a README almost always contains a mini-quickstart), but the primary type governs the structure.

| Type | When to use | Governing question the doc answers | Required sections |
|------|-------------|------------------------------------|-------------------|
| **README** | Project root or package root; first thing a developer sees | "What is this, should I use it, and how do I get started in 60 seconds?" | One-line summary, Why use it / When to use it, Prerequisites, Install, Quickstart (runnable), Links to deeper docs, License/contributing link |
| **API reference** | Every public function, class, or endpoint needs documented surface area | "What does this identifier do, what does it take, and what does it return?" | Per entry: signature, parameters (with types), return value, side effects, errors/exceptions, minimal example, "See also" links. Consistent template per entry. |
| **Tutorial** | Zero → visible result path; reader is learning | "How do I build a working thing from nothing?" | Prerequisites, final-result screenshot or output shown up top, numbered steps with imports on step 1, checkpoint output after each step, "What you've built" summary, next-steps links |
| **Developer guide** | Task-oriented walkthrough for a specific use case | "How do I accomplish task X with this tool?" | Problem framing ("you want to …"), working end-state code first, layered explanation, edge cases and gotchas, "How to choose" verdict if alternatives exist |
| **Comparison doc** | Evaluating two or more libraries, frameworks, or approaches | "Given my needs, which of these should I pick?" | Audience statement, conceptual mapping table (X's `Foo` ≈ Y's `Bar`), side-by-side code panels per functional area, feature gap matrix (✅/❌/🔶), verdict per category, "How to choose" synthesis at the end |
| **Migration guide** | Version N → N+1, or framework A → framework B | "I have working code today. How do I get to the new version without breaking anything?" | Version pinning (from X.Y.Z to A.B.C), breaking-change summary table, concept mapping, step-by-step transition path, gotchas, rollback note |
| **Quickstart** | Subset of README or tutorial — under 5 minutes to green | "Give me the shortest working path so I can evaluate." | Install command, minimal working snippet, expected output, one link to "now what?" |

## Which am I writing? decision heuristic

- Reader's first contact with the project? → **README**
- Reader needs to look up a specific identifier? → **API reference**
- Reader is learning from zero with time to follow along? → **Tutorial**
- Reader has a specific task in mind? → **Developer guide**
- Reader is evaluating between options? → **Comparison doc**
- Reader has working code and needs to move versions? → **Migration guide**
- Reader has 5 minutes to decide if it's worth more time? → **Quickstart**
