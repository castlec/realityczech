package org.realityczech.app.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.realityczech.app.model.LearningResource
import org.realityczech.app.model.TranscriptLine

@Composable
fun LessonMediaSection(
    resources: List<LearningResource>,
    transcript: List<TranscriptLine>,
) {
    val videos = resources.filter { it.isEmbeddedVideo }
    val otherResources = resources.filterNot { it.isEmbeddedVideo }

    if (videos.isNotEmpty()) {
        EmbeddedVideoSection(videos = videos, transcript = transcript)
    }

    if (otherResources.isNotEmpty()) {
        Text("Other sources", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        otherResources.forEach { resource -> ExternalResourceCard(resource) }
    }

    if (videos.isEmpty() && transcript.isNotEmpty()) {
        StaticTranscript(transcript)
    }
}

@Composable
private fun EmbeddedVideoSection(
    videos: List<LearningResource>,
    transcript: List<TranscriptLine>,
) {
    var selectedIndex by remember(videos) { mutableIntStateOf(0) }
    var transcriptVisible by remember { mutableStateOf(false) }
    var seekSeconds by remember { mutableStateOf<Int?>(null) }
    val selectedVideo = videos[selectedIndex.coerceIn(videos.indices)]
    val selectedTranscript = transcript.filter {
        it.mediaId.isBlank() || it.mediaId == selectedVideo.mediaId
    }

    Text("Watch and listen", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)

    if (videos.size > 1) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            videos.forEachIndexed { index, video ->
                if (index == selectedIndex) {
                    Button(
                        onClick = { selectedIndex = index },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(video.title) }
                } else {
                    OutlinedButton(
                        onClick = {
                            selectedIndex = index
                            transcriptVisible = false
                            seekSeconds = null
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(video.title) }
                }
            }
        }
    } else {
        Text(selectedVideo.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
    }

    YouTubePlayer(
        videoId = selectedVideo.mediaId,
        seekToSeconds = seekSeconds,
    )

    if (selectedVideo.note.isNotBlank()) {
        Text(selectedVideo.note, style = MaterialTheme.typography.bodySmall)
    }

    val uriHandler = LocalUriHandler.current
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        if (selectedTranscript.isNotEmpty()) {
            TextButton(onClick = { transcriptVisible = !transcriptVisible }) {
                Text(if (transcriptVisible) "Hide transcript" else "Show transcript")
            }
        }
        TextButton(onClick = { uriHandler.openUri(selectedVideo.url) }) {
            Text("Open source page")
        }
    }

    if (transcriptVisible) {
        Text(
            "Listen once before relying on the transcript.",
            style = MaterialTheme.typography.bodySmall,
        )
        selectedTranscript.forEach { line ->
            TranscriptRow(
                line = line,
                onSeek = line.startSeconds?.let { seconds -> { seekSeconds = seconds } },
            )
        }
    }
}

@Composable
private fun StaticTranscript(transcript: List<TranscriptLine>) {
    var visible by remember { mutableStateOf(false) }
    TextButton(onClick = { visible = !visible }) {
        Text(if (visible) "Hide transcript" else "Show transcript")
    }
    if (visible) transcript.forEach { line -> TranscriptRow(line = line, onSeek = null) }
}

@Composable
private fun TranscriptRow(
    line: TranscriptLine,
    onSeek: (() -> Unit)?,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .then(if (onSeek != null) Modifier.clickable(onClick = onSeek) else Modifier)
            .padding(vertical = 8.dp),
    ) {
        if (line.speaker.isNotBlank()) {
            Text(line.speaker, style = MaterialTheme.typography.labelMedium)
        }
        Text(line.czech, fontWeight = FontWeight.Bold)
        if (line.english.isNotBlank()) Text(line.english)
        if (line.note.isNotBlank()) Text(line.note, style = MaterialTheme.typography.bodySmall)
        if (onSeek != null) Text("Tap to replay this segment", style = MaterialTheme.typography.labelSmall)
        HorizontalDivider(Modifier.padding(top = 8.dp))
    }
}

@Composable
private fun ExternalResourceCard(resource: LearningResource) {
    val uriHandler = LocalUriHandler.current
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(resource.title, fontWeight = FontWeight.Bold)
            Text(resource.kind, style = MaterialTheme.typography.labelMedium)
            if (resource.note.isNotBlank()) Text(resource.note, style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = { uriHandler.openUri(resource.url) }) { Text("Open") }
        }
    }
}
