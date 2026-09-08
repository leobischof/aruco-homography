# Der C++-Rechenkern. Gebaut wird er ueber ./dev.ps1 build-core, das die
# Werkzeugkette sucht und die Pfade hier hineinreicht - von Hand:
#
#   cmake -S core -B core/build -G Ninja -DCMAKE_BUILD_TYPE=Release \
#         -DOpenCV_DIR=<sdk>/build -Dpybind11_DIR=<venv>/.../pybind11 \
#         -DPython_EXECUTABLE=<venv>/Scripts/python.exe
#
# Zwei Dinge entstehen: das Python-Modul `aruco_core` (die Bindung, gegen die die
# vorhandene Testsuite mit ARUCO_CORE=cpp faehrt) und `aruco_conformance` (der
# Pruefstand gegen shared/fixtures/).
#
# DREI ZIELE, EINE QUELLE. Dieselbe Datei uebersetzt auch fuer Android (NDK) und
# fuer den Browser (Emscripten) - siehe docs/cpp-migration/stage-4-cross-targets.md
# und ./dev.ps1 build-core-wasm / build-core-android. Was je Ziel verschieden ist,
# steht unten hinter einer Fallunterscheidung und nirgends sonst; der C++-Quelltext
# selbst kennt keine Ziel-Ifdefs. Genau das ist die Behauptung, fuer die dieser
# Umzug betrieben wird.

