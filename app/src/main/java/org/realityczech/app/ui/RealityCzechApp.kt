package org.realityczech.app.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.realityczech.app.data.ProgressStore
import org.realityczech.app.model.Course
import org.realityczech.app.model.Exercise
import org.realityczech.app.model.LearningResource
import org.realityczech.app.model.Lesson
import org.realityczech.app.model.TranscriptLine
import org.realityczech.app.model.VocabularyItem

private enum class MainSection(val label: String) {
    LEARN("Learn"),
    REVIEW("Review"),
    ABOUT("About"),
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RealityCzechApp(course: Course, progressStore: ProgressStore) {
    var section by remember { mutableStateOf(MainSection.LEARN) }
    var selectedLesson by remember { mutableStateOf<Lesson?>(null) }
    val completion = remember {
        mutableStateMapOf<String, Boolean>().apply {
            course.lessons.forEach { lesson -> put(lesson.id, progressStore.isComplete(lesson.id)) }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(selectedLesson?.title ?: course.title) },
                navigationIcon = {
                    if (selectedLesson != null) {
                        TextButton(onClick = { selectedLesson = null }) { Text("Back") }
                    }
                },
            )
        },
        bottomBar = {
            if (selectedLesson == null) {
                NavigationBar {
                    MainSection.entries.forEach { destination ->
                        NavigationBarItem(
                            selected = section == destination,
                            onClick = { section = destination },
                            icon = { Text(destination.label.take(1)) },
                            label = { Text(destination.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        Box(modifier = Modifier.padding(padding).fillMaxSize()) {
            val lesson = selectedLesson
            if (lesson != null) {
                LessonScreen(
                    lesson = lesson,
                    completed = completion[lesson.id] == true,
                    onCompletedChange = { complete ->
                        completion[lesson.id] = complete
                        progressStore.setComplete(lesson.id, complete)
                    },
                )
            } else {
                when (section) {
                    MainSection.LEARN -> LearnScreen(course, completion, onLessonSelected = { selectedLesson = it })
                    MainSection.REVIEW -> ReviewScreen(course.lessons.flatMap { it.vocabulary }.distinctBy { it.czech })
                    MainSection.ABOUT -> AboutScreen(course)
                }
            }
        }
    }
}

@Composable
private fun LearnScreen(
    course: Course,
    completion: Map<String, Boolean>,
    onLessonSelected: (Lesson) -> Unit,
) {
    val completedCount = completion.values.count { it }
    val totalCount = course.lessons.size.coerceAtLeast(1)

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(course.description, style = MaterialTheme.typography.bodyLarge)
            Spacer(Modifier.height(12.dp))
            Text("$completedCount of ${course.lessons.size} lessons complete")
            LinearProgressIndicator(
                progress = completedCount.toFloat() / totalCount.toFloat(),
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
            )
        }

        course.units.forEach { unit ->
            item {
                Text(unit.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text(unit.description, style = MaterialTheme.typography.bodyMedium)
            }

            unit.lessons.groupBy { it.day }.forEach { (day, lessons) ->
                item {
                    Text(day, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                }
                items(lessons, key = { it.id }) { lesson ->
                    LessonCard(
                        lesson = lesson,
                        complete = completion[lesson.id] == true,
                        onClick = { onLessonSelected(lesson) },
                    )
                }
            }
        }
    }
}

@Composable
private fun LessonCard(lesson: Lesson, complete: Boolean, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        colors = if (complete) {
            CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
        } else {
            CardDefaults.cardColors()
        },
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(lesson.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(if (complete) "Complete" else "${lesson.estimatedMinutes} min")
            }
            Spacer(Modifier.height(6.dp))
            Text(lesson.summary)
        }
    }
}

@Composable
private fun LessonScreen(
    lesson: Lesson,
    completed: Boolean,
    onCompletedChange: (Boolean) -> Unit,
) {
    val uriHandler = LocalUriHandler.current

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(lesson.day, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
        Text(lesson.summary, style = MaterialTheme.typography.bodyLarge)
        Text("Learning objectives", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        lesson.objectives.forEach { Text("• $it") }

        if (lesson.resources.isNotEmpty()) {
            Text("Original media and sources", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            lesson.resources.forEach { resource -> ResourceCard(resource) }
        }

        lesson.sections.forEach { section ->
            Surface(tonalElevation = 2.dp, shape = MaterialTheme.shapes.medium) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(section.heading, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text(section.body)
                    section.examples.forEach { example ->
                        Text(example, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.primary)
                    }
                }
            }
        }

        if (lesson.transcript.isNotEmpty()) {
            Text("Transcript", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            lesson.transcript.forEach { line -> TranscriptRow(line) }
        }

        if (lesson.vocabulary.isNotEmpty()) {
            Text("Vocabulary", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            lesson.vocabulary.forEach { item -> VocabularyRow(item) }
        }

        if (lesson.exercises.isNotEmpty()) {
            Text("Practice", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            lesson.exercises.forEachIndexed { index, exercise -> ExerciseCard(index + 1, exercise) }
        }

        Button(onClick = { onCompletedChange(!completed) }, modifier = Modifier.fillMaxWidth()) {
            Text(if (completed) "Mark incomplete" else "Mark lesson complete")
        }

        Surface(tonalElevation = 1.dp, shape = MaterialTheme.shapes.medium) {
            Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Source and license", fontWeight = FontWeight.Bold)
                Text("Adapted from ${lesson.sourceAttribution}; ${lesson.contentLicense}.")
                TextButton(onClick = { uriHandler.openUri(lesson.sourceUrl) }) { Text("Open original lesson") }
            }
        }
        Spacer(Modifier.height(20.dp))
    }
}

@Composable
private fun ResourceCard(resource: LearningResource) {
    val uriHandler = LocalUriHandler.current
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(resource.title, fontWeight = FontWeight.Bold)
            Text(resource.kind, style = MaterialTheme.typography.labelMedium)
            if (resource.note.isNotBlank()) Text(resource.note, style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = { uriHandler.openUri(resource.url) }) { Text("Open") }
        }
    }
}

@Composable
private fun TranscriptRow(line: TranscriptLine) {
    Column(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
        if (line.speaker.isNotBlank()) Text(line.speaker, style = MaterialTheme.typography.labelMedium)
        Text(line.czech, fontWeight = FontWeight.Bold)
        if (line.english.isNotBlank()) Text(line.english)
        if (line.note.isNotBlank()) Text(line.note, style = MaterialTheme.typography.bodySmall)
        HorizontalDivider(Modifier.padding(top = 6.dp))
    }
}

@Composable
private fun VocabularyRow(item: VocabularyItem) {
    Column(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(item.czech, fontWeight = FontWeight.Bold)
            Text(item.english)
        }
        if (item.note.isNotBlank()) Text(item.note, style = MaterialTheme.typography.bodySmall)
        HorizontalDivider(Modifier.padding(top = 6.dp))
    }
}

@Composable
private fun ExerciseCard(number: Int, exercise: Exercise) {
    when (exercise.type) {
        Exercise.MULTIPLE_CHOICE -> MultipleChoiceExercise(number, exercise)
        Exercise.TEXT_ENTRY -> TextEntryExercise(number, exercise)
    }
}

@Composable
private fun MultipleChoiceExercise(number: Int, exercise: Exercise) {
    var selected by remember(exercise.prompt) { mutableIntStateOf(-1) }
    val answered = selected >= 0

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("$number. ${exercise.prompt}", fontWeight = FontWeight.Bold)
            exercise.choices.forEachIndexed { index, choice ->
                Row(
                    modifier = Modifier.fillMaxWidth().clickable { selected = index },
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    RadioButton(selected = selected == index, onClick = { selected = index })
                    Text(choice)
                }
            }
            if (answered) {
                val correct = selected == exercise.correctIndex
                ExerciseFeedback(correct, exercise.explanation)
            }
        }
    }
}

@Composable
private fun TextEntryExercise(number: Int, exercise: Exercise) {
    var answer by remember(exercise.prompt) { mutableStateOf("") }
    var submitted by remember(exercise.prompt) { mutableStateOf(false) }
    val accepted = exercise.acceptedAnswers.map(::normalizeAnswer).toSet()
    val correct = normalizeAnswer(answer) in accepted

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("$number. ${exercise.prompt}", fontWeight = FontWeight.Bold)
            OutlinedTextField(
                value = answer,
                onValueChange = {
                    answer = it
                    submitted = false
                },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("Your answer") },
            )
            Button(onClick = { submitted = true }, enabled = answer.isNotBlank()) { Text("Check") }
            if (submitted) ExerciseFeedback(correct, exercise.explanation)
        }
    }
}

