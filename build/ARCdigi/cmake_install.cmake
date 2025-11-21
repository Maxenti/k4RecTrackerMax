# Install script for directory: /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/ARCdigi

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install")
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
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so"
         RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE MODULE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/ARCdigi/libARCdigi.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so"
         OLD_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/.plugins:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib:"
         NEW_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/ARCdigi.components")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/python/ARCdigi" TYPE FILE FILES
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/ARCdigi/genConfDir/ARCdigi/ARCdigiConf.py"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/ARCdigi/genConfDir/ARCdigi/__init__.py"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/ARCdigi.confdb")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/ARCdigi.confdb2")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so"
         RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE MODULE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/ARCdigi/libARCdigi.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so"
         OLD_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/.plugins:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib:"
         NEW_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libARCdigi.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/@{CMAKE_PROJECT_NAME}" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/ARCdigi/include/ARCdigitizer.h")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/test" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/ARCdigi/test/runARCdigitizer.py")
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/ARCdigi/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
