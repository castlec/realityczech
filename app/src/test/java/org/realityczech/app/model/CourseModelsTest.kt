package org.realityczech.app.model

import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.fail
import org.junit.Test

class CourseModelsTest {
    @Test
    fun quizQuestionRejectsInvalidCorrectIndex() {
        try {
            QuizQuestion(
                prompt = "Test",
                choices = listOf("A"),
                correctIndex = 2,
                explanation = "",
            )
            fail("Expected an IllegalArgumentException")
        } catch (_: IllegalArgumentException) {
            // Expected.
        }
    }

    @Test
    fun courseDecodesFromJson() {
        val course = Json.decodeFromString<Course>(
            """
            {
              "title":"Test",
              "description":"Description",
              "sourceUrl":"https://example.com",
              "license":"CC BY-SA",
              "units":[]
            }
            """.trimIndent(),
        )
        assertEquals("Test", course.title)
        assertEquals(0, course.lessons.size)
    }
}
