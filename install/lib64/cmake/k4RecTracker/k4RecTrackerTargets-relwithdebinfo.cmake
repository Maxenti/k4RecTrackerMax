#----------------------------------------------------------------
# Generated CMake target import file for configuration "RelWithDebInfo".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "k4RecTracker::DCHdigi" for configuration "RelWithDebInfo"
set_property(TARGET k4RecTracker::DCHdigi APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
set_target_properties(k4RecTracker::DCHdigi PROPERTIES
  IMPORTED_COMMON_LANGUAGE_RUNTIME_RELWITHDEBINFO ""
  IMPORTED_LOCATION_RELWITHDEBINFO "${_IMPORT_PREFIX}/lib64/libDCHdigi.so"
  IMPORTED_NO_SONAME_RELWITHDEBINFO "TRUE"
  )

list(APPEND _cmake_import_check_targets k4RecTracker::DCHdigi )
list(APPEND _cmake_import_check_files_for_k4RecTracker::DCHdigi "${_IMPORT_PREFIX}/lib64/libDCHdigi.so" )

# Import target "k4RecTracker::ARCdigi" for configuration "RelWithDebInfo"
set_property(TARGET k4RecTracker::ARCdigi APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
set_target_properties(k4RecTracker::ARCdigi PROPERTIES
  IMPORTED_COMMON_LANGUAGE_RUNTIME_RELWITHDEBINFO ""
  IMPORTED_LOCATION_RELWITHDEBINFO "${_IMPORT_PREFIX}/lib64/libARCdigi.so"
  IMPORTED_NO_SONAME_RELWITHDEBINFO "TRUE"
  )

list(APPEND _cmake_import_check_targets k4RecTracker::ARCdigi )
list(APPEND _cmake_import_check_files_for_k4RecTracker::ARCdigi "${_IMPORT_PREFIX}/lib64/libARCdigi.so" )

# Import target "k4RecTracker::VTXdigi" for configuration "RelWithDebInfo"
set_property(TARGET k4RecTracker::VTXdigi APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
set_target_properties(k4RecTracker::VTXdigi PROPERTIES
  IMPORTED_COMMON_LANGUAGE_RUNTIME_RELWITHDEBINFO ""
  IMPORTED_LOCATION_RELWITHDEBINFO "${_IMPORT_PREFIX}/lib64/libVTXdigi.so"
  IMPORTED_NO_SONAME_RELWITHDEBINFO "TRUE"
  )

list(APPEND _cmake_import_check_targets k4RecTracker::VTXdigi )
list(APPEND _cmake_import_check_files_for_k4RecTracker::VTXdigi "${_IMPORT_PREFIX}/lib64/libVTXdigi.so" )

# Import target "k4RecTracker::Tracking" for configuration "RelWithDebInfo"
set_property(TARGET k4RecTracker::Tracking APPEND PROPERTY IMPORTED_CONFIGURATIONS RELWITHDEBINFO)
set_target_properties(k4RecTracker::Tracking PROPERTIES
  IMPORTED_COMMON_LANGUAGE_RUNTIME_RELWITHDEBINFO ""
  IMPORTED_LOCATION_RELWITHDEBINFO "${_IMPORT_PREFIX}/lib64/libTracking.so"
  IMPORTED_NO_SONAME_RELWITHDEBINFO "TRUE"
  )

list(APPEND _cmake_import_check_targets k4RecTracker::Tracking )
list(APPEND _cmake_import_check_files_for_k4RecTracker::Tracking "${_IMPORT_PREFIX}/lib64/libTracking.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
