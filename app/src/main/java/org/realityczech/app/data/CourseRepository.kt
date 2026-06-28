package org.realityczech.app.data

import android.content.Context
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import org.realityczech.app.model.Course

class CourseRepository(private val context: Context) {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = false
    }

    fun load(): Course {
        val raw = context.assets.open(COURSE_ASSET).bufferedReader().use { it.readText() }
        return json.decodeFromString<Course>(raw)
    }

    companion object {
        private const val COURSE_ASSET = "course.json"
    }
}
