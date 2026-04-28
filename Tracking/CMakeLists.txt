# Tracking/CMakeLists.txt
cmake_minimum_required(VERSION 3.16)
set(PackageName Tracking)
project(${PackageName})

# -------- Dependencies ----------
find_package(Gaudi REQUIRED)
# GaudiAlg target name changed across versions, pick what's available
set(GAUDI_ALG_TGT "")
if (TARGET Gaudi::GaudiAlg)
  set(GAUDI_ALG_TGT Gaudi::GaudiAlg)
elseif (TARGET Gaudi::GaudiAlgLib)
  set(GAUDI_ALG_TGT Gaudi::GaudiAlgLib)
elseif (TARGET GaudiAlgLib)
  set(GAUDI_ALG_TGT GaudiAlgLib)
endif()
message(STATUS "GaudiAlg target used: '${GAUDI_ALG_TGT}' (empty means none)")

find_package(EDM4HEP REQUIRED)
find_package(k4FWCore REQUIRED)
find_package(DD4hep REQUIRED COMPONENTS DDRec DDCore)
find_package(onnxruntime REQUIRED)
find_package(ROOT REQUIRED COMPONENTS RIO Tree)
find_package(Eigen3 REQUIRED)
# torch can be header-only or a cmake target depending on env
find_package(Torch QUIET)  # provides Torch::Torch if available

# Optional external stack for Pandora/Marlin (used by some headers)
find_package(MarlinUtil QUIET)
if(DEFINED ENV{PANDORAPFA})
  list(APPEND CMAKE_MODULE_PATH $ENV{PANDORAPFA}/cmakemodules)
endif()
foreach(pkg MarlinUtil PandoraSDK)
  if(${pkg}_FOUND)
    include_directories(${${pkg}_INCLUDE_DIRS})
    link_libraries(${${pkg}_LIBRARIES})
    add_definitions(${${pkg}_DEFINITIONS})
  endif()
endforeach()

# Delphes (optional): keep variables if your build sets them
# They may be empty; linking with empty is harmless.
set(DELPHES_LIBRARIES ${DELPHES_LIBRARIES})

# -------- ExternalData for test model ----------
include(ExternalData)
list(APPEND ExternalData_URL_TEMPLATES
  "https://key4hep.web.cern.ch:443/testFiles/k4RecTracker/%(hash)"
)

