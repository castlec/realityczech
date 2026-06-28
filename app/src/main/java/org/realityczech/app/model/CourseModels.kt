package org.realityczech.app.model

import kotlinx.serialization.Serializable

@Serializable
data class CourseIndex(
    val title: String,
    val description: String,
    val sourceUrl: String,
    val license: String,
    val units: List<CourseUnitIndex>,
)

@Serializable
data class CourseUnitIndex(
    val id: String,
    val title: String,
    val description: String,
    val lessonFiles: List<String>,
)

@Serializable
data class Course(
    val title: String,
    val description: String,
    val sourceUrl: String,
    val license: String,
    val units: List<CourseUnit>,
) {
    val lessons: List<Lesson>
        get() = units.flatMap { it.lessons }
}

@Serializable
data class CourseUnit(
    val id: String,
    val title: String,
    val description: String,
    val lessons: List<Lesson>,
)

@Serializable
data class Lesson(
    val id: String,
    val day: String,
    val title: String,
    val summary: String,
    val estimatedMinutes: Int,
    val objectives: List<String>,
    val sections: List<LessonSection>,
    val vocabulary: List<VocabularyItem> = emptyList(),
    val transcript: List<TranscriptLine> = emptyList(),
    val resources: List<LearningResource> = emptyList(),
    val exercises: List<Exercise> = emptyList(),
    val sourceUrl: String,
    val sourceAttribution: String = "Reality Czech",
    val contentLicense: String = "CC BY-SA",
)

@Serializable
data class LessonSection(
    val heading: String,
    val body: String,
    val examples: List<String> = emptyList(),
)

@Serializable
data class VocabularyItem(
    val czech: String,
    val english: String,
    val note: String = "",
)

@Serializable
data class TranscriptLine(
    val speaker: String = "",
    val czech: String,
    val english: String = "",
    val note: String = "",
)

@Serializable
data class LearningResource(
    val title: String,
    val kind: String,
    val url: String,
    val note: String = "",
)

@Serializable
data class Exercise(
    val type: String,
    val prompt: String,
    val choices: List<String> = emptyList(),
    val correctIndex: Int = -1,
    val acceptedAnswers: List<String> = emptyList(),
    val explanation: String,
) {
    init {
        require(type in SUPPORTED_TYPES) { "Unsupported exercise type: $type" }
        if (type == MULTIPLE_CHOICE) {
            require(choices.isNotEmpty()) { "A multiple-choice exercise needs choices." }
            require(correctIndex in choices.indices) { "correctIndex must point to a choice." }
        }
        if (type == TEXT_ENTRY) {
            require(acceptedAnswers.isNotEmpty()) { "A text-entry exercise needs acceptedAnswers." }
        }
    }

    companion object {
        const val MULTIPLE_CHOICE = "multiple_choice"
        const val TEXT_ENTRY = "text_entry"
        val SUPPORTED_TYPES = setOf(MULTIPLE_CHOICE, TEXT_ENTRY)
    }
}
