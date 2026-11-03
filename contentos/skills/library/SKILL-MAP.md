# Skill Map and Video Format Taxonomy

Use this map to choose a creative recipe. The skill catalog in `config/skill-catalog.json` is the canonical source for numeric IDs and paths.

## Selection rules

1. If the user specifies a number, resolve it through the JSON catalog. Never guess a number.
2. If the user supplies a script without a style, run `prompts/02-script-intake-and-style-selector.md` first.
3. Choose one primary skill and at most two complementary skills unless the storyboard proves more are needed.
4. Verify the live factory supports the required effects. A skill's presence does not prove its dependencies or rendering path are installed.
5. Use the factory's existing renderer and QA; don't create a separate pipeline per skill.
6. If no skill fits, propose a new reusable skill using `prompts/05-integrate-skill-with-factory.md`.

## Music and lyric videos

- **4. `/lyric-video`** — A hand-drawn crayon lyric video on a dark chalkboard: every word writes on as it's sung, and each line gets its own little drawing.
- **10. `/hindi-lyric-video`** — A calm Hindi lyric video like Banjaare's “Barsaat”: Devanagari lines write on over old paper while rain falls and footprints walk across the page with the song.
- **12. `/titan-anime`** — An anime episode set in an Attack on Titan-style world: giant walls, green capes, horses, flags and titans, with your own original characters telling the story.
- **14. `/sketch-music-video`** — A pencil-sketch lyric video like Anuv Jain's “Inaam”: soft graphite drawings of the song's story fill the page while the lyrics are handwritten next to them, line by line.
- **15. `/kinetic-lyrics`** — Big kinetic typography for an English song, like Justin Bieber's “Let Me Love You”: every word punches in on the beat in chunky letters on black, with paint splats and confetti.
- **18. `/comic-reel`** — A famous movie scene retold as a comic book, like the Drishyam 3 reel: halftone panels, speed lines, BOOM bursts and speech bubbles for every line of dialogue.
- **19. `/sketch-to-motion`** — Your rough paper sketches turned into a polished app-promo animation: the sketch stays on the left, the finished motion graphic plays next to it, like the Kulhad chai reel.
- **21. `/podcast-cartoon`** — A famous podcast moment turned into a gag: the podcast clip plays, then an original cheeky cartoon kid pops in as a sticker and asks the big question, and you react, like the “maut ke baare mein sochte ho?” reel.
- **22. `/ink-line-lyrics`** — A fast lyric video drawn as ONE glowing ink line that never breaks, like the Main Aur Tu reel: the line morphs into a new drawing on every key word, with the camera punching on every kick.
- **23. `/mirzapur-video`** — A web-series dialogue turned into a comic meme, like the Kaalin Bhaiya “chai piyoge?” reel: a bold comic portrait of the don, halftone backgrounds that change on every beat, and a POV caption.
- **24. `/party-lyrics`** — A loud party-anthem lyric video, like Honey Singh's Casa Tupka: gold and gem 3D lettering, red curtains and lavender smoke, confetti on every beat, and a cartoon of the singer in their signature look.
- **26. `/rap-video`** — A full-energy cartoon rap video like Boom Shaka: the rapper drawn as a bold cartoon, BOOM bursts, speed lines and lyrics that slam in on every beat.
- **27. `/aarti-video`** — A devotional aarti video full of fire and light, like the Shiv aarti: glowing diyas, flames, a damru rhythm and the aarti lines in Devanagari.
- **30. `/neon-lyrics`** — A synthwave rap lyric video like KR$NA's “I Guess”: a neon grid, a big retro sun, a cartoon of the rapper in a varsity jacket and glowing Hindi lyrics.
- **31. `/paper-cutout`** — A paper-cutout music video like Jaadoo: hand-cut paper characters, floating islands and lyric tags that pop on their words, moving in 15 fps stop-motion.
- **33. `/bairan-style`** — A romantic lyric video like the Bairan reel: watercolour-painted characters cut out like paper stickers, polaroids, a sunflower and a beating heart popping in, every move fast in and slowly settling.
- **35. `/beat-transition-edit`** — The trending beat edit from the How to do this with Claude series (Ep 1): your dance or twirl video in smooth slow motion, cutting to your photos on every music hit with a quick zoom-blur dissolve and a warm film grade, copied from any reference reel.
- **36. `/scribble-edit`** — Your own clip covered in live marker doodles, like the Justin Bieber “Where Are Ü Now” video from How to do this with Claude (Ep 5): the wall behind you fills with hand-drawn stars, rockets, cats and lightning, crowns and shades stick to your face as you move, a neon line traces your body, and the whole look changes on every beat.
- **37. `/sketch-doodle-edit`** — One photo turned into the trending sketch doodle edit from How to do this with Claude (Ep 4): the people flicker between the real photo and a pencil sketch on the beat, white wind lines swoosh across the sky, a scribble outline draws around them and a handwritten line writes itself in.
- **39. `/painted-beat-edit`** — A viral footage edit remade with no footage at all, like the Shiv aarti reel from How to do this with Claude (Ep 2): Claude paints the images in code in an acrylic mural style and cuts between them on every half-beat with a slow zoom.
- **40. `/glow-lyrics`** — A dreamy lyric video like MITRAZ's Khwahish from Ye likho ye milega Part 7: flat vector scenes at purple dusk, silhouettes that tell the story (a boy alone on a bench, the girl he misses glowing inside a golden birdcage), soft bloom on every light, and the lyric line glowing in word by word.
- **41. `/minimal-lyrics`** — A quiet, minimal lyric video like Bayaan's Safar from Ye likho ye milega Part 7: a flat horizon, a lone silhouette walking, wind drawn as sweeping streak lines, and a sky whose colour follows the mood of each line, with one small serif lyric line at the bottom.
- **42. `/watercolor-lyrics`** — A soft lyric video like Ashu Shukla's Phir Se Shuru from Ye likho ye milega Part 7: the camera pans right across warm paper while autumn watercolour scenes of one couple draw themselves in (ink lines first, then the wash blooms), leaves fall, and the lyric lines write on word by word.
- **43. `/spotify-particle-lyrics`** — A 16:9 lyric video in four looks, like the Kalyani (ARJN × KDS × Fifty4 × Ronn ft. Shreya Ghoshal) video: a tilted Spotify lyrics card where every sung word lights up with glowing sparks, then the artists' photo turned into a monochrome particle portrait that morphs into a second photo while red-and-white lyrics pop on the right and dance on the beat, then gold motion-graphic lyrics with fast blur word changes for the singer's part, and a black-and-white rain-on-glass music player to end.
- **44. `/pink-spotify-clip-lyrics`** — A poetic 16:9 lyric video like the Alfaaz (Hamza Malik × Zain Zohaib) video: a tilted pink Spotify lyrics card, then motion graphics that follow the meaning of each line (a rose that draws itself, letters cut out of the clip, a cinema letterbox, a dotted footstep path with the words along it, and a split screen for the last line), with my emotional clips playing softly behind the lyrics so both the video and the words stay readable.
- **45. `/night-glow-lyrics`** — A 16:9 lyric video that makes people feel the song, like the Dooron Dooron (Paresh Pahuja ft. Harleen Sethi) video: one night-blue look with glowing white light, emotional clips that follow the story of each line, an Instagram post that dives into the title, and lyrics that change style with the music (small tracked caps + one huge serif word for the key lines, simple bottom lines in between), ending with the last line turning to light.
- **46. `/red-rap-lyrics`** — A fast rap lyric video in one red grade, like the Hola Amigo (KR$NA ft. Seedhe Maut) video: a red glass lyrics card that peels in like a page over a tilted wall of lyric words, then neon words standing on a rainy street with ripple reflections, then the rapper's photo turned into a monochrome particle portrait with stacked italic lyrics lighting up word by word, and a 3D tower of words where the camera eases to every new word, ending on a DAMN! slam.
- **47. `/glass-to-neon-lyrics`** — An emotional 16:9 lyric video that keeps changing mood with the song, like the Arz Kiya Hai (Anuv Jain × Lost Stories) video: a red glass Apple-Music-style lyrics card over a wall of giant red words that cracks and shatters, then full-screen clips with the lyrics standing in the empty space (a starry red field with twinkling and shooting stars, a sunny hill, a man against the clouds), a key line cut out as giant letters with fire burning inside them, and a pink neon ending where lyrics fall in, splash and reflect in water while it rains.
- **48. `/maut-ke-bare-mai-sochte-ho`** — A podcast moment retold as a comic page, like the Ranveer × Honey Singh “manzil kya hai? … Death.” clip from Ye likho ye milega Part 8: the host's big question in a speech bubble, a long silent beat, then DEATH. slams in on black with a skull and the guest gulps in an inset panel.
- **51. `/woof-woof`** — A streamer's live moment as a cartoon, like the IShowSpeed “woof woof” clip from Ye likho ye milega Part 8: he stares into the camera, then barks on every beat while WOOF! bursts fly, the live chat floods with woofs and the viewer count shoots up.
- **59. `/match-cut`** — The same word on a new page, landing in exactly the same spot on screen.
- **60. `/shutter-stack`** — Photo cards that drop in on a camera flash, stacking up.
- **61. `/led-matrix-text`** — Big dot-matrix words, one per beat, like a stadium screen.
- **64. `/particle-text`** — Words built out of falling dots that assemble on the beat.

