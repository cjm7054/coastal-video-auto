# **OCEAN CODE LAB 공학 숏츠 프롬프트**

&nbsp;

**사용 순서:** 첫 번째 프롬프트(코덱스) → 두 번째 프롬프트(플로우) → 세 번째 프롬프트(코덱스 → 결과를 플로우에 붙여넣기) → 파일 이름 정렬 프롬프트(코덱스)

붙여넣는 프롬프트는 전부 영문입니다. 대본과 이미지 안에 들어가는 글자는 한국어로 나오도록 프롬프트 안에 규칙이 들어 있습니다.

**준비:** 코덱스 새 세션에 영문 MD 파일(AION\_ENGINEERING\_SHORTS\_SYSTEM.md)을 먼저 붙여넣고 엔터 → 대본을 붙여넣고 엔터 → 그다음 아래 첫 번째 프롬프트를 사용합니다.

&nbsp;

# **첫 번째 프롬프트**

&nbsp;

**붙여넣는곳:** 코덱스

**주의:** 첫 줄의 **(XX)** 부분을 실제 음성 길이(초)로 반드시 바꾼 뒤 붙여넣으세요. 안 바꾸면 코덱스가 장면 수를 마음대로 늘립니다.

**결과:** 공통 스타일 한 문단 \+ 장면별 이미지 프롬프트. 이 결과 전체를 복사해서 플로우에 붙여넣으면 CLEAN 이미지(인포그래픽 없는 이미지)가 일괄 생성됩니다. 플로우 세팅은 에이전트 설정 → 9:16, ×1, 이미지 모델 나노바나나 2, 동영상 모델 옴니 1.1 플래시.

&nbsp;

The script is **(XX)** seconds long. Keep the script exactly as it is.

Analyze the script above, divide it into an appropriate number of scenes that follow the flow of the video, and write an image-generation prompt for each scene.

Each scene should run about 3 to 4 seconds and must never exceed 5 seconds.

Every image should look like a keyframe from a high-quality 3D infographic video that makes engineering principles, scientific principles, structures, mechanisms, historical facts, or everyday knowledge easy to understand visually.

Do not add any infographic elements yet: no explanatory text, subtitles, arrows, numbers, labels, or icons.  
Write the prompts so that only the scene itself is generated: background, objects, structures, people, machines, natural phenomena.

Apply the following standards to every scene.

\* 9:16 vertical video  
\* High-quality 3D rendering  
\* Clear, intuitive structure  
\* Visualization that makes the real structure and principle easy to grasp  
\* Strong sense of depth and dimension  
\* Dynamic, cinematic camera composition  
\* The key subject clearly visible in every scene  
\* Avoid overly busy backgrounds; keep attention on the subject being explained  
\* When the same subject appears in several scenes, keep its design, color, shape, and materials consistent  
\* Keep the overall 3D graphic style and lighting quality unified across scene changes  
\* Use cross-sections, cutaways, exploded views, magnified views, or see-through views where helpful  
\* Rather than a plain photorealistic photo, aim for the clear, striking look of an educational 3D documentary / engineering visualization

Output format: Do not consult other skills or external files. Output the entire result as one continuous plain-text block with no code blocks. At the top, write the common style once as a single paragraph. Then, for each scene, write four lines in this order, each on its own line: "number. scene title", "시간: start–end", "대본: script line", "이미지 프롬프트: prompt". The image prompt itself must be one paragraph without line breaks. Do not include tables, summaries, or production notes.

&nbsp;

# **두 번째 프롬프트**

**붙여넣는곳:** 플로우 (CLEAN 이미지가 생성된 같은 대화에서)

**결과:** CLEAN 이미지마다 인포그래픽이 들어간 INFO 이미지가 한 장씩 생성됩니다. 원본이 15장이면 결과도 15장.

Edit every currently selected or provided source image individually, one by one.

Treat each source image as a separate, independent editing job, and produce exactly one infographic-enhanced image per source image.

If there are 15 source images, there must be exactly 15 result images, and the one-to-one correspondence between source order and result order must be kept.

Do not edit only the first image or only the most recent image. Do not merge several source images into one, and do not create collages, grids, multi-panel layouts, split screens, or composites. Do not skip, merge, reorder, replace, or reuse any source image.

Each result must be built only from its own single source image. Do not pull people, objects, buildings, backgrounds, or graphic arrangements from any other source image.

\#\# Purpose

The goal is not to redesign the source scene or regenerate it as a different scene.