# -------- Sources / Headers ----------
file(GLOB sources
  ${PROJECT_SOURCE_DIR}/src/*.cpp
  ${PROJECT_SOURCE_DIR}/components/*.cpp
)
file(GLOB headers
  ${PROJECT_SOURCE_DIR}/include/*.h
)

# ---- Optional: GenFit2 support (robust & OFF if not found) ----
option(USE_GENFIT2 "Build GenFit2-based fitter(s)" ON)

# Try both the upstream package and manual hints
set(_GF_HINTS $ENV{GENFIT_DIR} ${GENFIT_DIR})
find_path(GENFIT2_INCLUDE_DIR genfit/RKTrackRep.h
          HINTS ${_GF_HINTS} PATH_SUFFIXES include)
find_library(GENFIT2_LIBRARY NAMES genfit2
             HINTS ${_GF_HINTS} PATH_SUFFIXES lib64 lib)

if(USE_GENFIT2)
  if(GENFIT2_INCLUDE_DIR AND GENFIT2_LIBRARY)
    message(STATUS "GenFit2 include: ${GENFIT2_INCLUDE_DIR}")
    message(STATUS "GenFit2 library: ${GENFIT2_LIBRARY}")
    set(HAVE_GENFIT2 TRUE)
  else()
    message(WARNING "USE_GENFIT2=ON but GenFit2 not found -> disabling GenFit2.")
    set(HAVE_GENFIT2 FALSE)
  endif()
else()
  set(HAVE_GENFIT2 FALSE)
endif()

# If GenFit2 not available, exclude the GenFit2 sources from the module
if(NOT HAVE_GENFIT2)
  list(FILTER sources EXCLUDE REGEX ".*/GenFit2.*\\.cpp$")
endif()

# Exclude the experimental v03 fitter entirely.
list(FILTER sources EXCLUDE REGEX ".*/GenFit2DCHFitter_v03\\.cpp$")

# -------- Build the Gaudi module (the plugin) ----------
gaudi_add_module(${PackageName}
  SOURCES ${sources}
  LINK
    Gaudi::GaudiKernel
    ${GAUDI_ALG_TGT}
    EDM4HEP::edm4hep
    k4FWCore::k4FWCore
    k4FWCore::k4Interface
    extensionDict
    onnxruntime::onnxruntime
    DD4hep::DDRec
    DD4hep::DDCore
    Eigen3::Eigen
    ${DELPHES_LIBRARIES}
)

# Torch is optional—link it only if target exists, else try 'torch' var
if(TARGET Torch::Torch)
  target_link_libraries(${PackageName} PRIVATE Torch::Torch)
elseif(TORCH_LIBRARIES)
  target_link_libraries(${PackageName} PRIVATE ${TORCH_LIBRARIES})
endif()

target_include_directories(${PackageName} PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
  ${MarlinUtil_INCLUDE_DIRS}
  ${DELPHES_INCLUDE_DIRS}
)

set_target_properties(${PackageName} PROPERTIES PUBLIC_HEADER "${headers}")

# ---- Add GenFit2 bits when present ----
if(HAVE_GENFIT2)
  target_compile_definitions(${PackageName} PRIVATE HAVE_GENFIT2=1)
  target_include_directories(${PackageName} PRIVATE ${GENFIT2_INCLUDE_DIR})
  target_link_libraries(${PackageName} PRIVATE ${GENFIT2_LIBRARY} Eigen3::Eigen)

  # Optional standalone fitter tool (kept from your old tree)
  if(EXISTS ${CMAKE_SOURCE_DIR}/Tracking/fitter/fit_ggtf_tracks.cpp)
    add_executable(fit_ggtf_tracks ${CMAKE_SOURCE_DIR}/Tracking/fitter/fit_ggtf_tracks.cpp)
    target_include_directories(fit_ggtf_tracks PRIVATE ${GENFIT2_INCLUDE_DIR})
    target_link_libraries(fit_ggtf_tracks PRIVATE
        ${GENFIT2_LIBRARY}
        Eigen3::Eigen
        EDM4HEP::edm4hep
        podio::podioRootIO
        ROOT::Tree ROOT::RIO
        k4FWCore::k4FWCore
        k4FWCore::k4Interface
        extensionDict)
    target_compile_features(fit_ggtf_tracks PRIVATE cxx_std_17)
  endif()
else()
  message(STATUS "GenFit2 disabled.")
endif()

# -------- Tests / scripts ----------
file(GLOB scripts ${PROJECT_SOURCE_DIR}/test/*.py)
file(COPY ${scripts} DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/test)

# Standard tests from your tree (safe if files exist)
SET(test_name "test_TracksFromGenParticles")
if(EXISTS ${CMAKE_SOURCE_DIR}/Tracking/test/testTracksFromGenParticles/test_TracksFromGenParticles.sh)
  ADD_TEST(NAME ${test_name} COMMAND sh +x test_TracksFromGenParticles.sh)
  set_test_env(${test_name})
  set_tests_properties(${test_name} PROPERTIES
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}/Tracking/test/testTracksFromGenParticles")
endif()

SET(test_name "test_TrackFinder")
if(EXISTS ${CMAKE_SOURCE_DIR}/Tracking/test/testTrackFinder/test_trackFinder.sh)
  ExternalData_Add_Test(test_TrackFinder
    NAME ${test_name}
    COMMAND sh +x Tracking/test/testTrackFinder/test_trackFinder.sh
            DATA{${CMAKE_SOURCE_DIR}/Tracking/test/inputFiles/SimpleGatrIDEAv3o1.onnx})
  set_test_env(${test_name})
  set_tests_properties(${test_name} PROPERTIES WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}")
  ExternalData_Add_Target(${test_name})
endif()

SET(test_name "Noddsim_track_test")
if(EXISTS ${CMAKE_SOURCE_DIR}/Tracking/test/testTrackFinder/Noddsim_track_test.sh)
  ExternalData_Add_Test(Noddsim_track_test
    NAME ${test_name}
    COMMAND sh +x Tracking/test/testTrackFinder/Noddsim_track_test.sh
            DATA{${CMAKE_SOURCE_DIR}/Tracking/test/inputFiles/SimpleGatrIDEAv3o1.onnx})
  set_test_env(${test_name})
  set_tests_properties(${test_name} PROPERTIES WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}")
  ExternalData_Add_Target(${test_name})
endif()

# -------- Install ----------
install(TARGETS ${PackageName}
  EXPORT ${CMAKE_PROJECT_NAME}Targets
  RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}" COMPONENT bin
  LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}" COMPONENT shlib
  PUBLIC_HEADER DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/${CMAKE_PROJECT_NAME}" COMPONENT dev
)
install(FILES ${scripts} DESTINATION test)

# Print where the plugin will land (so you can export GAUDI_PLUGIN_PATH accordingly)
get_target_property(_out_dir ${PackageName} LIBRARY_OUTPUT_DIRECTORY)
message(STATUS "[${PackageName}] will install to: ${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}")