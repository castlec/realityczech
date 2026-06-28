package org.realityczech.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import org.realityczech.app.data.CourseRepository
import org.realityczech.app.data.ProgressStore
import org.realityczech.app.ui.RealityCzechApp
import org.realityczech.app.ui.theme.RealityCzechTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val course = CourseRepository(this).load()
        val progressStore = ProgressStore(this)

        setContent {
            RealityCzechTheme {
                RealityCzechApp(course = course, progressStore = progressStore)
            }
        }
    }
}