Keep each source image's scene, key subject, composition, camera angle, perspective, layout, buildings, structures, machines, vehicles, terrain, natural environment, lighting, color, and visual identity as intact as possible, and add only infographic elements that make the subject faster and easier to understand.

Do not zoom, crop, or significantly change the camera angle. Do not reinterpret the key subject into a different form or replace it with an entirely new scene.

\#\# Core visual rules

Never make the infographic effects small or subtle. Every key graphic element must be large, sharp, and vivid enough to register instantly on screen.

Make arrows, rings, outlines, highlight areas, path lines, callout lines, measurement lines, data markers, and other key infographic elements thick and large, scaling them up boldly to occupy a substantial part of the frame where needed.

Actively combine a wide range of high-saturation colors such as bright red, electric blue, cyan, yellow, orange, green, purple, and magenta. Within a single image, separate different pieces of information with clearly different colors. Avoid colors close to the background and always create strong contrast.

Use at least two or three distinct accent colors per image, but do not repeat the same combination on every image; pick the colors that stand out best against each background and subject.

Make active use of glow, neon glow, bright outlines, translucent color planes, light trails, scan effects, energy lines, and layered graphics with depth. However, do not add meaningless decoration for the sake of flashiness; every large graphic effect must connect directly to the real subject being explained.

\#\# Architecture and engineering focus

Analyze each source image's subject and explanatory purpose individually, then choose graphic elements that actually help explain architecture and engineering.

Prioritize visualizing the following:

\- Building structure and framing  
\- Key members such as columns, beams, slabs, walls, and foundations  
\- Load transfer direction and supporting structure  
\- Interior spaces and floor-to-floor relationships  
\- Circulation and movement flow  
\- System flows such as piping, ducts, electrical, mechanical, and drainage  
\- How machines or structures operate  
\- Connections between components  
\- Cutaways, cross-sections, see-through views, exploded views  
\- Height, depth, distance, angle, range, scale  
\- Before/after, problem/solution, cause/effect comparisons  
\- Process order, construction stages, operating stages  
\- Force, pressure, heat, fluid, energy, vibration, rotation, speed, and flow

Where helpful, make part of the subject transparent or cut it away to reveal internal structure, without breaking the identity of the source.

\#\# Available infographic elements

Use only the elements that actually help each image's content.

\- Large, clear directional arrows  
\- Highlight rings, circles, arcs, rotation markers  
\- Magnifier circles and partial zoom-ins  
\- Glowing connector lines and path lines  
\- Flow lines, circulation diagrams, fluid-flow markers  
\- Motion trails, speed lines, afterimages  
\- Cross-sections, cutaways, see-through views, exploded views  
\- Simplified structural and operating diagrams  
\- Flow diagrams showing process and sequence  
\- Step-by-step progress markers  
\- Measurement lines for length, height, depth, angle, range  
\- Key figures and data points  
\- Name labels with callout lines  
\- Color highlighting of specific structures or areas  
\- Before/after and cause/effect comparisons  
\- Simple bar, ring, or line data visuals

Do not add random decoration unrelated to the information, arrows pointing at nothing, unsupported figures, or unnecessary charts.

\#\# Integration with the source scene

Graphics must not look like flat stickers pasted over the whole frame. Recognize the source image's camera angle, perspective, and spatial depth, and place graphic elements as if they exist inside real three-dimensional space.

Place graphics in front of, behind, above, below, or around the subject as appropriate, and let some elements follow the subject's surface or movement path naturally.

Callout lines and arrows must point at the exact subject or area, and must not cover key structures, important components, people's faces, vehicle shapes, or the main structure of buildings.

Where possible, place information in the source's empty space or along the frame edges, and connect it to the key subject with callout lines.

\#\# Absolute Korean text rule

All titles, labels, explanations, annotations, captions, numeric descriptions, units, and any other readable information inside the image must be written in natural, accurate Korean.

Never use English inside the image. Do not generate English words, English abbreviations, Roman letters, meaningless pseudo-English, or sentences mixing Korean and English.

Numbers may be used when needed, but the units and descriptions attached to them must be in Korean. Instead of English units, use easy-to-read Korean forms such as '미터', '제곱미터', '킬로그램', '초', '도'.

All Korean text must remain readable on a small mobile screen: bold modern typeface, sufficiently large size, short concise wording, strong contrast, clean spacing, and safe margins.

Do not include long paragraphs, tiny text, or an excessive number of labels.

\#\# Information accuracy

Do not invent figures, names, places, operating principles, or cause-and-effect relationships that cannot be confirmed from the image and the given context. Visualize only information that can be judged with confidence. Omit uncertain content rather than guessing.

