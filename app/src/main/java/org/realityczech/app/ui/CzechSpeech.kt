package org.realityczech.app.ui

import android.content.Context
import android.speech.tts.TextToSpeech
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
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

    fun stop() {
        engine.stop()
    }

    fun shutdown() {
        engine.stop()
        engine.shutdown()
    }
}

internal val LocalCzechSpeaker = compositionLocalOf<CzechSpeaker> {
    error("CzechSpeechProvider is missing")
}

@Composable
internal fun CzechSpeechProvider(content: @Composable () -> Unit) {
    val context = LocalContext.current
    val speaker = remember(context.applicationContext) { CzechSpeaker(context.applicationContext) }

    DisposableEffect(speaker) {
        onDispose { speaker.shutdown() }
    }

    CompositionLocalProvider(LocalCzechSpeaker provides speaker, content = content)
}

@Composable
internal fun CzechSpeakControls(
    text: String,
    modifier: Modifier = Modifier,
    showSlow: Boolean = true,
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
