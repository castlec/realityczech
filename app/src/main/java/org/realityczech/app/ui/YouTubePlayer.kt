package org.realityczech.app.ui

import android.annotation.SuppressLint
import android.graphics.Color
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView

private val YOUTUBE_ID = Regex("^[A-Za-z0-9_-]{11}$")

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun YouTubePlayer(
    videoId: String,
    modifier: Modifier = Modifier,
    seekToSeconds: Int? = null,
) {
    require(YOUTUBE_ID.matches(videoId)) { "Invalid YouTube video ID" }

    val webViewState = remember { mutableStateOf<WebView?>(null) }

    AndroidView(
        modifier = modifier.fillMaxWidth().aspectRatio(16f / 9f),
        factory = { context ->
            WebView(context).apply {
                setBackgroundColor(Color.BLACK)
                webViewClient = WebViewClient()
                webChromeClient = WebChromeClient()
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                settings.mediaPlaybackRequiresUserGesture = true
                settings.cacheMode = WebSettings.LOAD_DEFAULT
                settings.allowFileAccess = false
                settings.allowContentAccess = false
                loadYouTubeVideo(videoId)
                webViewState.value = this
            }
        },
        update = { webView ->
            val loadedVideoId = webView.tag as? String
            if (loadedVideoId != videoId) {
                webView.loadYouTubeVideo(videoId)
            }
            seekToSeconds?.let { seconds ->
                webView.evaluateJavascript("seekTo($seconds);", null)
            }
        },
    )

    DisposableEffect(Unit) {
        onDispose {
            webViewState.value?.apply {
                stopLoading()
                loadUrl("about:blank")
                destroy()
            }
            webViewState.value = null
        }
    }
}

private fun WebView.loadYouTubeVideo(videoId: String) {
    tag = videoId
    loadDataWithBaseURL(
        "https://realityczech.org/",
        youtubeHtml(videoId),
        "text/html",
        "UTF-8",
        null,
    )
}

private fun youtubeHtml(videoId: String): String = """
    <!doctype html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
        <style>
          html, body, #player { margin: 0; width: 100%; height: 100%; background: #000; overflow: hidden; }
        </style>
      </head>
      <body>
        <div id="player"></div>
        <script src="https://www.youtube.com/iframe_api"></script>
        <script>
          var player;
          function onYouTubeIframeAPIReady() {
            player = new YT.Player('player', {
              width: '100%',
              height: '100%',
              videoId: '$videoId',
              playerVars: {
                playsinline: 1,
                rel: 0,
                modestbranding: 1,
                origin: 'https://realityczech.org'
              }
            });
          }
          function seekTo(seconds) {
            if (player && player.seekTo) {
              player.seekTo(seconds, true);
              player.playVideo();
            }
          }
        </script>
      </body>
    </html>
""".trimIndent()
