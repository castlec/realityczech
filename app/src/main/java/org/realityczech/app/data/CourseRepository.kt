package org.realityczech.app.data

import android.content.Context
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import org.realityczech.app.model.Course
import org.realityczech.app.model.CourseIndex
import org.realityczech.app.model.CourseUnit
import org.realityczech.app.model.LearningResource
import org.realityczech.app.model.Lesson
import org.realityczech.app.model.MediaCatalog
import org.realityczech.app.model.MediaCatalogAsset

private const val LESSON_SECTION_PROVIDER = "lesson-section"

class CourseRepository(private val context: Context) {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = false
    }

    fun load(): Course {
        val index = readJson<CourseIndex>(COURSE_INDEX_ASSET)
        val mediaCatalog = readJson<MediaCatalog>(MEDIA_CATALOG_ASSET)
        val audioByLesson = assetsByLesson(mediaCatalog) { it.isBundledAudio }
        val documentImagesByLesson = assetsByLesson(mediaCatalog) { it.isVendorImage }
        val units = index.units.map { unit ->
            CourseUnit(
                id = unit.id,
                title = unit.title,
                description = unit.description,
                lessons = unit.lessonFiles.map { filename ->
                    val lesson = readJson<Lesson>("$LESSON_DIRECTORY/$filename")
                    lesson
                        .withGeneratedAudio(audioByLesson[lesson.id].orEmpty())
                        .withDocumentImages(documentImagesByLesson[lesson.id].orEmpty())
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

    private fun assetsByLesson(
        catalog: MediaCatalog,
        predicate: (MediaCatalogAsset) -> Boolean,
    ): Map<String, List<MediaCatalogAsset>> = catalog.assets
        .asSequence()
        .filter(predicate)
        .flatMap { asset -> asset.applicableLessonIds.asSequence().map { lessonId -> lessonId to asset } }
        .groupBy(keySelector = { it.first }, valueTransform = { it.second })

    private fun Lesson.withGeneratedAudio(assets: List<MediaCatalogAsset>): Lesson {
        if (assets.isEmpty()) return this
        val existingPaths = resources.map { it.assetPath }.filter { it.isNotBlank() }.toSet()
        val generated = assets
            .asSequence()
            .filterNot { "media/${it.localPath}" in existingPaths }
            .sortedWith(compareBy<MediaCatalogAsset> { it.label.lowercase() }.thenBy { it.id })
            .map { asset ->
                val speakerNote = if (asset.speaker.isBlank()) {
                    "Human recording. The source filename does not identify the speaker."
                } else {
                    "Human recording by ${asset.speaker}."
                }
                LearningResource(
                    title = asset.label,
                    kind = "audio",
                    url = asset.sourcePage.ifBlank { asset.sourceUrl },
                    note = listOf(speakerNote, asset.attribution)
                        .filter { it.isNotBlank() }
                        .joinToString("\n"),
                    provider = LearningResource.ASSET_AUDIO_PROVIDER,
                    assetPath = "media/${asset.localPath}",
                    fallbackText = asset.fallbackText.ifBlank { asset.label },
                    attribution = asset.attribution,
                )
            }
            .toList()
        return copy(resources = resources + generated)
    }

    private fun Lesson.withDocumentImages(assets: List<MediaCatalogAsset>): Lesson {
        if (assets.isEmpty()) return this
        val sectionResources = sections.mapIndexed { index, section ->
            LearningResource(
                title = section.heading,
                kind = "lesson section",
                url = sourceUrl,
                note = section.body,
                provider = LESSON_SECTION_PROVIDER,
                fallbackText = section.examples.joinToString("\n"),
                sourceOrder = index,
            )
        }
        val imageResources = assets
            .sortedWith(
                compareBy<MediaCatalogAsset> { it.sourceOrder ?: Int.MAX_VALUE }
                    .thenBy { it.label.lowercase() }
                    .thenBy { it.id },
            )
            .map { asset ->
                val inheritedNote = if (asset.attributionInherited) {
                    "Site-level Reality Czech attribution applies because the document contains no narrower credit."
                } else {
                    ""
                }
                LearningResource(
                    title = asset.label.ifBlank { "Source illustration" },
                    kind = "source document image",
                    url = asset.sourcePage.ifBlank { asset.sourceUrl },
                    note = listOf(asset.contextText, inheritedNote)
                        .filter { it.isNotBlank() }
                        .joinToString("\n"),
                    provider = LearningResource.VENDOR_IMAGE_PROVIDER,
                    assetPath = "media/${asset.localPath}",
                    attribution = asset.attribution,
                    semanticRole = asset.semanticRole,
                    placementHeading = asset.placementHeading,
                    caption = asset.caption,
                    contextText = asset.contextText,
                    sourceOrder = asset.sourceOrder,
                )
            }
        return copy(
            sections = emptyList(),
            resources = resources + sectionResources + imageResources,
        )
    }

    private inline fun <reified T> readJson(path: String): T {
        val raw = context.assets.open(path).bufferedReader().use { it.readText() }
        return json.decodeFromString(raw)
    }

    companion object {
        private const val COURSE_INDEX_ASSET = "course/index.json"
        private const val LESSON_DIRECTORY = "course/lessons"
        private const val MEDIA_CATALOG_ASSET = "media/catalog.json"
    }
}
