# Optional consumer study: dailyincrementalgame

This is a bounded integration proposal. The sibling repository was inspected
read-only; no integration has been installed there yet.
Its `public/shared/kit/music.mjs` already accepts a `song()` callback returning
`[key, pattern, cps]`, updates the current pattern on key changes, shares the audio
context, routes music and sound effects to different buses, and pauses for visibility
and audio preference changes. It serves sample packs and soundfonts locally.

A useful next experiment is one newly authored theme with calm, busy and intense
arrangements sharing motif, harmony, tempo and bar boundaries. Start with explicit
composition; do not add a general-purpose music-generation engine to this cleanup.

The [consumer workflow](consumer-sessions.md) now exports a synth-only pattern
factory plus tempo metadata, and keeps revisions/preferences in the consumer.
The game owns the transport and routes through its existing music bus. Switching currently
calls `pattern.play()` immediately, so transitions at a musical boundary need
explicit design and verification; the existing callback alone does not provide it.

Acceptance evidence: original/cleared composition, three audible arrangements,
controlled gain across states, no duplicate schedulers, preserved shared musical
phase, transition checks at bar boundaries, and behavior under mute, visibility
changes and re-entry. Human listening evaluates continuity and whether the three
states convey distinct energy. This proposal changes no sibling files.