\#\# Final visual quality

The final result must look like a keyframe from a high-quality educational documentary, a premium YouTube infographic video, or a professional architecture/engineering explainer.

Use a modern, cinematic, energetic, polished visual style. Combine strong color contrast, brightness, glow, depth, dimensionality, layering, clear information hierarchy, and a tidy composition.

Every result should be vivid, dramatic, and instantly eye-catching, but every graphic element must serve to help the viewer understand the source image's content faster and more accurately.

\#\# 1\) Sentence that makes the infographic occupy a large area

Infographic elements must be highly visible on screen; do not tuck them away as small supporting decoration, but render them large and clear enough to occupy a substantial area of the frame. Place important explanatory elements at bold sizes and strong contrast so the viewer recognizes them instantly.

\#\# 2\) Sentence that enforces varied color emphasis

The infographic in each scene must not rely on one or two dull colors; actively combine diverse high-saturation accent colors such as red, electric blue, cyan, yellow, orange, green, purple, and magenta for a rich, colorful look. Within a single scene, clearly separate different pieces of information with different colors.

\#\# 3\) Sentence that strengthens fast zoom-in / zoom-out

In scenes with a fast zoom, use a short, sharp zoom-in or zoom-out that the viewer feels immediately. Not a slow scale change, but an impactful camera move that snaps quickly into, or out of, the key subject or structure.

\#\# 4\) Sentence that makes the infographic and the zoom hit together

In scenes with a fast zoom, have the infographic activate more strongly at the same time as the camera move. For example, highlight rings, glowing outlines, callout lines, and key labels appear in sequence with the zoom-in, and boundary lines, comparison graphics, and path lines expand across the whole frame with the zoom-out.

\#\# Final batch rules

Process every provided or selected source image to the end.

Produce exactly one separate result image per source image.

Keep the input order of the sources identical to the output order of the results.

If there are 15 source images, there must be exactly 15 result images.

Do not stop after the first image. Do not apply effects to only the most recent image. Do not use one source image as the shared reference for all the others.

Forbidden: missing sources, merged sources, reordering, duplicated images, replaced images, collages, grids, multi-panel layouts, split screens, multiple scenes in one image, large-scale regeneration of the source scene, covering the key subject, English text, broken Korean, meaningless numbers, unsupported information, random decoration, low contrast, graphics too small to see, unreadable text.

Every result image must keep the same aspect ratio as its source. Do not arbitrarily change the source ratio to 16:9, 9:16, 1:1, or any other ratio.

# **세 번째 프롬프트**

&nbsp;

**붙여넣는곳:** 코덱스

**결과:** 장면별 플로우 동영상 생성 프롬프트. 이 결과를 복사해서 플로우에 그대로 붙여넣으면 각 장면의 CLEAN·INFO 두 이미지를 기준으로 영상이 일괄 생성됩니다.

&nbsp;

Using the two images for each scene created above, write the prompts that will actually be used for Flow video generation.

The actual image files are not in this conversation and will not be provided. Do not ask for them. Work from the scene list and image prompts written above: the start image of each scene is what its image prompt describes, and the end image is that same scene with the infographic elements (arrows, rings, callout lines, Korean labels, figures) added on top. Write every video prompt based on those descriptions.

Each scene has two images:

\- Start image: the original 3D scene with no infographics  
\- End image: the same scene with infographic elements added

Design each video so that it keeps the start image's key subject, structure, spatial relationships, background, lighting, color, and design as much as possible, while the end image's infographic elements are generated and expanded step by step over time, so that the final frame naturally matches the end image.

Do not settle for a simple fade transition or a plain zoom over a still image.

The two most important things are:

1\. Dynamic camera movement that explores real 3D space  
2\. Real movement of the subjects and environment in the scene \+ infographic motion graphics that explain that movement

In other words, every scene must take the form of "a moving 3D scene \+ a camera traveling through real space \+ infographics that explain the movement."

\#\# 1\. 3D-space camera direction

The camera should not merely scale or slide the image as a 2D effect; it should feel like it physically moves through a 3D space with real depth.

Depending on the scene, actively choose movements such as:

\- Fast approach from a wide overall view toward the key subject  
\- Descending from above or rising from below  
\- Entering a building, machine, or structure from the outside into its interior or cross-section  
\- Forward dive toward a specific component or structure  
\- Tracking along a path such as a pipe, road, railway, cable, blood vessel, or fluid channel  
\- Orbiting the key subject, then approaching the interior or a specific spot  
\- Strong parallax passing between foreground and background  
\- Cinematic fly-through inside or between structures  
\- Wide-to-detail or detail-to-wide moves between the whole structure and its parts