@Composable
private fun ExerciseFeedback(correct: Boolean, explanation: String) {
    Text(
        if (correct) "Correct. $explanation" else "Not yet. $explanation",
        color = if (correct) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
    )
}

private fun normalizeAnswer(value: String): String = value
    .trim()
    .lowercase()
    .trimEnd('.', '!', '?')
    .replace(Regex("\\s+"), " ")

@Composable
private fun ReviewScreen(vocabulary: List<VocabularyItem>) {
    if (vocabulary.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text("No review items yet.") }
        return
    }

    var index by remember { mutableIntStateOf(0) }
    var revealed by remember { mutableStateOf(false) }
    val item = vocabulary[index]

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Card ${index + 1} of ${vocabulary.size}")
        Spacer(Modifier.height(16.dp))
        Card(
            modifier = Modifier.fillMaxWidth().height(240.dp).clickable { revealed = !revealed },
        ) {
            Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
                Text(
                    if (revealed) "${item.english}\n\n${item.note}" else item.czech,
                    style = MaterialTheme.typography.headlineMedium,
                )
            }
        }
        Spacer(Modifier.height(16.dp))
        Text("Tap the card to reveal the meaning.")
        Spacer(Modifier.height(16.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedButton(
                onClick = {
                    index = if (index == 0) vocabulary.lastIndex else index - 1
                    revealed = false
                },
            ) { Text("Previous") }
            Button(
                onClick = {
                    index = (index + 1) % vocabulary.size
                    revealed = false
                },
            ) { Text("Next") }
        }
    }
}

@Composable
private fun AboutScreen(course: Course) {
    val uriHandler = LocalUriHandler.current
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("About this app", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text("This is an independent, offline-first Android adaptation of the Reality Czech open educational curriculum.")
        Text("Current status: the original Unit 1 sequence is being converted in instructional blocks. Days 1.1–1.3 are included in this build.")
        Text("Content license", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(course.license)
        Button(onClick = { uriHandler.openUri(course.sourceUrl) }) { Text("Open Reality Czech") }
        Text("Reality Czech and its original creators are not responsible for this application. Third-party media remains linked to its original host and license.")
    }
}
