# Install script for directory: /afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/Tracking

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
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so"
         RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/marlinutil/71b32a8436b0635bffdfb1ad2a850097d4cf3d4c_develop-miujhi/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/ced/5796193c222d1b604158934d4172c28a4e59400a_develop-2kx2nv/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/clhep/2.4.7.1-6k4dbh/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/pandorasdk/3.4.2-xev72z/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/c79b7a8a158c72483dd5577a20177602a5ce753c_develop-t673qg/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-onnxruntime/1.21.0-szdggw/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-torch/2.8.0-anom7k/lib/python3.13/site-packages/torch/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/e369490a18a9857d5a61771f340c1791e8f9f7a3_develop-c5qfjn/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/delphes/5a60982c470a9eb0e20a24ce9d71480abc0b7947_develop-37rmcc/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/podio/ec612dee213f0e0ef3584dcd6028f8a2427577a1_develop-uizlar/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/4d2242478347716d05b86c927fa6337764a5af62_develop-pbsm2k/lib64")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE MODULE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/Tracking/libTracking.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so"
         OLD_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/.plugins:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/marlinutil/71b32a8436b0635bffdfb1ad2a850097d4cf3d4c_develop-miujhi/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/ced/5796193c222d1b604158934d4172c28a4e59400a_develop-2kx2nv/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/clhep/2.4.7.1-6k4dbh/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/pandorasdk/3.4.2-xev72z/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/c79b7a8a158c72483dd5577a20177602a5ce753c_develop-t673qg/lib:/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/DCHdigi:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-onnxruntime/1.21.0-szdggw/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-torch/2.8.0-anom7k/lib/python3.13/site-packages/torch/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/e369490a18a9857d5a61771f340c1791e8f9f7a3_develop-c5qfjn/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/delphes/5a60982c470a9eb0e20a24ce9d71480abc0b7947_develop-37rmcc/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/podio/ec612dee213f0e0ef3584dcd6028f8a2427577a1_develop-uizlar/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/4d2242478347716d05b86c927fa6337764a5af62_develop-pbsm2k/lib64:"
         NEW_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/marlinutil/71b32a8436b0635bffdfb1ad2a850097d4cf3d4c_develop-miujhi/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/ced/5796193c222d1b604158934d4172c28a4e59400a_develop-2kx2nv/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/clhep/2.4.7.1-6k4dbh/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/pandorasdk/3.4.2-xev72z/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/c79b7a8a158c72483dd5577a20177602a5ce753c_develop-t673qg/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-onnxruntime/1.21.0-szdggw/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-torch/2.8.0-anom7k/lib/python3.13/site-packages/torch/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/e369490a18a9857d5a61771f340c1791e8f9f7a3_develop-c5qfjn/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/delphes/5a60982c470a9eb0e20a24ce9d71480abc0b7947_develop-37rmcc/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/podio/ec612dee213f0e0ef3584dcd6028f8a2427577a1_develop-uizlar/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/4d2242478347716d05b86c927fa6337764a5af62_develop-pbsm2k/lib64")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/Tracking.components")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/python/Tracking" TYPE FILE FILES
    "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/Tracking/genConfDir/Tracking/TrackingConf.py"
    "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/Tracking/genConfDir/Tracking/__init__.py"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/Tracking.confdb")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/Tracking.confdb2")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so"
         RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/marlinutil/71b32a8436b0635bffdfb1ad2a850097d4cf3d4c_develop-miujhi/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/ced/5796193c222d1b604158934d4172c28a4e59400a_develop-2kx2nv/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/clhep/2.4.7.1-6k4dbh/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/pandorasdk/3.4.2-xev72z/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/c79b7a8a158c72483dd5577a20177602a5ce753c_develop-t673qg/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-onnxruntime/1.21.0-szdggw/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-torch/2.8.0-anom7k/lib/python3.13/site-packages/torch/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/e369490a18a9857d5a61771f340c1791e8f9f7a3_develop-c5qfjn/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/delphes/5a60982c470a9eb0e20a24ce9d71480abc0b7947_develop-37rmcc/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/podio/ec612dee213f0e0ef3584dcd6028f8a2427577a1_develop-uizlar/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/4d2242478347716d05b86c927fa6337764a5af62_develop-pbsm2k/lib64")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE MODULE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/Tracking/libTracking.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so"
         OLD_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/.plugins:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/marlinutil/71b32a8436b0635bffdfb1ad2a850097d4cf3d4c_develop-miujhi/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/ced/5796193c222d1b604158934d4172c28a4e59400a_develop-2kx2nv/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/clhep/2.4.7.1-6k4dbh/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/pandorasdk/3.4.2-xev72z/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/c79b7a8a158c72483dd5577a20177602a5ce753c_develop-t673qg/lib:/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/DCHdigi:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-onnxruntime/1.21.0-szdggw/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-torch/2.8.0-anom7k/lib/python3.13/site-packages/torch/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/e369490a18a9857d5a61771f340c1791e8f9f7a3_develop-c5qfjn/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/delphes/5a60982c470a9eb0e20a24ce9d71480abc0b7947_develop-37rmcc/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/podio/ec612dee213f0e0ef3584dcd6028f8a2427577a1_develop-uizlar/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/4d2242478347716d05b86c927fa6337764a5af62_develop-pbsm2k/lib64:"
         NEW_RPATH "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/install/:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/marlinutil/71b32a8436b0635bffdfb1ad2a850097d4cf3d4c_develop-miujhi/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/ced/5796193c222d1b604158934d4172c28a4e59400a_develop-2kx2nv/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/clhep/2.4.7.1-6k4dbh/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/root/6.36.04-6qfi76/lib/root:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/pandorasdk/3.4.2-xev72z/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/k4fwcore/c79b7a8a158c72483dd5577a20177602a5ce753c_develop-t673qg/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-onnxruntime/1.21.0-szdggw/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/py-torch/2.8.0-anom7k/lib/python3.13/site-packages/torch/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/dd4hep/e369490a18a9857d5a61771f340c1791e8f9f7a3_develop-c5qfjn/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/delphes/5a60982c470a9eb0e20a24ce9d71480abc0b7947_develop-37rmcc/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/xerces-c/3.3.0-qlw52o/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/gaudi/40.0-hqgvjz/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/boost/1.88.0-pfej4w/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/intel-tbb/2022.0.0-sjg44y/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/python/3.13.5-vselov/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/podio/ec612dee213f0e0ef3584dcd6028f8a2427577a1_develop-uizlar/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/vdt/0.4.6-rviadr/lib:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/sio/9368e91bb3f4a99e8286d26dc7a425f216ff97d7_develop-5awric/lib64:/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-11-12/x86_64-almalinux9-gcc14.2.0-opt/edm4hep/4d2242478347716d05b86c927fa6337764a5af62_develop-pbsm2k/lib64")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libTracking.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/k4RecTracker" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/Tracking/include/GenFitter.h")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/test" TYPE FILE FILES "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/Tracking/test/runGenFitTrackingOnSimplifiedDriftChamber.py")
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build/Tracking/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