Camera movement must connect to the informational flow of the script.

Do not write abstract phrases like "dynamic camera movement." For each scene, specify the camera's start position, direction of travel, target subject, moment of entry, and final position concretely.

\#\# 2\. Cross-sections and internal structure

When the script explains internal structure, mechanical principles, underground spaces, building interiors, geological layers, the inside of the body, piping, engines, or equipment, do not simply float graphics over an exterior shot.

Where possible, direct it in this flow:

1\. Show the exterior or the overall structure  
2\. Camera approaches the key location  
3\. Outer wall, surface, or upper structure becomes transparent or is cut away  
4\. Interior or cross-section is revealed naturally  
5\. Camera moves closer to the interior or cross-section  
6\. Real operation, movement, or flow begins  
7\. Infographics appear following that movement  
8\. Finally, match the completed state of the end image

Cross-section transitions should look like a spatial change where the actual 3D structure opens or is cut, not a plain fade.

\#\# 3\. Movement within the scene

Do not let camera movement substitute for all movement in the video.

Based on the subjects and environment present in the start image, make the scene itself move naturally.

Examples:

\- Vehicles, trains, aircraft, ships actually move  
\- Machine parts rotate, reciprocate, operate  
\- Water, smoke, fire, steam, clouds, light, particles flow or change naturally  
\- If people are present, apply natural motion such as gaze, gestures, walking  
\- In science and engineering scenes, fluid, heat, pressure, energy, force, speed, and motion move first as real phenomena

Link the infographics so they explain this real movement.

Do not create new people, buildings, vehicles, machines, terrain, or key structures, and do not remove existing elements.

\#\# 4\. Infographic motion

Do not make the infographics small or subtle; render them large and sharp enough to be seen instantly on a mobile screen.

Actively use high-saturation, high-contrast colors such as deep red, electric blue, cyan, yellow, green, and magenta, and separate different pieces of information with different accent colors.

Use the following elements as suited to the subject:

\- Thick arrows  
\- Highlight rings, circles, arcs  
\- Glowing outlines  
\- Boundary lines  
\- Translucent highlight areas  
\- Connector lines and path lines  
\- Light trails  
\- Scan effects  
\- Energy lines  
\- Light-up effects  
\- Waves  
\- Callout lines  
\- Measurement lines  
\- Data displays  
\- Map / route / location highlights  
\- Timelines  
\- Comparison graphics  
\- Cross-section and structure highlights

Graphics are not decoration; they must explain the scene's content.

Do not show all graphics at once; bring them in step by step in this order:

1\. Highlight the key subject or area  
2\. Generate the main graphics: arrows, rings, boundaries, path lines  
3\. Labels, figures, explanatory elements appear  
4\. Additional graphics expand or connect  
5\. Match the completed infographic state of the end image

Prefer motion where lines are actually drawn, rings expand, paths progress, areas light up, and data pops in, rather than simple fades.

\#\# 5\. Automatic adaptation by subject

Automatically choose suitable movement and graphics according to each scene's script content.

Science / engineering:  
Express force, energy, pressure, heat, speed, flow, operating principles, and structural transfer through motion

History:  
Express years, era changes, maps, movement routes, event order, and territorial change through timelines and path animation

Geography:  
Express location, borders, distance, direction, routes, and terrain relationships through map-style graphics

Architecture:  
Express building structure, spatial relationships, cross-sections, floors, height, circulation, and connections through camera movement and cutaway direction

Transport:  
Express vehicle movement, direction, speed, networks, bottlenecks, and routes through tracking cameras and path graphics

Economy / society:  
Express increase/decrease, comparison, ratio, flow, and cause/effect through data-style motion

Everyday knowledge / education:  
Express subject emphasis, comparison, order, process, spatial relationships, and cause/effect intuitively

\#\# 6\. Fast zoom and impact

Review all scenes first, then use a fast zoom selectively in roughly one out of every three scenes.

Do not repeat it in every scene, and avoid the same style of fast zoom in adjacent scenes.

Allowed:

\- Fast zoom-in from a wide view to the key subject  
\- Fast zoom-out from a detail to the whole structure  
\- Snap zoom that pinpoints a specific part, building, terrain feature, or structure  
\- Fast entry from the whole into the internal structure  
\- Fast pull-out from internal detail to the overall context

Where possible, link the fast zoom with the infographics.

