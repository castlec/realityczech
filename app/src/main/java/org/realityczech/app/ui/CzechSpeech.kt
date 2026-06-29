package org.realityczech.app.ui

import android.content.Context
import android.speech.tts.TextToSpeech
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import java.util.Locale
import java.util.UUID

class CzechSpeaker internal constructor(context: Context) {
    var isReady by mutableStateOf(false)
        private set

    var isUnavailable by mutableStateOf(false)
        private set

    private var textToSpeech: TextToSpeech? = null

    init {
        textToSpeech = TextToSpeech(context.applicationContext) { status ->
            if (status != TextToSpeech.SUCCESS) {
                isUnavailable = true
                return@TextToSpeech
            }

            val result = textToSpeech
                ?.setLanguage(Locale.forLanguageTag("cs-CZ"))
                ?: TextToSpeech.LANG_NOT_SUPPORTED
            isReady = result != TextToSpeech.LANG_MISSING_DATA &&
                result != TextToSpeech.LANG_NOT_SUPPORTED
            isUnavailable = !isReady
        }
    }

    fun speak(text: String, slow: Boolean = false) {
        val engine = textToSpeech ?: return
        if (!isReady) return
        engine.setSpeechRate(if (slow) 0.65f else 0.9f)
        engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, UUID.randomUUID().toString())
    }

    fun stop() {
        textToSpeech?.stop()
    }

    fun shutdown() {
        textToSpeech?.stop()
        textToSpeech?.shutdown()
        textToSpeech = null
        isReady = false
    }
}

@Composable
fun rememberCzechSpeaker(): CzechSpeaker {
    val context = LocalContext.current
    val speaker = remember(context) { CzechSpeaker(context) }

    DisposableEffect(speaker) {
        onDispose { speaker.shutdown() }
    }

    return speaker
}
