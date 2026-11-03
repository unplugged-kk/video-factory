# Wispr Flow: One-line video request

Use this as the spoken-command contract. Speak naturally; the agent should normalize the request.

## Numbered skill command

"Create video number {NUMBER}. Topic or script: {TOPIC_OR_SCRIPT}. Target platform: {PLATFORM}. Language: {LANGUAGE}. Duration: {DURATION}. If I have not selected a style, analyze the content and recommend the best style and two alternatives. Check which skills and factory capabilities are available, explain the choice briefly, then create a storyboard and preview. Do not full-render until the required approval is given. Do not publish."

## Free-form command

"Create a {FORMAT_OR_STYLE} video about {TOPIC}. Use the attached script/audio/files. First analyze the content, audience, language, length, technical claims, and available assets. Recommend the best visual treatment, identify the skills and existing Video Factory capabilities you will use, and explain any missing capability. Then produce a scene plan and preview. Reuse existing tools and gates. Ask only for essential missing input. Do not install new dependencies, overwrite files, or publish without permission."

## Script-only command

"Here is my script. Do not start rendering yet. Analyze its narrative beats, audience, technical accuracy, likely scene types, pacing, and visual opportunities. Recommend one primary style and two alternatives. Map each scene to the most suitable available skills and animations. Identify unsupported requirements and any claims that need sources. Show me the proposed storyboard and explain the trade-offs before proceeding."
