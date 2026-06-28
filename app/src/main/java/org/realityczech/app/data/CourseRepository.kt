package org.realityczech.app.data

import android.content.Context
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import org.realityczech.app.model.Course
import org.realityczech.app.model.CourseIndex
import org.realityczech.app.model.CourseUnit
import org.realityczech.app.model.Lesson

class CourseRepository(private val context: Context) {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = false
    }

    fun load(): Course {
        val index = readJson<CourseIndex>(COURSE_INDEX_ASSET)
        val units = index.units.map { unit ->
            CourseUnit(
                id = unit.id,
                title = unit.title,
                description = unit.description,
                lessons = unit.lessonFiles.map { filename ->
                    readJson<Lesson>("$LESSON_DIRECTORY/$filename")
                },
            )
        }

        return Course(
            title = index.title,
            description = index.description,
            sourceUrl = index.sourceUrl,
            license = index.license,
            units = units,
        )
    }

    private inline fun <reified T> readJson(path: String): T {
        val raw = context.assets.open(path).bufferedReader().use { it.readText() }
        return json.decodeFromString(raw)
    }

    companion object {
        private const val COURSE_INDEX_ASSET = "course/index.json"
        private const val LESSON_DIRECTORY = "course/lessons"
    }
}
