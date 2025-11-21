# Install script for directory: /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/DCHdigi

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

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextension.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextension.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextension.so"
         RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE SHARED_LIBRARY FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/libextension.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextension.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextension.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextension.so"
         OLD_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/.plugins:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:"
         NEW_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextension.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/extension" TYPE FILE FILES
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiLocalData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiLocal.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MutableDriftChamberDigiLocal.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiLocalObj.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiLocalCollection.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiLocalCollectionData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigi.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MutableDriftChamberDigi.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiObj.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiCollection.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiCollectionData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MCRecoDriftChamberDigiAssociationData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MCRecoDriftChamberDigiAssociation.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MutableMCRecoDriftChamberDigiAssociation.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MCRecoDriftChamberDigiAssociationObj.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MCRecoDriftChamberDigiAssociationCollection.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MCRecoDriftChamberDigiAssociationCollectionData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiV2Data.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiV2.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MutableDriftChamberDigiV2.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiV2Obj.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiV2Collection.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DriftChamberDigiV2CollectionData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MCRecoDriftChamberDigiV2AssociationData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MCRecoDriftChamberDigiV2Association.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MutableMCRecoDriftChamberDigiV2Association.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MCRecoDriftChamberDigiV2AssociationObj.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MCRecoDriftChamberDigiV2AssociationCollection.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MCRecoDriftChamberDigiV2AssociationCollectionData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/TrackData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/Track.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MutableTrack.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/TrackObj.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/TrackCollection.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/TrackCollectionData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/SenseWireHitData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/SenseWireHit.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MutableSenseWireHit.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/SenseWireHitObj.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/SenseWireHitCollection.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/SenseWireHitCollectionData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/SenseWireHitSimTrackerHitLinkData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/SenseWireHitSimTrackerHitLink.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/MutableSenseWireHitSimTrackerHitLink.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/SenseWireHitSimTrackerHitLinkObj.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/SenseWireHitSimTrackerHitLinkCollection.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/SenseWireHitSimTrackerHitLinkCollectionData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/TrackerHit.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/TrackerHit_dev.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/DatamodelDefinition.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extension/extension.h"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextensionDict.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextensionDict.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextensionDict.so"
         RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE SHARED_LIBRARY FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/libextensionDict.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextensionDict.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextensionDict.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextensionDict.so"
         OLD_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/.plugins:/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:"
         NEW_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libextensionDict.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/extensionDictDict.rootmap")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/extension/driftChamberHit.yaml")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/extension" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/DCHdigi/dataFormatExtension/driftChamberHit.yaml")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/libextensionDict_rdict.pcm")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so"
         RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gsl/2.8-tphaa5/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/delphes/2dcc5a41ceebfea467ec3f7cb4295c117f2a1388_develop-3jt55n/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE MODULE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/libDCHdigi.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so"
         OLD_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/.plugins:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gsl/2.8-tphaa5/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/delphes/2dcc5a41ceebfea467ec3f7cb4295c117f2a1388_develop-3jt55n/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib:"
         NEW_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gsl/2.8-tphaa5/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/delphes/2dcc5a41ceebfea467ec3f7cb4295c117f2a1388_develop-3jt55n/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi.components")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/python/DCHdigi" TYPE FILE FILES
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/genConfDir/DCHdigi/DCHdigiConf.py"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/genConfDir/DCHdigi/__init__.py"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi.confdb")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi.confdb2")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so"
         RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gsl/2.8-tphaa5/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/delphes/2dcc5a41ceebfea467ec3f7cb4295c117f2a1388_develop-3jt55n/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE MODULE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/libDCHdigi.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so"
         OLD_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/.plugins:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gsl/2.8-tphaa5/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/delphes/2dcc5a41ceebfea467ec3f7cb4295c117f2a1388_develop-3jt55n/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib:"
         NEW_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/a56d9f63caec4c8c036ec6cc53107973701af7c0_develop-2bvzew/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/16a675dacf8711220768c096f6cb8e2f9e473698_develop-d7koo2/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gsl/2.8-tphaa5/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/delphes/2dcc5a41ceebfea467ec3f7cb4295c117f2a1388_develop-3jt55n/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/podio/6bd80b0d94fe8fb1da4dab9999fd2d4411f7f8dd_develop-owl64a/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/0964912cd4b79b5458ba0e51e443255fc9bbb1a5_develop-gkayi5/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libDCHdigi.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/k4RecTracker" TYPE FILE FILES
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/DCHdigi/include/AlgData.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/DCHdigi/include/DCHdigi_v01.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/DCHdigi/include/DCHsimpleDigitizer.h"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/DCHdigi/include/DCHsimpleDigitizerExtendedEdm.h"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/test" TYPE FILE FILES
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/DCHdigi/test/runDCHsimpleDigitizer.py"
    "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/DCHdigi/test/runDCHsimpleDigitizerExtendedEdm.py"
    )
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/build/DCHdigi/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
