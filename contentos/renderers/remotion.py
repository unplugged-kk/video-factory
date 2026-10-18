"""Remotion rendering provider implementation for Video Factory.

Provides an optional, selectable second video rendering provider using
Remotion (React + TypeScript). Supports spring animations, word-level caption
reveals, multi-scene sequencing, and deterministic frame rendering.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..qa import probe_video
from .base import RenderProvider

REMOTION_DIR = Path.home() / ".contentos" / "remotion"
REMOTION_BIN = REMOTION_DIR / "node_modules" / ".bin" / "remotion"


class RemotionRenderer(RenderProvider):
    """Optional selectable Remotion rendering engine."""

    @property
    def id(self) -> str:
        return "remotion"

    @property
    def version(self) -> str:
        return "4.0.536"

    def capabilities(self) -> dict[str, Any]:
        return {
            "engine": "remotion",
            "formats": ["9:16", "16:9"],
            "features": [
                "react_components",
                "spring_physics",
                "interpolations",
                "word_level_captions",
                "safezone_padding",
                "integrated_audio",
            ],
            "default": False,
        }

    def preflight(self, ctx: dict) -> None:
        if not REMOTION_BIN.exists():
            # Check if npx is available
            npx = shutil.which("npx")
            if not npx:
                raise RuntimeError(
                    f"Remotion executable not found at {REMOTION_BIN} and npx is not on PATH"
                )

    def validate(self, spec: dict) -> list[str]:
        errors = []
        if not spec.get("script"):
            errors.append("Spec missing required 'script' lines")
        return errors

    def compose(self, ctx: dict) -> tuple[str, list[Path]]:
        from ..features import registry as _feat
        from ..pipeline import caption_words, dur, words_for

        spec = ctx["spec"]
        W, H = map(int, ctx["res"])
        proj = ctx["dir"] / "project_remotion"
        proj.mkdir(parents=True, exist_ok=True)
        src_dir = proj / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        pub_dir = proj / "public" / "assets" / "voice"
        pub_dir.mkdir(parents=True, exist_ok=True)

        # Style card hook resolution
        _feat.get("style_card", spec)(ctx, spec)

        # Copy audio voice files into public directory for Remotion StaticFile
        audio_src = ctx["dir"] / "audio"
        for wav in sorted(audio_src.glob("*.wav")):
            shutil.copy(wav, pub_dir / wav.name)

        # Symlink node_modules from ~/.contentos/remotion to avoid per-job npm install
        nm_link = proj / "node_modules"
        if not nm_link.exists() and (REMOTION_DIR / "node_modules").exists():
            try:
                nm_link.symlink_to(REMOTION_DIR / "node_modules")
            except OSError:
                pass

        # Write package.json
        (proj / "package.json").write_text(
            json.dumps(
                {
                    "name": "contentos-remotion-job",
                    "version": "1.0.0",
                    "private": True,
                    "dependencies": {
                        "@remotion/cli": "4.0.536",
                        "react": "^18.2.0",
                        "react-dom": "^18.2.0",
                        "remotion": "4.0.536",
                    },
                },
                indent=2,
            )
        )

        # Write tsconfig.json
        (proj / "tsconfig.json").write_text(
            json.dumps(
                {
                    "compilerOptions": {
                        "target": "es2022",
                        "module": "commonjs",
                        "jsx": "react-jsx",
                        "strict": True,
                        "esModuleInterop": True,
                        "skipLibCheck": True,
                        "forceConsistentCasingInFileNames": True,
                    }
                },
                indent=2,
            )
        )

        # Build scene timing, captions, and layout
        t = 0.0
        scenes_data = []
        fps = 30

        _cap_override = _feat.get("captions_hook", spec)(ctx, spec)

        for i, ln in enumerate(spec["script"], 1):
            wav = audio_src / f"{i:02d}.wav"
            d = round(dur(wav) + 0.35, 2)
            asr = words_for(wav, audio_src / f"tx{i:02d}")
            toks = ln["say"].split()
            wl = caption_words(toks, asr, d)

            tag_text = ln.get("tag", f"{i}/{len(spec['script'])}")
            headline_text = ln["headline"]
            if _cap_override.get("clean_tags"):
                from ..features.captions_hook import clean_tag_and_headline
                is_hook = (i == 1)
                is_cta = (i == len(spec["script"]))
                tag_text, headline_text = clean_tag_and_headline(tag_text, headline_text, is_hook, is_cta)

            start_frame = int(round(t * fps))
            duration_frames = int(round(d * fps))

            words_data = [
                {"word": w, "start_frame": int(round(ws * fps)), "end_frame": int(round(we * fps))}
                for w, ws, we in wl
            ]

            scenes_data.append(
                {
                    "index": i,
                    "tag": tag_text,
                    "headline": headline_text,
                    "say": ln["say"],
                    "voice_path": f"assets/voice/{i:02d}.wav",
                    "start_frame": start_frame,
                    "duration_frames": duration_frames,
                    "words": words_data,
                }
            )
            t += d

        total_duration = round(t, 2)
        total_frames = int(round(total_duration * fps))

        # Safezone margins (G6: bottom >= 460px, right >= 190px, top >= 150px)
        bottom_pad = 460
        side_right = 190
        side_left = 80
        top_pad = 160

        # Generate src/scenes.json for easy component consumption
        (src_dir / "scenes.json").write_text(json.dumps(scenes_data, indent=2))

        # Write src/Video.tsx (React Component)
        (src_dir / "Video.tsx").write_text(f"""import React from 'react';
