# Submission Guide

**Deadline:** in your invitation email. **Format:** a Git repo (private repo + invite us, or a public one if you prefer) — or a zip by email/Drive if Git hosting is awkward where you are. Both are equally fine.

## Your submission contains

```
your-submission/
├── README.md              ← how to run everything, < 5 minutes, no API keys needed
├── analysis/              ← Act I code
├── agent/                 ← harness integration (see harness/README.md)
├── FINDINGS.md            ← Act I memo (template below)
├── decisions/             ← Act II ADRs, cost model, golden set, kitchen-table test
├── ANSWERS.md             ← Act III
├── AI_USE.md              ← template below
├── ai/                    ← your ACTUAL AI chats/prompts (see "Show us your AI" below)
└── walkthrough.(mp4/mkv/webm) or link — max 10 minutes
```

## Show us your AI (required, and scored)

We build with AI every day and we want to see how *you* do it — this is one of the most important signals in the whole sprint, not an afterthought. So we ask for the real thing, not a tidy summary:

- Put your **actual prompts and chat transcripts** in an `ai/` folder — exported `.md`/`.txt`/`.json` from whatever tools you used (ChatGPT, Claude, Cursor, Copilot, a local model, anything), or shared links. Messy is fine; real is the point.
- We're reading for: how you frame a problem to a model, when you push back on it or catch it being wrong, how you turn its output into something *you* understand and can defend, and where you chose to do it yourself instead.
- **If you barely used AI, or didn't — that's a completely valid choice. Just say so in `AI_USE.md` and tell us why.** We'd far rather have honesty about a light-AI approach than a fabricated trail. What ends the conversation is AI-generated work you present as your own but can't defend line-by-line at the walkthrough.

**The walkthrough:** screen-record yourself walking through your findings and your agent demo as if briefing the founder. Any recorder (OBS is free and works everywhere), any quality, your own voice. We're listening for how you explain, not how you edit video.

## FINDINGS.md template

```markdown
# Kilnbeck — Findings
## Headline (3 sentences max — what's wrong, what it's worth, how sure you are)
## The site as the data shows it (vs. as described)
## Data quality issues found & how each was handled
## NOH analysis (ratio, kW, baseload decomposition with reasoning)
## Waste vs legitimate load — the evidence
## Value: £/year range + every assumption
## Confidence table
| # | Finding | Confidence (H/M/L) | What would change my mind |
## What I didn't do (and why)
## Where my hours went (rough split)
## Five things I'd check on a site visit
```

## AI_USE.md template

```markdown
# AI Use Note
## Tools/models used (incl. local models, if any)
## The single best prompt of my week (verbatim) and why it worked
## The worst model failure I caught (what it got wrong, how I noticed)
## What I overrode or rewrote by hand, and why
## Anything submitted that I could NOT rebuild alone, flagged honestly
```

## How we evaluate

Weighted across: truth-finding (did the data give up its secrets), engineering quality (would your pipeline survive next month's export), architectural judgement (the ADRs' reasoning, not their vocabulary), calibration (your confidence table versus our ground truth — yes, we hold the answer key), communication (Tom's 200 words; your walkthrough), ownership signals (questions asked, change handled, what you chose under impossible scope), and integrity (honest accounting beats heroic claims, every time).

You'll receive written feedback against this framework whatever the outcome. If we go forward, the next stage is a **short trial working on the real system** — this sprint is the door, not the job.

*Stuck on something ambiguous? That might be deliberate. Ask, or decide and document. Both score better than pretending it wasn't there.*
