package org.realityczech.app.ui

import android.media.MediaPlayer
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import org.realityczech.app.model.LearningResource
import org.realityczech.app.model.TranscriptLine

private const val PRONUNCIATION_IMAGE_KIND = "pronunciation image"
private const val REALITY_CZECH_GDOC_PATH = "realityczech.org/wp-content/uploads/gdoc/"

@Composable
fun LessonMediaSection(
    resources: List<LearningResource>,
    transcript: List<TranscriptLine>,
) {
    val videos = resources.filter { it.isEmbeddedVideo }
    val recordedAudio = resources.filter { it.isEmbeddedAudio }
    val pronunciationImages = resources.filter { it.kind == PRONUNCIATION_IMAGE_KIND }
    val documentImages = resources.filter { it.isDocumentImage }
    val otherResources = resources.filterNot {
        it.isEmbeddedVideo || it.isEmbeddedAudio || it.isDocumentImage ||
            it.kind == PRONUNCIATION_IMAGE_KIND
    }

    if (videos.isNotEmpty()) EmbeddedVideoSection(videos, transcript)
    if (recordedAudio.isNotEmpty()) RecordedAudioSection(recordedAudio)
    if (pronunciationImages.isNotEmpty()) PronunciationGallery(pronunciationImages)
    if (documentImages.isNotEmpty()) DocumentImageGallery(documentImages)

    if (otherResources.isNotEmpty()) {
        Text("Other sources", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        otherResources.forEach { ExternalResourceCard(it) }
    }

    if (videos.isEmpty() && transcript.isNotEmpty()) StaticTranscript(transcript)
}

@Composable
private fun RecordedAudioSection(resources: List<LearningResource>) {
    val context = LocalContext.current
    val uriHandler = LocalUriHandler.current
    var player by remember { mutableStateOf<MediaPlayer?>(null) }
    var playbackError by remember { mutableStateOf<String?>(null) }

    DisposableEffect(Unit) {
        onDispose {
            player?.release()
            player = null
        }
    }

    fun play(resource: LearningResource) {
        player?.release()
        player = null
        playbackError = null
        try {
            val newPlayer = MediaPlayer()
            context.assets.openFd(resource.assetPath).use { descriptor ->
                newPlayer.setDataSource(
                    descriptor.fileDescriptor,
                    descriptor.startOffset,
                    descriptor.length,
                )
            }
            newPlayer.setOnCompletionListener { completed ->
                completed.release()
                if (player === completed) player = null
            }
            newPlayer.prepare()
            newPlayer.start()
            player = newPlayer
        } catch (error: Exception) {
            playbackError = error.message ?: "Unable to play the bundled recording."
        }
    }

    Text("Real-speaker recordings", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    Text(
        "These recordings are bundled from the declared sources. Device speech remains available as a fallback.",
        style = MaterialTheme.typography.bodySmall,
    )

    LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        items(resources, key = { it.assetPath }) { resource ->
            Card(Modifier.width(260.dp)) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(resource.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    if (resource.note.isNotBlank()) Text(resource.note, style = MaterialTheme.typography.bodySmall)
                    Button(onClick = { play(resource) }) { Text("Play real speaker") }
                    val fallback = resource.fallbackText.ifBlank { resource.title }
                    Text("Synthesized fallback", style = MaterialTheme.typography.labelMedium)
                    CzechSpeakControls(text = fallback)
                    TextButton(onClick = { uriHandler.openUri(resource.url) }) {
                        Text("Open original source")
                    }
                }
            }
        }
    }

    playbackError?.let {
        Text("Recorded playback failed: $it", color = MaterialTheme.colorScheme.error)
    }
}

@Composable
private fun PronunciationGallery(resources: List<LearningResource>) {
    val speaker = LocalCzechSpeaker.current
    Text("See, listen, and repeat", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    Text(
        "The pictures are bundled from declared source URLs. Device Czech speech is used when no matching human recording is available.",
        style = MaterialTheme.typography.bodySmall,
    )
    if (speaker.status == CzechSpeechStatus.UNAVAILABLE) {
        Text(
            "No Czech speech voice is installed. The pictures remain available, but synthesized playback is disabled.",
            color = MaterialTheme.colorScheme.error,
        )
    }
    LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        items(resources, key = { "${it.title}-${it.url}" }) { PronunciationCard(it) }
    }
    ListenAndTypePractice(resources)
}

