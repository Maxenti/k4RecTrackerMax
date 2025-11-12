# Install script for directory: /afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/install")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "RelWithDebInfo")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "0")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set path to fallback-tool for dependency-resolution.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/k4RecTracker" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/headers_db.csv")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64/cmake/k4RecTracker" TYPE FILE FILES
    "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/k4RecTrackerConfig.cmake"
    "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/k4RecTrackerConfigVersion.cmake"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/k4RecTracker" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/include/k4RecTracker/k4RecTrackerVersion.h")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/cmake/k4RecTracker/k4RecTrackerTargets.cmake")
    file(DIFFERENT _cmake_export_file_changed FILES
         "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/cmake/k4RecTracker/k4RecTrackerTargets.cmake"
         "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/CMakeFiles/Export/69ed724b694ef911d59e6b5b9efbb773/k4RecTrackerTargets.cmake")
    if(_cmake_export_file_changed)
      file(GLOB _cmake_old_config_files "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/cmake/k4RecTracker/k4RecTrackerTargets-*.cmake")
      if(_cmake_old_config_files)
        string(REPLACE ";" ", " _cmake_old_config_files_text "${_cmake_old_config_files}")
        message(STATUS "Old export file \"$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/cmake/k4RecTracker/k4RecTrackerTargets.cmake\" will be replaced.  Removing files [${_cmake_old_config_files_text}].")
        unset(_cmake_old_config_files_text)
        file(REMOVE ${_cmake_old_config_files})
      endif()
      unset(_cmake_old_config_files)
    endif()
    unset(_cmake_export_file_changed)
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64/cmake/k4RecTracker" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/CMakeFiles/Export/69ed724b694ef911d59e6b5b9efbb773/k4RecTrackerTargets.cmake")
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ww][Ii][Tt][Hh][Dd][Ee][Bb][Ii][Nn][Ff][Oo])$")
    file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64/cmake/k4RecTracker" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/CMakeFiles/Export/69ed724b694ef911d59e6b5b9efbb773/k4RecTrackerTargets-relwithdebinfo.cmake")
  endif()
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for each subdirectory.
  include("/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/DCHdigi/cmake_install.cmake")
  include("/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/ARCdigi/cmake_install.cmake")
  include("/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/VTXdigi/cmake_install.cmake")
  include("/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/Tracking/cmake_install.cmake")

endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
if(CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_COMPONENT MATCHES "^[a-zA-Z0-9_.+-]+$")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
  else()
    string(MD5 CMAKE_INST_COMP_HASH "${CMAKE_INSTALL_COMPONENT}")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INST_COMP_HASH}.txt")
    unset(CMAKE_INST_COMP_HASH)
  endif()
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