## Spoken content, podcast, news, and editing

- **3. `/katha-video`** — A pravachan clip turned into an animated story: the characters act out the kahani, the speaker talks from a lip-synced corner badge, and Hindi captions follow every word.
- **6. `/news-report`** — A Hinglish tech-news report in Fireship style: flat dark background, screenshot cards with red boxes and highlights, memes, and a hard cut every two seconds, with you as the anchor.
- **7. `/talking-head-edit`** — Your raw clip, fully edited: captions on every word, the screen splits into two windows to show what you're talking about, and demo videos play full screen. Your face is never re-coloured.
- **8. `/podcast-explainer`** — A podcast clip turned into an animated explainer, like the Raj Shamani “Two Winners” video: simple stick-figure metaphors for every idea, bold kinetic captions, and the host drawn as a cartoon in a live corner window.
- **9. `/podcast-comic`** — A podcast clip retold as a 9:16 comic book, like the Raj Shamani “ladke ko kab jaanoge” reel: the guest drawn in the studio below (bookshelf, Break the Cage poster, mic), and a new comic panel slams in on top for every point he makes, with a burst word and Hindi speech-bubble captions.
- **32. `/street-interview`** — A funny street interview turned into a cartoon, like the bad day interview: the interviewee drawn as a flat cartoon, night-street background and big caption words on the punchlines.
- **66. `/podcast-reel-edit`** — Tight cuts, a clean headline and punch-ins, podcast-clip style.
- **70. `/kinetic-talking-head-edit`** — A cream panel with green highlight typography that moves with my words.
- **76. `/breaking-news`** — A TV-news lower third, a scrolling ticker and a channel bug.

