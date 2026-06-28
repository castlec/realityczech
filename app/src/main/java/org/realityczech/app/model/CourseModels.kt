package org.realityczech.app.model

import kotlinx.serialization.Serializable

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
    val title: String,
    val summary: String,
    val estimatedMinutes: Int,
    val objectives: List<String>,
    val sections: List<LessonSection>,
    val vocabulary: List<VocabularyItem> = emptyList(),
    val quiz: List<QuizQuestion> = emptyList(),
    val sourceUrl: String,
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
data class QuizQuestion(
    val prompt: String,
    val choices: List<String>,
    val correctIndex: Int,
    val explanation: String,
) {
    init {
        require(choices.isNotEmpty()) { "A quiz question needs choices." }
        require(correctIndex in choices.indices) { "correctIndex must point to a choice." }
    }
}