import {{
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
}} from 'remotion';
import scenes from './scenes.json';

const SceneView: React.FC<{{ scene: any }}> = ({{ scene }}) => {{
  const frame = useCurrentFrame();
  const {{ fps }} = useVideoConfig();

  // Smooth spring entrance for headline
  const entrance = spring({{
    frame,
    fps,
    config: {{ damping: 14, stiffness: 120, mass: 0.8 }},
  }});

  // Smooth exit fade
  const exitProgress = interpolate(
    frame,
    [scene.duration_frames - 8, scene.duration_frames],
    [1, 0],
    {{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }}
  );

  const headlineY = interpolate(entrance, [0, 1], [60, 0]);
  const opacity = interpolate(frame, [0, 6], [0, 1], {{
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  }}) * exitProgress;

  // Modern background palette per scene
  const bgGradients = [
    'radial-gradient(circle at 50% 25%, #1e1b4b, #090a0f)',
    'radial-gradient(circle at 50% 25%, #1e293b, #090a0f)',
    'radial-gradient(circle at 50% 25%, #172554, #090a0f)',
    'radial-gradient(circle at 50% 25%, #14532d, #090a0f)',
    'radial-gradient(circle at 50% 25%, #3b0764, #090a0f)',
    'radial-gradient(circle at 50% 25%, #450a0a, #090a0f)',
  ];
  const bg = bgGradients[(scene.index - 1) % bgGradients.length];

  return (
    <AbsoluteFill
      style={{{{
        background: bg,
        opacity,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        paddingTop: {top_pad},
        paddingBottom: {bottom_pad},
        paddingLeft: {side_left},
        paddingRight: {side_right},
        boxSizing: 'border-box',
        color: '#ffffff',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}}}
    >
      <Audio src={{staticFile(scene.voice_path)}} />
      
      {{/* Top Section: Tag and Headline */}}
      <div style={{{{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}}}>
        {{scene.tag ? (
          <div
            style={{{{
              fontFamily: 'ui-monospace, Menlo, monospace',
              fontWeight: 700,
              fontSize: 32,
              letterSpacing: 3,
              color: '#a5b4fc',
              marginBottom: 32,
              textTransform: 'uppercase',
            }}}}
          >
            {{scene.tag}}
          </div>
        ) : null}}
        <h1
          style={{{{
            fontSize: 76,
            fontWeight: 900,
            lineHeight: 1.15,
            margin: 0,
            letterSpacing: -1,
            transform: `translateY(${{headlineY}}px)`,
            opacity: entrance,
            maxWidth: 880,
          }}}}
        >
          {{scene.headline}}
        </h1>
      </div>

      {{/* Bottom Section: Word-level Active Captions */}}
      <div
        style={{{{
          textAlign: 'center',
          fontSize: 54,
          fontWeight: 800,
          lineHeight: 1.3,
          textShadow: '0 4px 20px rgba(0, 0, 0, 0.8)',
        }}}}
      >
        {{scene.words.map((w: any, idx: number) => {{
          const isActive = frame >= w.start_frame && frame <= w.end_frame;
          return (
            <span
              key={{idx}}
              style={{{{
                color: isActive ? '#fbbf24' : '#ffffff',
                transition: 'color 0.1s ease',
                marginRight: 10,
                display: 'inline-block',
              }}}}
            >
              {{w.word}}
            </span>
          );
        }})}}
      </div>
    </AbsoluteFill>
  );
}};

export const MainVideo: React.FC = () => {{
  return (
    <AbsoluteFill style={{{{ backgroundColor: '#090a0f' }}}}>
      {{scenes.map((sc) => (
        <Sequence
          key={{sc.index}}
          from={{sc.start_frame}}
          durationInFrames={{sc.duration_frames}}
        >
          <SceneView scene={{sc}} />
        </Sequence>
      ))}}
    </AbsoluteFill>
  );
}};
""")

        # Write src/Root.tsx
        (src_dir / "Root.tsx").write_text(f"""import React from 'react';
import {{ Composition }} from 'remotion';
import {{ MainVideo }} from './Video';

export const RemotionRoot: React.FC = () => {{
  return (
    <Composition
      id="MainVideo"
      component={{MainVideo}}
      durationInFrames={{{total_frames}}}
      fps={{{fps}}}
      width={{{W}}}
      height={{{H}}}
    />
  );
}};
""")

        # Write src/index.ts
        (src_dir / "index.ts").write_text("""import { registerRoot } from 'remotion';
import { RemotionRoot } from './Root';

registerRoot(RemotionRoot);
""")

        return "remotion", [src_dir / "Root.tsx", src_dir / "Video.tsx", src_dir / "scenes.json"]

    def render(self, ctx: dict) -> tuple[str, list[Path]]:
        from ..features import registry as _feat

        proj = ctx["dir"] / "project_remotion"
        mp4 = ctx["dir"] / "video.mp4"

        cmd = [
            str(REMOTION_BIN) if REMOTION_BIN.exists() else "npx",
        ]
        if not REMOTION_BIN.exists():
            cmd.extend(["remotion"])

        cmd.extend([
            "render",
            "src/index.ts",
            "MainVideo",
            str(mp4),
            "--public-dir=public",
            "--concurrency=8",
        ])

        env = {**os.environ}
        p = subprocess.run(cmd, cwd=proj, capture_output=True, text=True, env=env)
        if p.returncode != 0:
            raise RuntimeError(f"Remotion render failed with exit code {p.returncode}: {p.stderr[-800:]}")

        if not mp4.exists() or mp4.stat().st_size < 1000:
            raise RuntimeError(f"Remotion render produced missing or empty video: {mp4}")

        # Post-render audio stage (Lane D / audio_bed). Pass-through when off.
        mp4 = _feat.get("audio_bed", ctx["spec"])(ctx, mp4, ctx["spec"])

        return "remotion", [mp4]

    def inspect(self, artifact: Path) -> dict[str, Any]:
        info = probe_video(artifact)
        if not info:
            raise ValueError(f"Unable to probe video artifact: {artifact}")
        return info
