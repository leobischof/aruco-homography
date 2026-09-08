// Der Gradle-Bau der Android-Huelle.
//
// Er liegt unter android/ und NICHT im Wurzelverzeichnis: das Repo ist in erster
// Linie ein Python-Projekt mit einem C++-Kern, und ein build.gradle.kts oben
// liesse jedes Werkzeug glauben, es sei ein Android-Projekt.

pluginManagement {
    repositories {
        // google() zuerst: das Android-Gradle-Plugin kommt von dort und sonst
        // nirgends. gradlePluginPortal() bleibt als Rueckfall fuer alles andere.
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "aruco-homographie-android"
include(":app")
