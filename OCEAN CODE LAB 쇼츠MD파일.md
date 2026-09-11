# OCEAN CODE LAB ENGINEERING SHORTS PRODUCTION SYSTEM (CODEX)

## Overview

This document specifies the full Codex workflow for producing vertical explainer shorts on engineering subjects: architecture, civil and mechanical engineering, aerospace, military engineering, fluid dynamics, structural systems, thermodynamics, pressure systems, and related technical topics.

It is written to stand on its own as the project instruction file. No earlier conversation, custom skill, or hidden context is required.

The production chain is:

```text
Script (supplied by the user)
→ CLEAN keyframes
→ INFO keyframes
→ CLEAN-to-INFO 4-second video clips
→ TTS-synced edit
→ Final publishing package
```

Repeatability matters more than anything else. A stage that has been approved or finished is never rebuilt unless the user explicitly asks for a revision.

---

# A. PROJECT OPERATING RULES

## A1. Tools

Equivalent tools are acceptable, but the intended setup is:

- A working environment with Codex enabled
- One dedicated project folder per topic
- An image generation tool
- An image-to-video generation tool
- A TTS generator
- Premiere Pro or another NLE

Example tools used in class:

- Google Flow
- Any supported image generation model
- Gemini Omni Flash or a comparable image-driven video model

Model names and features change over time. The production logic in this document takes priority over any specific vendor or model.

---

## A2. Starting a New Project

1. Create a folder dedicated to the topic.
2. Open that folder as the Codex working directory.
3. Attach this MD file to a new Codex session.
4. Paste the finished script.
5. Use the initialization prompt below.

```text
Read the attached AION_ENGINEERING_SHORTS_SYSTEM.md from start to finish and treat it as the operating specification for this project.

Topic: [TOPIC]
Target duration: [e.g. 60 seconds / 100 seconds]
Project folder: [ABSOLUTE PATH]
Primary phenomenon to visualize: [air / water / soil / heat / pressure / load / vibration / energy]
Image and video platform: [e.g. Google Flow]
Source clip duration: 4 seconds per clip

This is a new project.

The script above is already final. Do not write a new script and do not edit it. Use it exactly as given.

Read and learn the script first, then stop. Do not move on to scene planning or image generation until the next instruction arrives.

Save every completed stage as an MD file inside the project folder and also provide the same output in a copyable code block in the conversation.

If any stage already exists, inspect the current project state first and continue from the latest completed stage instead of rebuilding earlier work.
```

For an existing project, replace the final instruction with:

```text
Current stage: [e.g. CLEAN images completed]

Inspect the existing project assets and documents first.

Do not rebuild completed stages.

Perform only the next required stage.
```

---

## A3. Resume, Never Restart

Before any new work:

- Inspect existing scripts, manifests, CLEAN assets, INFO assets, MP4 files, prompts, and status files.
- Never regenerate approved or completed work on your own.
- Perform only the stage the user requested.
- If the next stage needs approval, present the output and stop.

---

## A4. Approval Gates

Follow this order unless the user explicitly says to skip one or more stages:

1. Scene plan and keyframe count
2. CLEAN generation prompts
3. CLEAN asset review
4. INFO second-pass prompts
5. INFO asset review
6. 4-second video generation prompts
7. MP4 review and filename ordering
8. Final edit and publishing text

Never pass an approval gate without the user's approval.

If the user explicitly asks for full generation or says to skip testing, follow that instruction.

---

## A5. Recommended Folder Layout

When starting from scratch, use:

```text
[PROJECT]/
  script/
  clean/
  info/
  video/
  edit/
  manifests/
  prompts/
```

If an existing project already uses a different sensible layout, keep it rather than forcing a migration.

Recommended core files:

```text
script/APPROVED_NARRATION_KR.md
manifests/IMAGE_SEQUENCE.md
manifests/PROJECT_STATUS.md
prompts/CLEAN_KEYFRAME_PROMPTS.md
prompts/INFOGRAPHIC_KEYFRAME_PROMPTS.md
prompts/VIDEO_GENERATION_PROMPTS.md
```

---

## A6. Stable Scene and Asset IDs

Use the same IDs across the whole project.

Recommended pattern:

```text
Scene: S01A
Keyframe: KF-01A
Video: CLIP01
```

