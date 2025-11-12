# This file is configured by CMake automatically as DartConfiguration.tcl
# If you choose not to use CMake, this file may be hand configured, by
# filling in the required variables.


# Configuration directories and files
SourceDirectory: /afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker
BuildDirectory: /afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker/build

# Where to place the cost data store
CostDataFile: 

# Site is something like machine.domain, i.e. pragmatic.crd
Site: lxplus944.cern.ch

# Build name is osname-revision-compiler, i.e. Linux-2.4.2-2smp-c++
BuildName: Linux-g++

# Subprojects
LabelsForSubprojects: 

# Submission information
SubmitURL: http://
SubmitInactivityTimeout: 

# Dashboard start time
NightlyStartTime: 00:00:00 EDT

# Commands for the build/test/submit cycle
ConfigureCommand: "/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/cmake/3.31.8-36nqaa/bin/cmake" "/afs/cern.ch/user/c/cglenn/FCCWork/GGTF_tracking/k4RecTracker"
MakeCommand: /cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/cmake/3.31.8-36nqaa/bin/cmake --build . --config "${CTEST_CONFIGURATION_TYPE}"
DefaultCTestConfigurationType: Release

# version control
UpdateVersionOnly: 

# CVS options
# Default is "-d -P -A"
CVSCommand: 
CVSUpdateOptions: 

# Subversion options
SVNCommand: 
SVNOptions: 
SVNUpdateOptions: 

# Git options
GITCommand: /cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/git/2.48.1-3t2qod/bin/git
GITInitSubmodules: 
GITUpdateOptions: 
GITUpdateCustom: 

# Perforce options
P4Command: 
P4Client: 
P4Options: 
P4UpdateOptions: 
P4UpdateCustom: 

# Generic update command
UpdateCommand: /cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/git/2.48.1-3t2qod/bin/git
UpdateOptions: 
UpdateType: git

# Compiler info
Compiler: /cvmfs/sw.hsf.org/contrib/x86_64-almalinux9-gcc11.4.1-opt/gcc/14.2.0-yuyjov/bin/g++
CompilerVersion: 14.2.0

# Dynamic analysis (MemCheck)
PurifyCommand: 
ValgrindCommand: 
ValgrindCommandOptions: 
DrMemoryCommand: 
DrMemoryCommandOptions: 
CudaSanitizerCommand: 
CudaSanitizerCommandOptions: 
MemoryCheckType: 
MemoryCheckSanitizerOptions: 
MemoryCheckCommand: /cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-09-21/x86_64-almalinux9-gcc14.2.0-opt/valgrind/3.25.1-iz25gj/bin/valgrind
MemoryCheckCommandOptions: 
MemoryCheckSuppressionFile: 

# Coverage
CoverageCommand: /cvmfs/sw.hsf.org/contrib/x86_64-almalinux9-gcc11.4.1-opt/gcc/14.2.0-yuyjov/bin/gcov
CoverageExtraFlags: -l

# Testing options
# TimeOut is the amount of time in seconds to wait for processes
# to complete during testing.  After TimeOut seconds, the
# process will be summarily terminated.
# Currently set to 25 minutes
TimeOut: 1500

# During parallel testing CTest will not start a new test if doing
# so would cause the system load to exceed this value.
TestLoad: 

TLSVerify: 
TLSVersion: 

UseLaunchers: 
CurlOptions: 
# warning, if you add new options here that have to do with submit,
# you have to update cmCTestSubmitCommand.cxx

# For CTest submissions that timeout, these options
# specify behavior for retrying the submission
CTestSubmitRetryDelay: 5
CTestSubmitRetryCount: 3