@Composable
private fun PronunciationCard(resource: LearningResource) {
    Card(Modifier.width(220.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            AsyncImage(
                model = bundledImageModel(resource),
                contentDescription = resource.note.ifBlank { resource.title },
                modifier = Modifier.fillMaxWidth().height(140.dp),
                contentScale = ContentScale.Crop,
            )
            Column(
                modifier = Modifier.padding(start = 12.dp, end = 12.dp, bottom = 12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(resource.title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                if (resource.note.isNotBlank()) Text(resource.note)
                CzechSpeakControls(text = resource.title)
            }
        }
    }
}

@Composable
private fun DocumentImageGallery(resources: List<LearningResource>) {
    var visible by remember(resources) { mutableStateOf(false) }
    Text("Source document images", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    Text(
        "${resources.size} additional image${if (resources.size == 1) "" else "s"} recovered from the original lesson document. Credits and source links are preserved.",
        style = MaterialTheme.typography.bodySmall,
    )
    TextButton(onClick = { visible = !visible }) {
        Text(if (visible) "Hide source images" else "Show source images (${resources.size})")
    }
    if (!visible) return

    LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        items(resources, key = { it.assetPath }) { resource -> DocumentImageCard(resource) }
    }
}

@Composable
private fun DocumentImageCard(resource: LearningResource) {
    val uriHandler = LocalUriHandler.current
    var creditVisible by remember(resource.assetPath) { mutableStateOf(false) }
    Card(Modifier.width(260.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            AsyncImage(
                model = "file:///android_asset/${resource.assetPath}",
                contentDescription = resource.title,
                modifier = Modifier.fillMaxWidth().height(180.dp),
                contentScale = ContentScale.Fit,
            )
            Column(
                modifier = Modifier.padding(start = 12.dp, end = 12.dp, bottom = 12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(resource.title, fontWeight = FontWeight.Bold)
                if (resource.note.isNotBlank()) Text(resource.note, style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = { creditVisible = !creditVisible }) {
                    Text(if (creditVisible) "Hide credit" else "Show credit")
                }
                if (creditVisible) {
                    Text(resource.attribution, style = MaterialTheme.typography.bodySmall)
                }
                TextButton(onClick = { uriHandler.openUri(resource.url) }) {
                    Text("Open source lesson")
                }
            }
        }
    }
}

@Composable
private fun ListenAndTypePractice(resources: List<LearningResource>) {
    var selectedIndex by remember(resources) { mutableIntStateOf(0) }
    var answer by remember(selectedIndex) { mutableStateOf("") }
    var submitted by remember(selectedIndex) { mutableStateOf(false) }
    val item = resources[selectedIndex.coerceIn(resources.indices)]
    val correct = normalizeMediaAnswer(answer) == normalizeMediaAnswer(item.title)

    Text("Picture dictation", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            AsyncImage(
                model = bundledImageModel(item),
                contentDescription = item.note.ifBlank { "Vocabulary image" },
                modifier = Modifier.fillMaxWidth().height(180.dp),
                contentScale = ContentScale.Fit,
            )
            Text("Listen to the Czech word, then type it with the correct diacritics.")
            CzechSpeakControls(text = item.title)
            OutlinedTextField(
                value = answer,
                onValueChange = {
                    answer = it
                    submitted = false
                },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Czech word") },
                singleLine = true,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { submitted = true }, enabled = answer.isNotBlank()) { Text("Check") }
                OutlinedButton(
                    onClick = {
                        selectedIndex = (selectedIndex + 1) % resources.size
                        answer = ""
                        submitted = false
                    },
                ) { Text("Another picture") }
            }
            if (submitted) {
                Text(
                    if (correct) "Correct. ${item.title} means ${item.note}." else "Not yet. The answer is ${item.title}.",
                    color = if (correct) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}

@Composable
private fun EmbeddedVideoSection(videos: List<LearningResource>, transcript: List<TranscriptLine>) {
    var selectedIndex by remember(videos) { mutableIntStateOf(0) }
    var transcriptVisible by remember { mutableStateOf(false) }
    var seekSeconds by remember { mutableStateOf<Int?>(null) }
    val selectedVideo = videos[selectedIndex.coerceIn(videos.indices)]
    val selectedTranscript = transcript.filter { it.mediaId.isBlank() || it.mediaId == selectedVideo.mediaId }

    Text("Watch and listen", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    if (videos.size > 1) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            videos.forEachIndexed { index, video ->
                val onSelect = {
                    selectedIndex = index
                    transcriptVisible = false
                    seekSeconds = null
                }
                if (index == selectedIndex) {
                    Button(onClick = onSelect, modifier = Modifier.fillMaxWidth()) { Text(video.title) }
                } else {
                    OutlinedButton(onClick = onSelect, modifier = Modifier.fillMaxWidth()) { Text(video.title) }
                }
            }
        }
    } else {
        Text(selectedVideo.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
    }

    YouTubePlayer(videoId = selectedVideo.mediaId, seekToSeconds = seekSeconds)
    if (selectedVideo.note.isNotBlank()) Text(selectedVideo.note, style = MaterialTheme.typography.bodySmall)

    val uriHandler = LocalUriHandler.current
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        if (selectedTranscript.isNotEmpty()) {
            TextButton(onClick = { transcriptVisible = !transcriptVisible }) {
                Text(if (transcriptVisible) "Hide transcript" else "Show transcript")
            }
        }
        TextButton(onClick = { uriHandler.openUri(selectedVideo.url) }) { Text("Open source page") }
    }

    if (transcriptVisible) {
        Text("Listen once before relying on the transcript.", style = MaterialTheme.typography.bodySmall)
        selectedTranscript.forEach { line ->
            TranscriptRow(line, line.startSeconds?.let { seconds -> { seekSeconds = seconds } })
        }
    }
}

@Composable
private fun StaticTranscript(transcript: List<TranscriptLine>) {
    var visible by remember { mutableStateOf(false) }
    TextButton(onClick = { visible = !visible }) {
        Text(if (visible) "Hide transcript" else "Show transcript")
    }
    if (visible) transcript.forEach { TranscriptRow(it, null) }
}

@Composable
private fun TranscriptRow(line: TranscriptLine, onSeek: (() -> Unit)?) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .then(if (onSeek != null) Modifier.clickable(onClick = onSeek) else Modifier)
            .padding(vertical = 8.dp),
    ) {
        if (line.speaker.isNotBlank()) Text(line.speaker, style = MaterialTheme.typography.labelMedium)
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

private fun bundledImageModel(resource: LearningResource): String {
    if (resource.kind != PRONUNCIATION_IMAGE_KIND || !resource.url.contains(REALITY_CZECH_GDOC_PATH)) {
        return resource.url
    }
    val fileName = resource.url.substringAfterLast('/').substringBefore('?')
    return "file:///android_asset/media/images/$fileName"
}

private fun normalizeMediaAnswer(value: String): String = value
    .trim()
    .lowercase()
    .trimEnd('.', '!', '?')
    .replace(Regex("\\s+"), " ")