## Stories, animation, and illustration

- **1. `/anime-reel`** — An anime-style episode with original characters drawn in code and lip-synced to your voice lines, like the Zero Se Freelance series.
- **2. `/madhubani-kahani`** — A Panchatantra-style story told as a living Madhubani painting: double black outlines, patterned fills, fish-scale water and a red-yellow folk border.
- **5. `/watercolor-map`** — A painted watercolor world map: a pin drops on the start city, a plane flies the real great-circle route, and the destination washes in with colour.
- **11. `/pusho-reel`** — A Puneet Superstar “Baba Pusho” cartoon reel with the full class: Baba Pusho teaching, his students reacting, Hindi captions on every word, a new scene for every line.
- **16. `/latent-reel`** — A roast-show clip turned into a cartoon, like Samay Raina's India's Got Latent: the guest at the mic on the left, the host reacting on the right, the show's stage behind them.
- **17. `/latent-comic`** — An India's Got Latent clip retold as a 9:16 comic book, like the MC Stan episode reels: Samay Raina and the judges at the show's desk on top, a close-up of whoever is talking below with a gag for every line, halftone dots, bursts and speech-bubble captions.
- **25. `/anime-fight`** — An anime fight gag in the one-punch style: a sleepy, unbothered hero ends a giant monster with a single punch, then turns the same punch on something relatable, like Monday morning.
- **28. `/shadow-puppet`** — A kids story told like tholu bommalata shadow puppets: black cut-out characters with pin joints moving against a glowing orange screen.
- **29. `/kids-story`** — A bright 60-second kids story like Pyaasi Chidiya: soft rounded characters, a sunny world, Hindi speech bubbles and a little reacting companion in the corner.
- **49. `/madira-peekar-soo-gaye`** — A famous movie dialogue turned into a comic-book scene, like the Drishyam 3 “madira peekar so gaye” clip from Ye likho ye milega Part 8: one character delivers the line in a speech bubble word by word, then the other explodes in close-up with speed lines and a colour flash.
- **50. `/baba-pusho`** — A Puneet Superstar “Baba Pusho” clip as a cartoon class, like Ye likho ye milega Part 8: Pusho preaches from his desk under a big Om, his fixed class of students reacts, and every Hindi line gets a caption plus a scene of its own.
- **75. `/comic-halftone`** — Halftone dots, a comic panel border, speech bubbles and POW words.