cmake_minimum_required(VERSION 3.21)  # 3.21 wegen $<TARGET_RUNTIME_DLLS:...>
project(aruco_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Bauart" FORCE)
endif()

set(ARUCO_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(ARUCO_SHARED_DIR "${ARUCO_REPO_ROOT}/shared")

# --- Was dieser Bau liefert ---------------------------------------------------
# Das Python-Modul ergibt nur auf dem Rechner Sinn, auf dem die Testsuite laeuft.
# Ein Kreuzbau (NDK, Emscripten) hat kein Ziel-Python und braucht auch keines:
# dort ist die Bibliothek das Erzeugnis, und der Pruefstand ist der Beleg.
if(CMAKE_CROSSCOMPILING)
  set(ARUCO_PYTHON_DEFAULT OFF)
else()
  set(ARUCO_PYTHON_DEFAULT ON)
endif()
option(ARUCO_BUILD_PYTHON "Das Python-Modul aruco_core bauen" ${ARUCO_PYTHON_DEFAULT})
option(ARUCO_BUILD_CONFORMANCE "Den Pruefstand aruco_conformance bauen" ON)

# `geometry` ist in OpenCV 5 ein eigenes Modul: cv::contourArea wohnt dort und
# nicht mehr in imgproc.
find_package(OpenCV REQUIRED COMPONENTS core geometry imgproc objdetect)

if(ARUCO_BUILD_PYTHON)
  # pybind11 sucht dabei auch Python und legt Python_EXECUTABLE fest - dasselbe
  # venv, das die Testsuite fuehrt. Die Erzeugungsschritte unten benutzen es, damit
  # nicht zwei verschiedene Python im Spiel sind.
  # PYBIND11_FINDPYTHON: ohne das greift pybind11 zum alten FindPythonLibsNew und
  # nimmt das erstbeste Python vom PATH - hier war das die Store-Installation und
  # nicht das venv, gegen das die Testsuite laeuft. Das Modul liesse sich dann
  # gegen die falsche python313.lib binden.
  set(PYBIND11_FINDPYTHON ON)
  find_package(pybind11 CONFIG REQUIRED)
  set(ARUCO_HOST_PYTHON "${Python_EXECUTABLE}" CACHE FILEPATH "Python fuer die Erzeugungsschritte")
endif()

# Die beiden Erzeugungsschritte (Konstanten-Header, Fixture-Paket) laufen auf dem
# BAUENDEN Rechner und nicht auf dem Ziel. Im Kreuzbau gibt es kein pybind11, das
# ein Python fuende - also muss der Aufrufer eines nennen. Und zwar dasselbe venv:
# make_fixture_pack.py braucht cv2, um die PNG in rohe Bytes zu wandeln, und es
# muss dasselbe cv2 sein, das auch tests/test_conformance.py liest. Sonst stuende
# zwischen den beiden Messungen ein anderer PNG-Dekoder.
if(NOT ARUCO_HOST_PYTHON)
  message(FATAL_ERROR
    "ARUCO_HOST_PYTHON ist nicht gesetzt. Im Kreuzbau muss das venv-Python "
    "genannt werden: -DARUCO_HOST_PYTHON=<repo>/venv/Scripts/python.exe")
endif()

message(STATUS "OpenCV ${OpenCV_VERSION} aus ${OpenCV_DIR}")
message(STATUS "Ziel ${CMAKE_SYSTEM_NAME} ${CMAKE_SYSTEM_PROCESSOR} (Kreuzbau: ${CMAKE_CROSSCOMPILING})")
message(STATUS "Python fuer die Erzeugungsschritte: ${ARUCO_HOST_PYTHON}")

# --- Erzeugte Konstanten ------------------------------------------------------
# shared/constants.json ist die einzige Stelle, an der diese Zahlen stehen
# (AGENTS.md, Invariante 4). Der Header entsteht im BAUVERZEICHNIS und nicht im
# Quellbaum: eine erzeugte Datei zwischen den Quellen wird frueher oder spaeter
# eingecheckt, und dann gibt es die Konstanten zweimal.
set(ARUCO_GENERATED_DIR "${CMAKE_BINARY_DIR}/generated")
set(ARUCO_CONSTANTS_HPP "${ARUCO_GENERATED_DIR}/aruco/constants.hpp")

add_custom_command(
  OUTPUT "${ARUCO_CONSTANTS_HPP}"
  COMMAND "${ARUCO_HOST_PYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/gen_constants.py"
          "${ARUCO_SHARED_DIR}/constants.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/include/aruco/constants.hpp.in"
          "${ARUCO_CONSTANTS_HPP}"
  DEPENDS "${ARUCO_SHARED_DIR}/constants.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/include/aruco/constants.hpp.in"
          "${CMAKE_CURRENT_SOURCE_DIR}/tools/gen_constants.py"
  COMMENT "shared/constants.json -> aruco/constants.hpp"
  VERBATIM)

# --- Die Bibliothek -----------------------------------------------------------
add_library(aruco_core_lib STATIC
  src/detect.cpp
  "${ARUCO_CONSTANTS_HPP}")

target_include_directories(aruco_core_lib PUBLIC include "${ARUCO_GENERATED_DIR}")
target_link_libraries(aruco_core_lib PUBLIC ${OpenCV_LIBS})

if(MSVC)
  # /utf-8: die Kommentare in diesem Baum sind deutsch. Ohne das legt MSVC die
  # Codepage der Konsole zugrunde und meckert bei jedem Umlaut, der spaeter
  # einmal hineingerat.
  target_compile_options(aruco_core_lib PUBLIC /utf-8 /W3)
endif()

if(EMSCRIPTEN)
  # Emscripten uebersetzt seit 3.x OHNE Ausnahmebehandlung, wenn man nichts sagt:
  # ein `throw` wird dann zu einem abort(), und ein `catch` verschwindet. Der Kern
  # wirft aber (std::invalid_argument bei einer unbrauchbaren ImageView), OpenCV
  # wirft (CV_Assert), und der Pruefstand faengt. Ohne dieses Flag stuerbe der
  # Browser-Bau bei jedem Fehler wortlos ab, statt ihn zu melden.
  #
  # PUBLIC/INTERFACE, weil das Entfalten durch JEDEN Rahmen dazwischen muss: das
  # OpenCV fuer WASM ist mit demselben Schalter gebaut (siehe die Anleitung in
  # docs/cpp-migration/stage-4-cross-targets.md). Fehlt er auf einer Seite, endet
  # die Ausnahme im abort().
  target_compile_options(aruco_core_lib PUBLIC -fexceptions)
  target_link_options(aruco_core_lib PUBLIC -fexceptions)
endif()

# --- Das Python-Modul ---------------------------------------------------------
if(ARUCO_BUILD_PYTHON)
  pybind11_add_module(aruco_core bindings/python.cpp)
  target_link_libraries(aruco_core PRIVATE aruco_core_lib)
endif()

# --- Der Pruefstand -----------------------------------------------------------
# Das Fixture-Paket: rohe Pixel plus Grundwahrheit, mechanisch aus
# shared/fixtures/ abgeleitet. Warum nicht direkt die PNG: siehe den Kopf von
# core/tools/make_fixture_pack.py.
if(ARUCO_BUILD_CONFORMANCE)
  set(ARUCO_FIXTURE_DIR "${CMAKE_BINARY_DIR}/fixtures")
  set(ARUCO_FIXTURE_PACK "${ARUCO_FIXTURE_DIR}/fixtures.txt")

  file(GLOB ARUCO_FIXTURE_SOURCES
    "${ARUCO_SHARED_DIR}/fixtures/expected/*.json"
    "${ARUCO_SHARED_DIR}/fixtures/scenes/*.png")

  add_custom_command(
    OUTPUT "${ARUCO_FIXTURE_PACK}"
    COMMAND "${ARUCO_HOST_PYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/make_fixture_pack.py"
            "${ARUCO_SHARED_DIR}/fixtures" "${ARUCO_FIXTURE_DIR}"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/tools/make_fixture_pack.py" ${ARUCO_FIXTURE_SOURCES}
    COMMENT "shared/fixtures/ -> rohe Pixel und Grundwahrheit fuer den Pruefstand"
    VERBATIM)

  add_custom_target(aruco_fixtures ALL DEPENDS "${ARUCO_FIXTURE_PACK}")

  add_executable(aruco_conformance tests/conformance.cpp)
  target_link_libraries(aruco_conformance PRIVATE aruco_core_lib)
  add_dependencies(aruco_conformance aruco_fixtures)

  if(EMSCRIPTEN)
    # Der Pruefstand liest seine Szenen mit std::ifstream aus dem Dateisystem.
    # NODERAWFS legt Emscriptens virtuelles Dateisystem beiseite und reicht die
    # Aufrufe an Node durch - damit liest der WASM-Bau BUCHSTAEBLICH DIESELBEN
    # Bytes wie der Windows-Bau, aus derselben Datei, ohne Umweg und ohne Kopie.
    # Das ist der Grund, warum hier Node und nicht der Browser gemessen wird: im
    # Browser muesste das Paket erst hineingereicht werden, und jede Kopie ist
    # eine Stelle, an der ein Unterschied entstehen koennte, den man dann dem
    # Detektor zuschriebe.
    #
    # ALLOW_MEMORY_GROWTH: eine Szene ist 2400x1800x3 = 12,4 MiB, und der
    # Detektor legt mehrere solcher Bilder an. Der Vorgabespeicher (16 MiB)
    # reicht dafuer nicht.
    #
    # EXIT_RUNTIME: ohne das verfaellt der Rueckgabewert von main() und der
    # Pruefstand meldete auch dann Erfolg, wenn eine Ecke danebenliegt.
    #
    # STACK_SIZE: Emscripten gibt seit 3.1.27 nur 64 KiB, native Ziele geben
    # Megabytes. OpenCVs Aufrufketten sind tief.
    target_link_options(aruco_conformance PRIVATE
      -sNODERAWFS=1
      -sALLOW_MEMORY_GROWTH=1
      -sEXIT_RUNTIME=1
      -sSTACK_SIZE=8MB)
  endif()
endif()

# --- Laufzeit-DLLs neben die Erzeugnisse legen --------------------------------
# opencv_world500.dll steht im SDK und in keinem PATH. Sie daneben zu legen macht
# beide Erzeugnisse fuer sich lauffaehig: Windows sucht neben einer .pyd, bevor
# es den PATH befragt, und niemand muss eine Umgebungsvariable setzen, damit die
# Testsuite den Kern findet.
#
# Nur auf Windows: Android und WASM binden statisch, dort gibt es nichts
# danebenzulegen, und $<TARGET_RUNTIME_DLLS:...> waere dort leer.
if(WIN32)
  set(ARUCO_RUNTIME_TARGETS "")
  if(ARUCO_BUILD_PYTHON)
    list(APPEND ARUCO_RUNTIME_TARGETS aruco_core)
  endif()
  if(ARUCO_BUILD_CONFORMANCE)
    list(APPEND ARUCO_RUNTIME_TARGETS aruco_conformance)
  endif()
  foreach(target ${ARUCO_RUNTIME_TARGETS})
    add_custom_command(TARGET ${target} POST_BUILD
      COMMAND "${CMAKE_COMMAND}" -E copy_if_different
              "$<TARGET_RUNTIME_DLLS:${target}>" "$<TARGET_FILE_DIR:${target}>"
      COMMAND_EXPAND_LISTS)
  endforeach()
endif()
