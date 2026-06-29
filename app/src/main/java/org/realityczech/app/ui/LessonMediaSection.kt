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
import androidx.compose.material3.Surface
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
private const val LESSON_SECTION_PROVIDER = "lesson-section"

@Composable
fun LessonMediaSection(
    resources: List<LearningResource>,
    transcript: List<TranscriptLine>,
) {
    val context = LocalContext.current
    var player by remember { mutableStateOf<MediaPlayer?>(null) }
    var playbackError by remember { mutableStateOf<String?>(null) }

    DisposableEffect(Unit) {
        onDispose {
            player?.release()
            player = null
        }
    }

    val playRecording: (LearningResource) -> Unit = { resource ->
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

    val videos = resources.filter { it.isEmbeddedVideo }
    val recordedAudio = resources.filter { it.isEmbeddedAudio }
    val pronunciationImages = resources.filter { it.kind == PRONUNCIATION_IMAGE_KIND }
    val sectionResources = resources.filter { it.provider == LESSON_SECTION_PROVIDER }
    val documentImages = resources.filter { it.isDocumentImage }
    val otherResources = resources.filterNot {
        it.isEmbeddedVideo || it.isEmbeddedAudio || it.isDocumentImage ||
            it.kind == PRONUNCIATION_IMAGE_KIND || it.provider == LESSON_SECTION_PROVIDER
    }
    val imageKeys = pronunciationImages.map { normalizeMediaKey(it.title) }.toSet()
    val recordingsByKey = recordedAudio.groupBy { normalizeMediaKey(it.title) }
    val unpairedRecordings = recordedAudio.filter { normalizeMediaKey(it.title) !in imageKeys }

    if (videos.isNotEmpty()) EmbeddedVideoSection(videos, transcript)
    if (pronunciationImages.isNotEmpty()) {
        PronunciationGallery(pronunciationImages, recordingsByKey, playRecording)
    }
    if (unpairedRecordings.isNotEmpty()) {
        RecordedAudioSection(unpairedRecordings, playRecording)
    }
    if (sectionResources.isNotEmpty()) {
        SemanticLessonContent(sectionResources, documentImages)
    } else if (documentImages.isNotEmpty()) {
        DocumentImageStrip("Source lesson illustrations", documentImages)
    }

    playbackError?.let {
        Text("Recorded playback failed: $it", color = MaterialTheme.colorScheme.error)
    }

    if (otherResources.isNotEmpty()) {
        Text("Other sources", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        otherResources.forEach { ExternalResourceCard(it) }
    }
    if (videos.isEmpty() && transcript.isNotEmpty()) StaticTranscript(transcript)
}

@Composable
private fun RecordedAudioSection(
    resources: List<LearningResource>,
    playRecording: (LearningResource) -> Unit,
) {
    val uriHandler = LocalUriHandler.current
    Text("More real-speaker recordings", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    Text(
        "These source recordings do not have a matching picture card. Device speech is available only as a fallback.",
        style = MaterialTheme.typography.bodySmall,
    )
    LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        items(resources, key = { it.assetPath }) { resource ->
            Card(Modifier.width(260.dp)) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(resource.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    if (resource.note.isNotBlank()) Text(resource.note, style = MaterialTheme.typography.bodySmall)
                    Button(onClick = { playRecording(resource) }) { Text("Play real speaker") }
                    SynthesizedFallback(resource.fallbackText.ifBlank { resource.title })
                    TextButton(onClick = { uriHandler.openUri(resource.url) }) {
                        Text("Open original source")
                    }
                }
            }
        }
    }
}

@Composable
private fun PronunciationGallery(
    resources: List<LearningResource>,
    recordingsByKey: Map<String, List<LearningResource>>,
    playRecording: (LearningResource) -> Unit,
) {
    val speaker = LocalCzechSpeaker.current
    Text("See, listen, and repeat", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    Text(
        "A matching human recording is used whenever one exists. Device Czech speech appears only as a fallback.",
        style = MaterialTheme.typography.bodySmall,
    )
    if (speaker.status == CzechSpeechStatus.UNAVAILABLE) {
        Text(
            "No Czech speech voice is installed. Human recordings remain available.",
            color = MaterialTheme.colorScheme.error,
        )
    }
    LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        items(resources, key = { "${it.title}-${it.url}" }) { resource ->
            PronunciationCard(
                resource = resource,
                recording = recordingsByKey[normalizeMediaKey(resource.title)]?.firstOrNull(),
                playRecording = playRecording,
            )
        }
    }
    ListenAndTypePractice(resources, recordingsByKey, playRecording)
}

@Composable
private fun PronunciationCard(
    resource: LearningResource,
    recording: LearningResource?,
    playRecording: (LearningResource) -> Unit,
) {
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
                if (recording != null) {
                    Button(onClick = { playRecording(recording) }) {
                        Text(if (recording.note.contains(" by ")) "Play real speaker" else "Play recording")
                    }
                    SynthesizedFallback(resource.title)
                } else {
                    Text("No human recording found", style = MaterialTheme.typography.labelMedium)
                    CzechSpeakControls(text = resource.title)
                }
            }
        }
    }
}