## Explainers and motion graphics

- **13. `/personal-explainer`** — An explainer in your own voice, like “How will the Tesla fly?”: real footage with credit, clean diagrams that build step by step, numbers that pop, and you as the narrator.
- **20. `/blueprint-explainer`** — A long YouTube explainer drawn like an engineering blueprint, like the Piramal Finance loan video: a blue grid sheet, white line drawings, and numbers that calculate live as you talk.
- **34. `/3d-explainer`** — A 3D animated news explainer built in Blender, like the Professor of Claude ISRO and Cyclone Arnab reels: Claude builds every 3D shot in code (rockets on launch pads, a 3D India map with pins, a storm spiralling over the sea, Earth from space), cuts the camera on your words and pops the numbers in as you say them.
- **56. `/educational-youtube-editor`** — Turn a long lesson recording into a clean, chaptered YouTube edit.
- **63. `/particle-chart`** — Particles pour down and pile up into a bar chart.
- **65. `/price-tag-zoom`** — A slow push-in on a product with a floating price tag.
- **67. `/dark-red-timeline-motion-graphics`** — A dark red grade, a blinking REC tag and an animated timeline.

## Visual treatments and edit styles

- **54. `/depth-ui-reel`** — Floating app interfaces that sit behind my head, with my body cut out in front of them.
- **71. `/red-kinetic-collage-edit`** — Black-and-white footage with one glowing red word and collage-style type.
- **72. `/iphone-style-by-aansh`** — Frosted iOS widgets and notifications floating over my footage.
- **73. `/rgb-glitch-live`** — Split colour channels, torn slices and a live news chyron.
- **74. `/magazine-cover`** — A magazine masthead behind my head, with cover lines around me.
- **77. `/neon-outline`** — A glowing neon outline around me, with neon words.
- **78. `/cinema-scope`** — 2.39:1 film bars, film grain and a title card.
- **79. `/triptych-timecode`** — Three clips side by side, each with its own live timecode.

## Motion effects and formats

- **38. `/crayon-carousel`** — The trending crayon carousel from How to do this with Claude (Ep 3): every slide puts a crayon drawing of your photo on top, labelled “One day”, over the real photo labelled “Day one”, ready to post as an Instagram carousel.
- **52. `/personal-short-form-reels`** — A fast personal reel with my own B-roll and word-by-word captions.
- **53. `/personal-broll-library`** — Search my own B-roll folder in plain English ("me walking at night") and return the best matching clips.
- **55. `/youtube-clips`** — Find the best moments in a long YouTube video and turn each into a vertical clip.
- **57. `/ranking-format`** — A tier-list reel: items ranked one by one, S to F.
- **58. `/business-short-form-reels`** — A reel for business topics, with docs, decks and screen recordings as B-roll.
- **62. `/glass-stat-card`** — A frosted-glass card with a number that counts up live.
- **68. `/instagram-ui-hinglish`** — Instagram profile grids behind me, with tick-mark chips for each point.
- **69. `/hindi-pastel-reel-edit`** — A soft pastel set with one giant word behind my head.

## Cross-cutting core workflows

- Script analysis and style recommendation: `prompts/02-script-intake-and-style-selector.md`
- Create a video: `prompts/03-create-video.md`
- Analyze a reference video: `prompts/04-reference-video-analysis.md`
- Integrate a skill: `prompts/05-integrate-skill-with-factory.md`
- Research upstream projects: `prompts/06-research-upstream-project.md`
- Independent QA: `prompts/07-review-and-qa.md`
- Publishing package: `prompts/08-publish-package.md`

## Core workflow skills

- **`video-director`** — Routes any topic, script, audio, clip, or reference to the right Video Factory workflow and skills.
- **`script-to-storyboard`** — Analyzes a script and creates a style-aware, technically grounded scene plan before rendering.
- **`style-architect`** — Selects and evolves distinct video styles using versioned style cards and checkable visual signatures.
- **`reference-video-analyzer`** — Breaks down an accessible reference video into reusable timing, motion, composition, and storytelling techniques.
- **`factory-skill-integrator`** — Integrates a new skill into the existing Video Factory without duplicating renderers, timelines, or QA.
- **`video-qa-critic`** — Independently reviews rendered video for technical validity, visual quality, audio, captions, style coherence, and accuracy.
- **`publishing-packager`** — Prepares platform-specific titles, descriptions, thumbnail concepts, tags, attribution, and a pre-publish checklist.