CLEAN, INFO, and MP4 assets must map 1:1 through a shared scene/keyframe identity.

Use zero-padded numeric prefixes so that alphabetical filename order equals narrative order.

```text
01_S01A_KF-01A_CLEAN_[short-description]
01_S01A_KF-01A_INFO_[short-description]
01_CLIP_S01A_KF-01A_[short-description].mp4
```

---

## A7. Local File Safety

- Create and modify files only inside the project folder the user specified.
- Never overwrite original images or videos.
- Before deleting anything, confirm it is truly a duplicate or invalid.
- Never rely on creation time or filenames alone to determine sequence.
- Verify order from the actual visual content.
- If visual inspection is impossible, do not guess. Ask for, or build, a contact-sheet / representative-frame review workflow.

---

# B. SCRIPT AND TTS DURATION

The script is written and finalized by the user. Codex does not write or rewrite it.

Store the supplied script as-is:

```text
script/APPROVED_NARRATION_KR.md
```

After TTS is generated, record the **actual TTS duration**. Once the real audio length is known, stop using the estimated script duration.

---

# C. STAGE 1 — SCENE MAP AND KEYFRAME COUNT

Use the supplied script and the actual TTS duration.

```text
Using the supplied script and the actual TTS duration of [XX seconds], build the scene and keyframe plan.

Source video clips are 4 seconds each.

In the final edit, roughly 1.5 to 4 seconds of each generated clip may be used.

Create a new scene only when there is a meaningful change in one of the following:

- physical state
- load path
- construction stage
- internal cross-section
- macro mechanism
- scale comparison
- material interaction
- major visual transition

Do not create redundant scenes that differ only by camera angle.

For every scene specify:

- Scene ID
- Keyframe ID
- narration phrase
- scene purpose
- CLEAN visual content
- INFO overlay concept
- expected camera movement

Save all mappings to:

manifests/IMAGE_SEQUENCE.md

Stop after the scene plan.

Do not write image-generation prompts yet.
```

Scene count is not a fixed rule.

Useful starting ranges:

- 55–70 seconds: roughly 16–22 source clips
- 90–110 seconds: roughly 26–36 source clips

The number of real physical states in the narration outranks these estimates.

---

# D. STAGE 2 — CLEAN KEYFRAME PROMPTS

CLEAN images are the base visual assets.

They contain only the real engineering scene, with no explanatory graphics.

Use a prompt along these lines:

```text
Using the supplied script and manifests/IMAGE_SEQUENCE.md, write the complete batch prompt for generating every CLEAN keyframe.

Every keyframe must be an independent vertical 9:16 image.

Do not merge them into a collage, storyboard, contact sheet, or split-screen composition.

Instruct the generation agent to produce the full requested quantity without pausing for confirmation between images.

For each image include:

- scene ID
- keyframe ID
- sortable output filename
- photoreal cinematic 3D engineering-documentary style
- consistent geometry, era, materials, colors, and environment across related scenes
- foreground, midground, and background depth
- enough spatial depth for a later 5–15 degree camera move
- physical state
- viewpoint
- lens feel
- lighting
- material appearance
- scene-specific error-prevention rules
- scene-specific forbidden elements

CLEAN images must NOT contain:

- text
- numbers
- symbols
- dimensions
- dimension lines
- arrows
- callout lines
- formulas
- charts
- maps
- UI
- HUD
- subtitles
- logos
- watermarks
- infographic glow

Show air, water, soil, smoke, dust, heat, particles, or similar effects only when they are physically relevant to the scene itself.

Return the entire batch prompt inside one text code block.

Save it as:

prompts/CLEAN_KEYFRAME_PROMPTS.md

Do not generate images in this stage.
```

### CLEAN Quality Standard

- 9:16 vertical
- Recommended resolution: 1080×1920 or higher
- Enough scene depth for controlled camera motion
- No excessive neon
- No fantasy-energy look
- Leave usable space for later INFO graphics without making the frame look like an empty template
- Keep historical, mechanical, structural, and material inaccuracies to a minimum

---

# E. STAGE 3 — CLEAN ASSET REVIEW

After CLEAN images have been generated externally, review them against the approved scene map.

