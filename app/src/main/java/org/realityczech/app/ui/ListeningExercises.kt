package org.realityczech.app.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.realityczech.app.model.Exercise

@Composable
internal fun ListeningChoiceExercise(number: Int, exercise: Exercise) {
    var selected by remember(exercise.prompt) { mutableIntStateOf(-1) }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("$number. ${exercise.prompt}", fontWeight = FontWeight.Bold)
            CzechSpeakControls(text = exercise.spokenText)
            exercise.choices.forEachIndexed { index, choice ->
                Row(
                    modifier = Modifier.fillMaxWidth().clickable { selected = index },
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    RadioButton(selected = selected == index, onClick = { selected = index })
                    Text(choice)
                }
            }
            if (selected >= 0) {
                val correct = selected == exercise.correctIndex
                Text(
                    if (correct) "Correct. ${exercise.explanation}" else "Not yet. ${exercise.explanation}",
                    color = if (correct) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}

@Composable
internal fun ListeningTextExercise(number: Int, exercise: Exercise) {
    var answer by remember(exercise.prompt) { mutableStateOf("") }
    var submitted by remember(exercise.prompt) { mutableStateOf(false) }
    val accepted = exercise.acceptedAnswers.map(::normalizeListeningAnswer).toSet()
    val correct = normalizeListeningAnswer(answer) in accepted

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("$number. ${exercise.prompt}", fontWeight = FontWeight.Bold)
            CzechSpeakControls(text = exercise.spokenText)
            OutlinedTextField(
                value = answer,
                onValueChange = {
                    answer = it
                    submitted = false
                },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("Type what you hear") },
            )
            Button(onClick = { submitted = true }, enabled = answer.isNotBlank()) {
                Text("Check")
            }
            if (submitted) {
                Text(
                    if (correct) "Correct. ${exercise.explanation}" else "Not yet. ${exercise.explanation}",
                    color = if (correct) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}

private fun normalizeListeningAnswer(value: String): String = value
    .trim()
    .lowercase()
    .trimEnd('.', '!', '?')
    .replace(Regex("\\s+"), " ")
