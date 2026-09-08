plugins {
    // 8.7.3 zu Gradle 8.9: das ist das Paar, mit dem hier gebaut wurde. Beide
    // Zahlen gehoeren zusammen - AGP verlangt eine Mindestfassung von Gradle und
    // weist eine zu neue ab. Wer eine davon anhebt, hebt die andere mit an und
    // schreibt es in docs/cpp-migration/stage-4-android.md.
    id("com.android.application") version "8.7.3" apply false
}