```text
Review every CLEAN image in the folder below against the approved scene plan.

CLEAN folder:
[ABSOLUTE PATH]

Scene map:
[ABSOLUTE PATH TO IMAGE_SEQUENCE.md]

Check:

- total quantity
- aspect ratio
- actual visual content
- geometry consistency
- continuity of materials and environment
- narration order
- physical state
- camera depth
- absence of INFO graphics
- duplicates
- missing scenes

Do not trust filename or creation time alone.

Inspect the actual image content and map every asset to the correct scene/keyframe ID.

If all assets are valid, rename or prefix them so alphabetical filename order matches narration order.

If an image is wrong, report only:
- affected ID
- exact failure
- reason for regeneration

Do not request full-batch regeneration when only specific images are defective.
```

---

# F. STAGE 4 — INFO SECOND-PASS EDIT PROMPTS

INFO is **not a fresh scene-generation pass.**

INFO is produced by editing the matching CLEAN keyframe.

The underlying CLEAN image must stay visually identical.

Use a prompt along these lines:

```text
Using the reviewed CLEAN images, the supplied script, and manifests/IMAGE_SEQUENCE.md, write the complete second-pass editing prompts that turn each CLEAN image into its INFO version.

Global preservation rules:

Preserve the CLEAN image's:
- camera
- crop
- lens
- geometry
- parts
- people
- physical state
- lighting
- materials
- textures
- environment
- background

Do not redraw the scene.

Do not rotate, reposition, zoom, shrink, enlarge, replace, or redesign the base object.

The INFO layer must read as model-rendered engineering visualization sitting inside real 3D space, not as a flat HUD.

Anchor callout lines and arrows to actual structures and physical phenomena.

All overlays must respect:
- perspective
- parallax
- depth
- occlusion

Use one consistent project-wide color system for:
- normal flow
- pressure / danger
- structural information
- key measurements

Organize the graphic components so the later video can assemble them in this order:

anchor
→ line
→ arrow body
→ arrowhead
→ number
→ label
→ moving pulse / flow cue

Use only verified measurements and units.

The narration carries the explanation and the conclusion.

So do not default to giant titles or sentence-length headings.

Each scene should normally contain:
- 1 to 3 small technical labels
- 0 to 1 critical numeric value

The main visual subject remains the physical phenomenon, flow, wave, force path, load path, or engineering mechanism.

Only special conclusion scenes may use a short medium-sized statement.

If the matching CLEAN image already exists in the current image-generation conversation, refer to it by its ID instead of asking the user to upload it again.

Return all prompts inside one text code block.

Save them as:

prompts/INFOGRAPHIC_KEYFRAME_PROMPTS.md

Do not generate INFO images in this stage.
```

### Example INFO Color Logic

A consistent project palette might use:

- normal flow / acoustic wave / streamline: cyan or teal
- sudden pressure change / impact / danger: orange to red
- moisture / cooling / condensation: white and pale blue
- velocity / key metric / final highlight: gold
- structural / neutral callout line: restrained blue-white

The exact palette may vary by topic, but it must stay consistent through the whole video.

---

# G. STAGE 5 — INFO REVIEW

Compare CLEAN and INFO assets 1:1 by ID.

```text
Compare every CLEAN and INFO image pair using their shared IDs.

CLEAN folder:
[ABSOLUTE PATH]

INFO folder:
[ABSOLUTE PATH]

Scene map:
[ABSOLUTE PATH TO IMAGE_SEQUENCE.md]

Verify:

- INFO is truly an edit of the same CLEAN composition
- camera is preserved
- geometry is preserved
- people are preserved
- lighting is preserved
- background is preserved
- approved numbers and units are correct
- callout lines end on real components or phenomena
- force / pressure / fluid arrows point the right way
- graphics respect perspective and occlusion
- no giant title dominates the frame
- each image communicates one primary concept
- no assets are missing
- no duplicates exist
- IDs are correct

If a problem exists, report only the affected ID and the exact element that must be corrected.

Do not request regeneration of the entire set.
```

---

# H. STAGE 6 — CLEAN-TO-INFO 4-SECOND VIDEO PROMPTS

Each clip starts from CLEAN and builds progressively toward INFO.

CLEAN is the true opening frame.

INFO is the target reference for the final graphic state.

INFO must never be treated as the opening frame or as a flat board that simply moves.

Use a prompt along these lines:

