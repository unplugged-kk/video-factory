# Motion intent for explainers (project reference)

Advisory guidance for the `video-director`. It fills gaps only. `explainer-motion-craft` (R1-R6) and `hyperframes-core` are authoritative, and nothing here may override them. If a sentence below ever seems to conflict, the higher rule wins and the director records the conflict in the decision log.

Source note: the method (intent before technique, one personality per piece, hero-first staging, failure vocabulary) is paraphrased from the approved audit `docs/factory-v2/10-motion-director-integration-audit.md`, which studied LottieFiles' motion-design-skill (MIT, (c) 2025 LottieFiles, commit f9a8a04). No text or tables were copied, and nothing was taken from Motion AI Kit. Numbers marked *provisional* are this project's own starting points, not tested thresholds.

## 1. Intent before animation
Answer in this order, in words, before naming any technique: what should the viewer understand after this scene, what should they feel (curious, reassured, surprised, calm), and what is the smallest change over time that gets them there. If the answer to the last question is "nothing changes", the scene is static.

## 2. One personality per video
Choose one for the whole video and use it everywhere. It sets pace and ease, never whether motion is purposeful.

| Personality | Use for | Entrance ease | Overshoot | Typical reveal (provisional) |
|---|---|---|---|---|
| `calm-precise` (default) | explainers, how-it-works | `power3.out` (R1) | none | 0.4-0.7 s |
| `premium` | brand, product stories | `power2.inOut` / `power3.out` | none | 0.6-1.0 s |
| `energetic` | hooks, news, shorts | `power4.out` / `expo.out` | none | 0.2-0.4 s |
| `playful` | children, light brand | `back.out(1.2)` | small, and only when the brief asks (R1) | 0.3-0.5 s |

Mixing personalities inside one video reads as inconsistency; do not.

## 3. Staging and the focal point
One focal point at any moment. Everything else is quiet (dimmed or still). Lead with the thing the narration is naming; context settles before or after, not at the same time. Entries come from one consistent direction (left-to-right for 16:9, top-to-bottom for 9:16) so the eye learns the flow once.

## 4. Primary, secondary, ambient
- **Primary**: the change that carries the idea (a line drawing, a card appearing on its word). Every animated scene has exactly one.
- **Secondary**: allowed only when it makes the primary easier to read (for example the receiving node highlights as the line arrives). It needs a reason in `why`. If you cannot say what it helps the viewer understand, delete it.
- **Ambient**: `none`. No breathing, drifting or looping decoration (R4). Only a brief that explicitly sets `allow_ambient` can change this, and then it must be finite and seek-safe.

## 5. Counter-motion, only when it explains
A return path may mirror its outbound path in the opposite direction because "coming back" is the idea (a request goes out, an answer comes back). Do not add opposing motion for balance or atmosphere. Parallax and background drift are out.

## 6. Timing follows the narration
Reveals land on the spoken word (R2), using narration cues, not a stagger budget. If narration is slow, the reveal waits; if it is fast, split the scene rather than speed up the motion. Hold each finished frame long enough to read its text twice at phone size. One idea per shot (R6). Do not shorten holds for the 9:16 version.

## 7. Static is a valid choice
Keep a scene static when it must be read or compared (a menu of options, a final loop diagram, an end card), when the point is a relationship rather than a sequence, or when motion would compete with the caption. A static scene still gets a clean entrance from the previous scene; it simply has no further motion. A video where every scene animates is a warning sign.

## 8. Camera
Default `hold`. Move only when the move itself explains something (a pull-back that reveals the whole loop). At most one move per scene; start from where the last one ended (R3). No scene-long drift. Avoid large zooms, spins and rapid direction changes: they are uncomfortable on a phone.

## 9. Failure vocabulary for review (symptom -> project-safe fix)
| Symptom | Likely cause | Fix inside the house rules |
|---|---|---|
| Feels like a slideshow | everything appears at scene start | move reveals to their spoken cues (R2) |
| Feels busy | competing movers, decoration | remove secondary and ambient motion; one focal point |
| Feels robotic | linear or identical eases | use the personality's ease; vary reveal length by importance, not randomly |
| Feels flat | nothing leads the eye | stage the focal point; dim the rest; do not add loops |
| Unreadable on a phone | text too small, held too briefly | larger type, longer hold, inside the safe box (R5) |
| Disconnected scenes | different entry directions or personalities | one flow direction, one personality |

## 10. What this reference does not do
It does not set durations in milliseconds for UI states, hover or press feedback, 60 fps budgets or `prefers-reduced-motion` handling; those belong to interactive interfaces and do not apply to a fixed MP4.