@Composable
private fun SynthesizedFallback(text: String) {
    var visible by remember(text) { mutableStateOf(false) }
    TextButton(onClick = { visible = !visible }) {
        Text(if (visible) "Hide synthesized fallback" else "Use synthesized fallback")
    }
    if (visible) CzechSpeakControls(text = text)
}

@Composable
private fun ListenAndTypePractice(
    resources: List<LearningResource>,
    recordingsByKey: Map<String, List<LearningResource>>,
    playRecording: (LearningResource) -> Unit,
) {
    var selectedIndex by remember(resources) { mutableIntStateOf(0) }
    var answer by remember(selectedIndex) { mutableStateOf("") }
    var submitted by remember(selectedIndex) { mutableStateOf(false) }
    val item = resources[selectedIndex.coerceIn(resources.indices)]
    val recording = recordingsByKey[normalizeMediaKey(item.title)]?.firstOrNull()
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
            if (recording != null) {
                Button(onClick = { playRecording(recording) }) { Text("Play real speaker") }
                SynthesizedFallback(item.title)
            } else {
                CzechSpeakControls(text = item.title)
            }
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
private fun SemanticLessonContent(
    sections: List<LearningResource>,
    images: List<LearningResource>,
) {
    val instructional = images.filter { it.semanticRole != "exercise-related" }
    val practice = images.filter { it.semanticRole == "exercise-related" }
    val orderedSections = sections.sortedBy { it.sourceOrder ?: Int.MAX_VALUE }
    val assigned = mutableSetOf<String>()

    orderedSections.forEach { section ->
        Surface(tonalElevation = 2.dp, shape = MaterialTheme.shapes.medium) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(section.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(section.note)
                section.fallbackText.lines().filter { it.isNotBlank() }.forEach { example ->
                    Text(example, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.primary)
                }
            }
        }
        val related = instructional.filter { image ->
            headingMatches(image.placementHeading, section.title)
        }
        if (related.isNotEmpty()) {
            assigned += related.map { it.assetPath }
            DocumentImageStrip("Source illustrations for ${section.title}", related)
        }
    }

    val remaining = instructional.filterNot { it.assetPath in assigned }
    if (remaining.isNotEmpty()) {
        DocumentImageStrip("Additional instructional illustrations", remaining)
    }
    if (practice.isNotEmpty()) {
        DocumentImageStrip("Practice illustrations from the source", practice)
    }
}

@Composable
private fun DocumentImageStrip(title: String, resources: List<LearningResource>) {
    Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
    LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        items(resources, key = { "${it.assetPath}-${it.placementHeading}-${it.title}" }) {
            DocumentImageCard(it)
        }
    }
}

@Composable
private fun DocumentImageCard(resource: LearningResource) {
    val uriHandler = LocalUriHandler.current
    var creditVisible by remember(resource.assetPath, resource.title) { mutableStateOf(false) }
    Card(Modifier.width(280.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            AsyncImage(
                model = "file:///android_asset/${resource.assetPath}",
                contentDescription = resource.title,
                modifier = Modifier.fillMaxWidth().height(190.dp),
                contentScale = ContentScale.Fit,
            )
            Column(
                modifier = Modifier.padding(start = 12.dp, end = 12.dp, bottom = 12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(resource.title, fontWeight = FontWeight.Bold)
                if (resource.caption.isNotBlank() && resource.caption != resource.title) {
                    Text(resource.caption)
                }
                if (resource.note.isNotBlank()) Text(resource.note, style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = { creditVisible = !creditVisible }) {
                    Text(if (creditVisible) "Hide credit" else "Show credit")
                }
                if (creditVisible) Text(resource.attribution, style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = { uriHandler.openUri(resource.url) }) { Text("Open source lesson") }
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

private fun headingMatches(source: String, adapted: String): Boolean {
    val left = headingTokens(source)
    val right = headingTokens(adapted)
    if (left.isEmpty() || right.isEmpty()) return false
    return left.intersect(right).isNotEmpty() || normalizeMediaKey(source).contains(normalizeMediaKey(adapted)) ||
        normalizeMediaKey(adapted).contains(normalizeMediaKey(source))
}

private fun headingTokens(value: String): Set<String> = value
    .lowercase()
    .split(Regex("[^\\p{L}\\p{N}]+"))
    .filter { it.length >= 4 && it !in setOf("with", "from", "using", "czech", "lesson") }
    .toSet()

private fun normalizeMediaKey(value: String): String = value
    .trim()
    .lowercase()
    .trimEnd('.', '!', '?')
    .replace(Regex("\\s+"), " ")

private fun normalizeMediaAnswer(value: String): String = normalizeMediaKey(value)
