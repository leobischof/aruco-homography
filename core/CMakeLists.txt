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

# `geometry` ist in OpenCV 5 ein eigenes Modul: cv::contourArea wohnt dort und
# nicht mehr in imgproc.
find_package(OpenCV REQUIRED COMPONENTS core geometry imgproc objdetect)
# pybind11 sucht dabei auch Python und legt Python_EXECUTABLE fest - dasselbe
# venv, das die Testsuite fuehrt. Die Erzeugungsschritte unten benutzen es, damit
# nicht zwei verschiedene Python im Spiel sind.
# PYBIND11_FINDPYTHON: ohne das greift pybind11 zum alten FindPythonLibsNew und
# nimmt das erstbeste Python vom PATH - hier war das die Store-Installation und
# nicht das venv, gegen das die Testsuite laeuft. Das Modul liesse sich dann
# gegen die falsche python313.lib binden.
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

message(STATUS "OpenCV ${OpenCV_VERSION} aus ${OpenCV_DIR}")
message(STATUS "Python ${Python_EXECUTABLE}")

# --- Erzeugte Konstanten ------------------------------------------------------
# shared/constants.json ist die einzige Stelle, an der diese Zahlen stehen
# (AGENTS.md, Invariante 4). Der Header entsteht im BAUVERZEICHNIS und nicht im
# Quellbaum: eine erzeugte Datei zwischen den Quellen wird frueher oder spaeter
# eingecheckt, und dann gibt es die Konstanten zweimal.
set(ARUCO_GENERATED_DIR "${CMAKE_BINARY_DIR}/generated")
set(ARUCO_CONSTANTS_HPP "${ARUCO_GENERATED_DIR}/aruco/constants.hpp")

add_custom_command(
  OUTPUT "${ARUCO_CONSTANTS_HPP}"
  COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/gen_constants.py"
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

# --- Das Python-Modul ---------------------------------------------------------
pybind11_add_module(aruco_core bindings/python.cpp)
target_link_libraries(aruco_core PRIVATE aruco_core_lib)

# --- Der Pruefstand -----------------------------------------------------------
# Das Fixture-Paket: rohe Pixel plus Grundwahrheit, mechanisch aus
# shared/fixtures/ abgeleitet. Warum nicht direkt die PNG: siehe den Kopf von
# core/tools/make_fixture_pack.py.
set(ARUCO_FIXTURE_DIR "${CMAKE_BINARY_DIR}/fixtures")
set(ARUCO_FIXTURE_PACK "${ARUCO_FIXTURE_DIR}/fixtures.txt")

file(GLOB ARUCO_FIXTURE_SOURCES
  "${ARUCO_SHARED_DIR}/fixtures/expected/*.json"
  "${ARUCO_SHARED_DIR}/fixtures/scenes/*.png")

add_custom_command(
  OUTPUT "${ARUCO_FIXTURE_PACK}"
  COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/make_fixture_pack.py"
          "${ARUCO_SHARED_DIR}/fixtures" "${ARUCO_FIXTURE_DIR}"
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/tools/make_fixture_pack.py" ${ARUCO_FIXTURE_SOURCES}
  COMMENT "shared/fixtures/ -> rohe Pixel und Grundwahrheit fuer den Pruefstand"
  VERBATIM)

add_custom_target(aruco_fixtures ALL DEPENDS "${ARUCO_FIXTURE_PACK}")

add_executable(aruco_conformance tests/conformance.cpp)
target_link_libraries(aruco_conformance PRIVATE aruco_core_lib)
add_dependencies(aruco_conformance aruco_fixtures)

# --- Laufzeit-DLLs neben die Erzeugnisse legen --------------------------------
# opencv_world500.dll steht im SDK und in keinem PATH. Sie daneben zu legen macht
# beide Erzeugnisse fuer sich lauffaehig: Windows sucht neben einer .pyd, bevor
# es den PATH befragt, und niemand muss eine Umgebungsvariable setzen, damit die
# Testsuite den Kern findet.
foreach(target aruco_core aruco_conformance)
  add_custom_command(TARGET ${target} POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different
            "$<TARGET_RUNTIME_DLLS:${target}>" "$<TARGET_FILE_DIR:${target}>"
    COMMAND_EXPAND_LISTS)
endforeach()
