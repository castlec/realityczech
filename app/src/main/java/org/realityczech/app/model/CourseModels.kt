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
    val mediaId: String = "",
    val startSeconds: Int? = null,
)

@Serializable
data class LearningResource(
    val title: String,
    val kind: String,
    val url: String,
    val note: String = "",
    val provider: String = "",
    val mediaId: String = "",
    val assetPath: String = "",
    val fallbackText: String = "",
    val attribution: String = "",
) {
    val isEmbeddedVideo: Boolean
        get() = provider == YOUTUBE_PROVIDER && mediaId.isNotBlank()

    val isEmbeddedAudio: Boolean
        get() = provider == ASSET_AUDIO_PROVIDER && assetPath.isNotBlank()

    companion object {
        const val YOUTUBE_PROVIDER = "youtube"
        const val ASSET_AUDIO_PROVIDER = "asset-audio"
    }
}

@Serializable
data class MediaCatalog(
    val version: Int,
    val license: String = "",
    val assets: List<MediaCatalogAsset>,
)

@Serializable
data class MediaCatalogAsset(
    val id: String,
    val kind: String,
    val delivery: String,
    val lessonId: String = "",
    val lessonIds: List<String> = emptyList(),
    val label: String = "",
    val sourcePage: String = "",
    val sourcePages: List<String> = emptyList(),
    val sourceUrl: String = "",
    val localPath: String = "",
    val attribution: String = "",
    val speaker: String = "",
    val fallbackText: String = "",
) {
    val applicableLessonIds: List<String>
        get() = lessonIds.ifEmpty { listOfNotNull(lessonId.takeIf(String::isNotBlank)) }

    val isBundledAudio: Boolean
        get() = kind == "audio" && delivery == "bundle" && localPath.isNotBlank()
}

@Serializable
data class Exercise(
    val type: String,
    val prompt: String,
    val choices: List<String> = emptyList(),
    val correctIndex: Int = -1,
    val acceptedAnswers: List<String> = emptyList(),
    val spokenText: String = "",
    val explanation: String,
) {
    init {
        require(type in SUPPORTED_TYPES) { "Unsupported exercise type: $type" }
        if (type in CHOICE_TYPES) {
            require(choices.isNotEmpty()) { "A choice exercise needs choices." }
            require(correctIndex in choices.indices) { "correctIndex must point to a choice." }
        }
        if (type in TEXT_ENTRY_TYPES) {
            require(acceptedAnswers.isNotEmpty()) { "A text-entry exercise needs acceptedAnswers." }
        }
        if (type in LISTENING_TYPES) {
            require(spokenText.isNotBlank()) { "A listening exercise needs spokenText." }
        }
    }

    companion object {
        const val MULTIPLE_CHOICE = "multiple_choice"
        const val TEXT_ENTRY = "text_entry"
        const val LISTEN_SELECT = "listen_select"
        const val LISTEN_TYPE = "listen_type"

        val CHOICE_TYPES = setOf(MULTIPLE_CHOICE, LISTEN_SELECT)
        val TEXT_ENTRY_TYPES = setOf(TEXT_ENTRY, LISTEN_TYPE)
        val LISTENING_TYPES = setOf(LISTEN_SELECT, LISTEN_TYPE)
        val SUPPORTED_TYPES = CHOICE_TYPES + TEXT_ENTRY_TYPES
    }
}
