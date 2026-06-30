#!/usr/bin/env python3
from pathlib import Path

p = Path("app/src/main/java/org/realityczech/app/ui/RealityCzechApp.kt")
s = p.read_text(encoding="utf-8")

if "import org.realityczech.app.BuildConfig\n" not in s:
    s = s.replace(
        "import org.realityczech.app.data.ProgressStore\n",
        "import org.realityczech.app.BuildConfig\nimport org.realityczech.app.data.ProgressStore\n",
        1,
    )

marker = '        Text("About this app", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)\n'
version = '        Text("Version ${BuildConfig.VERSION_NAME} (build ${BuildConfig.VERSION_CODE})")\n'
if version not in s:
    s = s.replace(marker, marker + version, 1)

s = s.replace(
    '        Text("Current status: Unit 1 days 1.1–1.3 include original interview video, device-generated Czech pronunciation, vocabulary playback, and listening practice.")\n',
    '        Text("Current status: Unit 1 days 1.1–1.3 and pronunciation material from 1.5 include original video, bundled human recordings, source-document images, vocabulary playback, and listening practice.")\n',
    1,
)
s = s.replace(
    '        Text("Vocabulary and listening-exercise audio is synthesized by the Czech voice installed on the Android device. It is not an original Reality Czech recording.")\n',
    '        Text("Original human recordings are preferred where available. Android Czech speech is clearly labeled and used only as a fallback or for generated exercises.")\n',
    1,
)

p.write_text(s, encoding="utf-8")