```text
Using the approved CLEAN–INFO pairs and manifests/IMAGE_SEQUENCE.md, write the complete image-to-video prompts for independent 4-second engineering clips.

Asset roles:

CLEAN:
- true opening frame
- source of scene geometry
- source of camera framing
- source of lighting
- source of materials

INFO:
- target reference for final graphic content
- target reference for final labels
- target reference for final values
- target reference for overlay positions
- target reference for final colors and composition

Do not use INFO as the first frame.

Do not move INFO as a flat image plate.

Instead, start from CLEAN and progressively construct the infographic elements over the real scene until the final state visually converges on INFO.

Default 4-second construction timing:

0.0–0.4 s
CLEAN only.
Camera movement and natural environmental motion begin.

0.4–0.9 s
Engineering anchor points light up or appear on the relevant structures / phenomena.

0.9–1.7 s
Callout lines, wavefronts, dimension lines, flow paths, or arrow bodies construct outward.

1.7–2.6 s
Small Korean technical labels and verified numeric values assemble.
Arrowheads appear only after their lines or bodies have formed.

2.6–3.4 s
Load, pressure, fluid, material, process, or energy pulses travel along their intended paths.

3.4–4.0 s
The composition settles into the final INFO target state and stays readable.

Global video rules:

- each result is a separate 4.0-second clip
- vertical 9:16
- one continuous shot
- no cuts
- only one restrained camera move per scene
- camera movement generally stays within roughly 5–15 degrees
- allowed movement styles include subtle orbit, dolly, or tracking
- camera and graphics move independently
- graphics stay anchored to real 3D space
- preserve perspective
- preserve parallax
- preserve occlusion
- every flow has a start point, direction, interaction boundary, and result
- do not invent a giant title that is not in INFO
- do not add new subtitles

Forbidden:

- simultaneous full-screen fade-in of all graphics
- flat HUD appearance
- jittering text
- reversed arrows
- excessive neon
- fantasy energy
- structural morphing
- object duplication
- 360-degree rotation
- whip pans
- camera roll

Do not generate:
- narration
- dialogue
- music
- new subtitles
- logos
- watermarks

Prefix final filenames with zero-padded numbering starting at CLIP01.

For each clip specify:

- CLEAN source ID
- INFO target ID
- output filename
- camera movement
- anchor location
- graphic build order
- moving pulse behavior
- occlusion behavior
- physical direction

Return all prompts inside one text code block.

Save as:

prompts/VIDEO_GENERATION_PROMPTS.md

Do not generate videos in this stage.
```

If the same generation conversation already holds the matching CLEAN and INFO assets, prepend:

```text
The CLEAN and INFO images with matching KF IDs already exist in this conversation.

CLEAN is the real starting image.

INFO is the final target-state reference.

Do not use INFO as the first frame.

Reconstruct the graphics progressively on top of CLEAN until the clip reaches the INFO target state.

Do not ask the user to upload the same images again.
```

If a new generation conversation is used, supply each CLEAN–INFO pair while keeping the exact filenames and IDs.

---

# I. STAGE 7 — MP4 REVIEW AND ORDERING

Review generated video content visually.

Do not rely on file creation time or filenames alone.

```text
Review the MP4 folder against the INFO image folder and the approved scene map using actual visual content.

INFO folder:
[ABSOLUTE PATH]

MP4 folder:
[ABSOLUTE PATH]

Scene map:
[ABSOLUTE PATH TO IMAGE_SEQUENCE.md]

Compare a representative frame from every MP4 with its intended INFO image.

Check:

- image-to-video scene correspondence
- narration order
- missing clips
- duplicated clips
- clip duration
- aspect ratio
- CLEAN opening state
- progressive infographic construction
- independent camera and graphic motion
- geometry stability
- direction of forces and flows
- readability of the final INFO state

After verifying the actual scene content, prefix filenames with 01_, 02_, 03_ and so on so alphabetical filename sorting matches narration order.

Preserve the descriptive portion of each filename.

If deletion of duplicates is necessary, explain the evidence first.

Do not delete anything without approval.
```

---

# J. STAGE 8 — FINAL EDIT

Generated source duration and final narration duration are not expected to match.

Example:

```text
19 clips × 4 seconds = 76 seconds of source footage
Actual TTS = 64 seconds
```

The final edit may therefore drop roughly 12 seconds.

Typical usage:

