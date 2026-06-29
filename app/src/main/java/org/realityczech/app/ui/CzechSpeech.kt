package org.realityczech.app.ui

import android.content.Context
import android.media.MediaPlayer
import android.speech.tts.TextToSpeech
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import org.realityczech.app.model.MediaCatalog
import java.util.Locale

internal enum class CzechSpeechStatus {
    INITIALIZING,
    READY,
    UNAVAILABLE,
}

internal class CzechSpeaker(context: Context) : TextToSpeech.OnInitListener {
    private val locale = Locale.forLanguageTag("cs-CZ")
    private val engine = TextToSpeech(context.applicationContext, this)

    var status by mutableStateOf(CzechSpeechStatus.INITIALIZING)
        private set

    override fun onInit(result: Int) {
        if (result != TextToSpeech.SUCCESS) {
            status = CzechSpeechStatus.UNAVAILABLE
            return
        }
        val availability = engine.isLanguageAvailable(locale)
        status = if (
            availability == TextToSpeech.LANG_MISSING_DATA ||
            availability == TextToSpeech.LANG_NOT_SUPPORTED
        ) {
            CzechSpeechStatus.UNAVAILABLE
        } else {
            engine.language = locale
            CzechSpeechStatus.READY
        }
    }

    fun speak(text: String, slow: Boolean = false) {
        if (status != CzechSpeechStatus.READY || text.isBlank()) return
        engine.language = locale
        engine.setSpeechRate(if (slow) 0.65f else 0.9f)
        engine.speak(
            text,
            TextToSpeech.QUEUE_FLUSH,
            null,
            "reality-czech-${text.hashCode()}-${if (slow) "slow" else "normal"}",
        )
    }

    fun shutdown() {
        engine.stop()
        engine.shutdown()
    }
}

internal data class HumanRecording(
    val assetPath: String,
    val speaker: String,
)

internal class HumanRecordingPlayer(context: Context) {
    private val appContext = context.applicationContext
    private var player: MediaPlayer? = null
    private val recordings: Map<String, HumanRecording> = runCatching {
        val raw = appContext.assets.open("media/catalog.json").bufferedReader().use { it.readText() }
        val catalog = Json { ignoreUnknownKeys = true }.decodeFromString<MediaCatalog>(raw)
        buildMap {
            catalog.assets
                .asSequence()
                .filter { it.isBundledAudio }
                .forEach { asset ->
                    val recording = HumanRecording(
                        assetPath = "media/${asset.localPath}",
                        speaker = asset.speaker,
                    )
                    sequenceOf(asset.label, asset.fallbackText)
                        .map(::normalizeSpeechKey)
                        .filter { it.isNotBlank() }
                        .forEach { key -> putIfAbsent(key, recording) }
                }
        }
    }.getOrDefault(emptyMap())

    fun find(text: String): HumanRecording? = recordings[normalizeSpeechKey(text)]

    fun play(recording: HumanRecording) {
        player?.release()
        player = null
        runCatching {
            val newPlayer = MediaPlayer()
            appContext.assets.openFd(recording.assetPath).use { descriptor ->
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
        }
    }

    fun shutdown() {
        player?.release()
        player = null
    }
}

internal val LocalCzechSpeaker = compositionLocalOf<CzechSpeaker> {
    error("CzechSpeechProvider is missing")
}

internal val LocalHumanRecordings = compositionLocalOf<HumanRecordingPlayer> {
    error("CzechSpeechProvider is missing")
}

@Composable
internal fun CzechSpeechProvider(content: @Composable () -> Unit) {
    val context = LocalContext.current
    val speaker = remember(context.applicationContext) { CzechSpeaker(context.applicationContext) }
    val recordings = remember(context.applicationContext) {
        HumanRecordingPlayer(context.applicationContext)
    }

    DisposableEffect(speaker, recordings) {
        onDispose {
            speaker.shutdown()
            recordings.shutdown()
        }
    }

    CompositionLocalProvider(
        LocalCzechSpeaker provides speaker,
        LocalHumanRecordings provides recordings,
        content = content,
    )
}

@Composable
internal fun CzechSpeakControls(
    text: String,
    modifier: Modifier = Modifier,
    showSlow: Boolean = true,
) {
    val recordings = LocalHumanRecordings.current
    val recording = recordings.find(text)
    var fallbackVisible by remember(text) { mutableStateOf(false) }

    if (recording == null) {
        TtsButtons(text = text, modifier = modifier, showSlow = showSlow)
        return
    }

    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        OutlinedButton(onClick = { recordings.play(recording) }) {
            Text(if (recording.speaker.isBlank()) "Play real speaker" else "Play ${recording.speaker}")
        }
        TextButton(onClick = { fallbackVisible = !fallbackVisible }) {
            Text(if (fallbackVisible) "Hide synthesized fallback" else "Use synthesized fallback")
        }
        if (fallbackVisible) {
            TtsButtons(text = text, showSlow = showSlow)
        }
    }
}

@Composable
private fun TtsButtons(
    text: String,
    modifier: Modifier = Modifier,
    showSlow: Boolean,
) {
    val speaker = LocalCzechSpeaker.current
    val enabled = speaker.status == CzechSpeechStatus.READY
    Row(modifier = modifier, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedButton(
            onClick = { speaker.speak(text) },
            enabled = enabled,
        ) {
            Text(if (enabled) "Play TTS" else "Czech TTS unavailable")
        }
        if (showSlow) {
            OutlinedButton(
                onClick = { speaker.speak(text, slow = true) },
                enabled = enabled,
            ) {
                Text("Slow TTS")
            }
        }
    }
}

private fun normalizeSpeechKey(value: String): String = value
    .trim()
    .lowercase()
    .trimEnd('.', '!', '?')
    .replace(Regex("\\s+"), " ")
