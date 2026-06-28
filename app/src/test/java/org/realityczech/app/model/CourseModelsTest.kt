package org.realityczech.app.model

import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class CourseModelsTest {
    @Test
    fun multipleChoiceRejectsInvalidCorrectIndex() {
        try {
            Exercise(
                type = Exercise.MULTIPLE_CHOICE,
                prompt = "Test",
                choices = listOf("A"),
                correctIndex = 2,
                explanation = "Explanation",
            )
            fail("Expected an IllegalArgumentException")
        } catch (_: IllegalArgumentException) {
            // Expected.
        }
    }

    @Test
    fun textEntryRequiresAcceptedAnswers() {
        try {
            Exercise(
                type = Exercise.TEXT_ENTRY,
                prompt = "Test",
                explanation = "Explanation",
            )
            fail("Expected an IllegalArgumentException")
        } catch (_: IllegalArgumentException) {
            // Expected.
        }
    }

    @Test
    fun courseIndexDecodesFromJson() {
        val index = Json.decodeFromString<CourseIndex>(
            """
            {
              "title":"Test",
              "description":"Description",
              "sourceUrl":"https://example.com",
              "license":"CC BY-SA",
              "units":[{
                "id":"unit-1",
                "title":"Unit 1",
                "description":"Description",
                "lessonFiles":["lesson.json"]
              }]
            }
            """.trimIndent(),
        )
        assertEquals("Test", index.title)
        assertEquals(listOf("lesson.json"), index.units.single().lessonFiles)
    }

    @Test
    fun youtubeResourceIsRecognizedAsEmbeddedVideo() {
        val video = LearningResource(
            title = "Interview",
            kind = "video",
            url = "https://example.com/video",
            provider = "youtube",
            mediaId = "Xopqb_Az90Q",
        )
        val lessonPage = LearningResource(
            title = "Lesson",
            kind = "web",
            url = "https://example.com/lesson",
        )

        assertTrue(video.isEmbeddedVideo)
        assertFalse(lessonPage.isEmbeddedVideo)
    }
}