Examples:

\- Highlight ring and glowing outline activate together with the zoom-in  
\- Boundary lines and path lines expand together with the zoom-out  
\- Key label and figure pop up right after a snap zoom

Keep fast zooms short and sharp, and avoid excessive camera shake.

\#\# 7\. Source preservation rules

Preserve the start image's key subject, structure, spatial relationships, background, lighting, color, and design.

However, camera position and viewpoint may be changed actively for the sake of conveying information.

Preserving the source does not mean locking the camera.

Exploring the existing 3D space from various distances and angles, and approaching interiors or cross-sections, is actively allowed.

Do not create new key subjects or structures, and do not delete existing elements.

Keep all on-screen text based on the Korean text present in the end image, and do not generate new English text.

Keep the Korean text as stable as possible during motion so it does not break or morph into other characters.

\#\# 8\. Final video flow

Each scene basically follows this flow:

Moving clean 3D scene → camera explores the space → key subject highlighted → real phenomena and subject movement → infographics generated in sequence → cutaway / interior entry if needed → completed end image

Do not repeat the same camera movement or graphic entry style in every scene; vary it to suit the script and structure.

\#\# Output format

Write each scene in the following format.

Scene number:

Script segment:

Camera movement:

3D-space camera path:

Cross-section / interior entry:

Fast zoom used:

Movement within the scene:

Infographic appearance order:

Flow video generation prompt:

Write the Flow video generation prompt as one concrete paragraph that can be entered directly into the generator.

Each prompt must clearly include:

\- What changes from the start image to the end image  
\- The camera's start and end positions  
\- Which direction the camera moves  
\- Which subject it approaches or moves away from  
\- Which spatial move it makes: up, down, forward, backward, rotation  
\- If there is a cross-section or interior entry, when and how it happens  
\- How the subjects and environment in the scene move  
\- How the real movement and the infographics are linked  
\- Which graphics are generated in which order  
\- Which elements glow, expand, move, light up, or are drawn  
\- If there is a fast zoom, at what moment and toward which subject  
\- An instruction that the final frame should naturally match the end image

For every scene, write a concrete, executable prompt ready to be used directly for Flow video generation.

\#\# 8-second video camera structure rule

Each video should hold one and the same 3D space for about 8 seconds while using 2 to 3 connected stages of camera viewpoint change.

Do not stretch a single camera movement across the full 8 seconds.

The basic structure is:

\- Early: a wide viewpoint that lets the viewer understand the overall structure and situation  
\- Middle: a viewpoint approaching the key subject or structure, or entering the interior / cross-section  
\- Late: the viewpoint that shows the key principle or the completed infographic most clearly

Do not cut abruptly between viewpoints as if they were separate scenes; let the camera move continuously within one 3D space so they connect naturally.

Example:  
Overall structure → camera approaches the key subject → moves along the interior or cross-section → final viewpoint emphasizing the key part

Or:

Detail structure → camera moves sideways tracking the operating principle → pulls out quickly to a final viewpoint showing the whole structure together with the infographic

The purpose is to secure usable segments that fit my intent, rather than using all 8 seconds in the final video: cutting out only the useful part, such as using just the first 4 seconds or just the last 4 seconds. Create a clear, highly usable camera composition in each of the early, middle, and late segments so that each segment can be cut and used independently and still look natural.

The camera movement in each segment should differ, but keep the subject's shape and structure, background, lighting, and color consistent.

&nbsp;

# **파일 이름 정렬 프롬프트**

&nbsp;

**붙여넣는곳:** 코덱스

**순서:** 플로우 화면 우측 상단 점 세 개 → 프로젝트 다운로드 → 압축 해제 → 저장된 폴더 경로를 복사해 코덱스에 붙여넣고, 아래 프롬프트를 함께 입력합니다. 코덱스가 대본 순서대로 파일에 번호를 붙입니다.

**그다음:** 캡컷 좌측 상단 가져오기 → 정렬 기준 이름 A부터 Z → 전체 드래그해서 타임라인에 배치 → 음성과 타이밍 맞춰 편집.

&nbsp;

Rename the files by adding sequential numbers such as 01, 02, 03, and so on at the beginning of each filename, following the exact order of the script you have worked on so far. Keep the file order consistent with the script sequence.

**밤새 고민해서 만들었습니다**  
**무료 프롬프트, 만족하셨다면**

**영상에 하이프와 응원의 댓글 한마디**&nbsp;

**꼭 한번씩만 부탁드립니다\!**

**감사합니다 :)**