- problem setup / transitional scene: about 1.5–3 seconds
- central mechanism / payoff scene: about 3–4 seconds
- scene where the graphic build finishes late: keep enough of the completed graphic state
- visually repetitive camera movement: shorten aggressively

In Premiere Pro or another NLE:

1. Sort the project panel by filename ascending.
2. Select clips from 01 through the final numbered clip.
3. Place them on the timeline in that order.

Recommended edit order:

```text
TTS
→ adjust clip durations
→ essential sound effects
→ background music
→ minimal necessary subtitles
→ volume balancing
→ color cleanup
→ final review
```

---

# K. STAGE 9 — TITLE AND DESCRIPTION PACKAGE

Use a prompt along these lines:

```text
Create the YouTube title and description for the completed engineering short.

Topic:
[TOPIC]

Final duration:
[XX seconds]

Central engineering question:
[QUESTION]

Main mechanism:
[MECHANISM]

Provide:
- 1 recommended title
- 3 alternative titles

Build strong curiosity without false or exaggerated engineering claims.

Write the description in this order:

1. engineering mystery / problem
2. short explanation of the main mechanism
3. the physical flow / force shown in the video
4. short disclosure that some phenomena were visually simplified for clarity
5. relevant Korean and English hashtags
```

---

# L. MASTER QUALITY CONTROL

## CLEAN

Confirm that:

- no infographic, text, or number appears
- geometry and materials stay consistent
- depth exists for later camera movement
- physical phenomena look realistic

## INFO

Confirm that:

- the underlying CLEAN camera and scene are unchanged
- graphics sit inside 3D scene space rather than acting like a flat HUD
- arrows and callout lines are anchored to real physical locations
- no oversized title needlessly repeats the narration
- only small labels and critical values remain

## VIDEO

Confirm that:

- the clip begins from CLEAN
- graphics build progressively
- camera and graphics move independently
- perspective, parallax, and occlusion stay stable
- forces and flows move in the correct physical direction
- the final INFO state is readable

## FILES

Confirm that:

- narration, CLEAN, INFO, and MP4 assets share correct IDs
- no numeric sequence is missing or duplicated
- alphabetical filename order equals narration order
- originals were not overwritten or accidentally deleted

---

# M. FAST EXECUTION MAP

```text
Attach this workflow to a new Codex session
→ paste the finished script
→ generate TTS
→ record actual TTS duration
→ finalize scene map and IDs
→ write CLEAN prompts
→ generate CLEAN assets externally
→ review CLEAN assets visually
→ write INFO second-pass prompts
→ generate INFO edits from matching CLEAN assets
→ review CLEAN–INFO pairs
→ write 4-second CLEAN-to-INFO video prompts
→ generate clips externally
→ review MP4 content and ordering
→ edit in Premiere Pro or another NLE
→ generate title and description
```

The invariant production chain is:

```text
SCRIPT
→ CLEAN
→ INFO
→ VIDEO
```

Never trade these away for speed:

- approval gates
- visual inspection
- one-to-one asset mapping
- stable IDs
- physical accuracy
- continuity between CLEAN and INFO
- correct CLEAN-to-INFO animation direction

---

# N. COMPLETION RULES

A stage counts as complete only when its required file exists, the output has been reviewed, and the relevant IDs match the project manifest.

Do not infer completion from filenames alone.

When a defect affects a single asset, repair only that asset.

Do not restart the full pipeline unless the user explicitly asks for a full rebuild.

For any uncertain engineering measurement or important factual claim, prefer official or reliable primary references.

Generated structures, aircraft, machinery, and internal mechanisms may contain visual inaccuracies and must be reviewed before publication.

External model capabilities, prices, limits, and product names may change over time.

Copyright, licensing, trademarks, music usage, image usage, and third-party asset rights must be checked separately before publication.

---

# O. PROJECT STATUS HANDOFF

At the end of every completed stage, update:

```text
manifests/PROJECT_STATUS.md
```

The status file contains:

```text
Project:
Topic:
Target duration:
Actual TTS duration:
Current approved stage:
Last completed asset ID:
Next required stage:
Known defects:
Regeneration required:
Pending user approval:
```

When the project is reopened in a new session, inspect this status file together with the actual folders and manifests before continuing.

The project always resumes from the latest verified state, never from assumptions.
