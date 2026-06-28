package org.realityczech.app.data

import android.content.Context

class ProgressStore(context: Context) {
    private val preferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    fun isComplete(lessonId: String): Boolean = preferences.getBoolean(key(lessonId), false)

    fun setComplete(lessonId: String, complete: Boolean) {
        preferences.edit().putBoolean(key(lessonId), complete).apply()
    }

    private fun key(lessonId: String): String = "lesson_complete_$lessonId"

    companion object {
        private const val PREFERENCES_NAME = "reality_czech_progress"
    }
}
