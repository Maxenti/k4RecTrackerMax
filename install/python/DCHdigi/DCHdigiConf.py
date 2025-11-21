#Mon Nov 17 21:55:39 2025"""Automatically generated. DO NOT EDIT please"""
from GaudiKernel.DataHandle import DataHandle
from GaudiKernel.Proxy.Configurable import *

class DCHdigi_v01( ConfigurableAlgorithm ) :
  __slots__ = { 
    'ExtraInputs' : set(),
    'ExtraOutputs' : set(),
    'OutputLevel' : 0,
    'Enable' : True,
    'ErrorMax' : 1,
    'AuditInitialize' : False,
    'AuditReinitialize' : False,
    'AuditRestart' : False,
    'AuditExecute' : False,
    'AuditFinalize' : False,
    'AuditStart' : False,
    'AuditStop' : False,
    'Timeline' : True,
    'MonitorService' : 'MonitorSvc',
    'RegisterForContextService' : False,
    'Cardinality' : 0,
    'NeededResources' : [  ],
    'Asynchronous' : False,
    'FilterCircularDependencies' : True,
    'DCH_simhits' : [ '' ],
    'HeaderName' : [ 'EventHeader' ],
    'DCH_DigiCollection' : [ 'DCH_DigiCollection' ],
    'DCH_DigiSimAssociationCollection' : [ 'DCH_DigiSimAssociationCollection' ],
    'GeoSvcName' : 'GeoSvc',
    'uidSvcName' : 'uidSvc',
    'DCH_name' : 'DCH_v2',
    'zResolution_mm' : 1.00000,
    'xyResolution_mm' : 0.100000,
    'calculate_dndx' : False,
    'fileDataAlg' : '/eos/project/f/fccsw-web/www/filesForSimDigiReco/IDEA/DataAlgFORGEANT.root',
    'create_debug_histograms' : False,
    'out_debug_filename' : 'dch_digi_alg_debug.root',
  }
  _propertyDocDct = { 
    'ExtraInputs' : """  [DataHandleHolderBase<PropertyHolder<CommonMessaging<implements<IAlgorithm,IDataHandleHolder,IProperty,IStateful> > > >] """,
    'ExtraOutputs' : """  [DataHandleHolderBase<PropertyHolder<CommonMessaging<implements<IAlgorithm,IDataHandleHolder,IProperty,IStateful> > > >] """,
    'OutputLevel' : """ output level [Gaudi::Algorithm] """,
    'Enable' : """ should the algorithm be executed or not [Gaudi::Algorithm] """,
    'ErrorMax' : """ [[deprecated]] max number of errors [Gaudi::Algorithm] """,
    'AuditInitialize' : """ trigger auditor on initialize() [Gaudi::Algorithm] """,
    'AuditReinitialize' : """ trigger auditor on reinitialize() [Gaudi::Algorithm] """,
    'AuditRestart' : """ trigger auditor on restart() [Gaudi::Algorithm] """,
    'AuditExecute' : """ trigger auditor on execute() [Gaudi::Algorithm] """,
    'AuditFinalize' : """ trigger auditor on finalize() [Gaudi::Algorithm] """,
    'AuditStart' : """ trigger auditor on start() [Gaudi::Algorithm] """,
    'AuditStop' : """ trigger auditor on stop() [Gaudi::Algorithm] """,
    'Timeline' : """ send events to TimelineSvc [Gaudi::Algorithm] """,
    'MonitorService' : """ name to use for Monitor Service [Gaudi::Algorithm] """,
    'RegisterForContextService' : """ flag to enforce the registration for Algorithm Context Service [Gaudi::Algorithm] """,
    'Cardinality' : """ how many clones to create - 0 means algo is reentrant [Gaudi::Algorithm] """,
    'NeededResources' : """ named resources needed during event looping [Gaudi::Algorithm] """,
    'Asynchronous' : """ whether algorithm is asynchronous and uses Boost Fiber to suspend while offloaded code is running. [Gaudi::Algorithm] """,
    'FilterCircularDependencies' : """ filter out circular data dependencies [Gaudi::Algorithm] """,
    'DCH_simhits' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::SenseWireHitCollection,extension::SenseWireHitSimTrackerHitLinkCollection> (edm4hep::SimTrackerHitCollection const&,edm4hep::EventHeaderCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'HeaderName' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::SenseWireHitCollection,extension::SenseWireHitSimTrackerHitLinkCollection> (edm4hep::SimTrackerHitCollection const&,edm4hep::EventHeaderCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'DCH_DigiCollection' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::SenseWireHitCollection,extension::SenseWireHitSimTrackerHitLinkCollection> (edm4hep::SimTrackerHitCollection const&,edm4hep::EventHeaderCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'DCH_DigiSimAssociationCollection' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::SenseWireHitCollection,extension::SenseWireHitSimTrackerHitLinkCollection> (edm4hep::SimTrackerHitCollection const&,edm4hep::EventHeaderCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'GeoSvcName' : """ The name of the GeoSvc instance [DCHdigi_v01] """,
    'uidSvcName' : """ The name of the UniqueIDGenSvc instance [DCHdigi_v01] """,
    'DCH_name' : """ Name of the Drift Chamber detector [DCHdigi_v01] """,
    'zResolution_mm' : """ Spatial resolution in the z direction (from reading out the wires at both sides) in mm. Default 1 mm. [DCHdigi_v01] """,
    'xyResolution_mm' : """ Spatial resolution in the xy direction in mm. Default 0.1 mm. [DCHdigi_v01] """,
    'calculate_dndx' : """ Calculate number of clusters and electron per cluster [DCHdigi_v01] """,
    'fileDataAlg' : """ ROOT file with cluster size distributions [DCHdigi_v01] """,
    'create_debug_histograms' : """ Create output file with histograms for debugging [DCHdigi_v01] """,
    'out_debug_filename' : """ name for the file that will contain the histograms for debugging [DCHdigi_v01] """,
  }
  __declaration_location__ = 'DCHdigi_v01.h:202'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(DCHdigi_v01, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'DCHdigi'
  def getType( self ):
      return 'DCHdigi_v01'
  pass # class DCHdigi_v01

class DCHsimpleDigitizer( ConfigurableAlgorithm ) :
  __slots__ = { 
    'ExtraInputs' : set(),
    'ExtraOutputs' : set(),
    'OutputLevel' : 0,
    'Enable' : True,
    'ErrorMax' : 1,
    'AuditInitialize' : False,
    'AuditReinitialize' : False,
    'AuditRestart' : False,
    'AuditExecute' : False,
    'AuditFinalize' : False,
    'AuditStart' : False,
    'AuditStop' : False,
    'Timeline' : True,
    'MonitorService' : 'MonitorSvc',
    'RegisterForContextService' : False,
    'Cardinality' : 0,
    'NeededResources' : [  ],
    'Asynchronous' : False,
    'FilterCircularDependencies' : True,
    'readoutName' : 'CDCHHits',
    'zResolution' : 1.00000,
    'xyResolution' : 0.100000,
    'inputSimHits' : DataHandle('inputSimHits', 'R', 'DataWrapper<edm4hep::SimTrackerHitCollection>'),
    'outputDigiHits' : DataHandle('outputDigiHits', 'W', 'DataWrapper<edm4hep::TrackerHit3DCollection>'),
  }
  _propertyDocDct = { 
    'ExtraInputs' : """  [DataHandleHolderBase<PropertyHolder<CommonMessaging<implements<IAlgorithm,IDataHandleHolder,IProperty,IStateful> > > >] """,
    'ExtraOutputs' : """  [DataHandleHolderBase<PropertyHolder<CommonMessaging<implements<IAlgorithm,IDataHandleHolder,IProperty,IStateful> > > >] """,
    'OutputLevel' : """ output level [Gaudi::Algorithm] """,
    'Enable' : """ should the algorithm be executed or not [Gaudi::Algorithm] """,
    'ErrorMax' : """ [[deprecated]] max number of errors [Gaudi::Algorithm] """,
    'AuditInitialize' : """ trigger auditor on initialize() [Gaudi::Algorithm] """,
    'AuditReinitialize' : """ trigger auditor on reinitialize() [Gaudi::Algorithm] """,
    'AuditRestart' : """ trigger auditor on restart() [Gaudi::Algorithm] """,
    'AuditExecute' : """ trigger auditor on execute() [Gaudi::Algorithm] """,
    'AuditFinalize' : """ trigger auditor on finalize() [Gaudi::Algorithm] """,
    'AuditStart' : """ trigger auditor on start() [Gaudi::Algorithm] """,
    'AuditStop' : """ trigger auditor on stop() [Gaudi::Algorithm] """,
    'Timeline' : """ send events to TimelineSvc [Gaudi::Algorithm] """,
    'MonitorService' : """ name to use for Monitor Service [Gaudi::Algorithm] """,
    'RegisterForContextService' : """ flag to enforce the registration for Algorithm Context Service [Gaudi::Algorithm] """,
    'Cardinality' : """ how many clones to create - 0 means algo is reentrant [Gaudi::Algorithm] """,
    'NeededResources' : """ named resources needed during event looping [Gaudi::Algorithm] """,
    'Asynchronous' : """ whether algorithm is asynchronous and uses Boost Fiber to suspend while offloaded code is running. [Gaudi::Algorithm] """,
    'FilterCircularDependencies' : """ filter out circular data dependencies [Gaudi::Algorithm] """,
    'readoutName' : """ Name of the detector readout [DCHsimpleDigitizer] """,
    'zResolution' : """ Spatial resolution in the z direction (from reading out the wires at both sides) [mm] [DCHsimpleDigitizer] """,
    'xyResolution' : """ Spatial resolution in the xy direction [mm] [DCHsimpleDigitizer] """,
    'inputSimHits' : """ Input sim tracker hit collection name [unknown owner type] """,
    'outputDigiHits' : """ Output digitized tracker hit collection name [unknown owner type] """,
  }
  __declaration_location__ = 'DCHsimpleDigitizer.cpp:10'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(DCHsimpleDigitizer, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'DCHdigi'
  def getType( self ):
      return 'DCHsimpleDigitizer'
  pass # class DCHsimpleDigitizer

class DCHsimpleDigitizerExtendedEdm( ConfigurableAlgorithm ) :
  __slots__ = { 
    'ExtraInputs' : set(),
    'ExtraOutputs' : set(),
    'OutputLevel' : 0,
    'Enable' : True,
    'ErrorMax' : 1,
    'AuditInitialize' : False,
    'AuditReinitialize' : False,
    'AuditRestart' : False,
    'AuditExecute' : False,
    'AuditFinalize' : False,
    'AuditStart' : False,
    'AuditStop' : False,
    'Timeline' : True,
    'MonitorService' : 'MonitorSvc',
    'RegisterForContextService' : False,
    'Cardinality' : 0,
    'NeededResources' : [  ],
    'Asynchronous' : False,
    'FilterCircularDependencies' : True,
    'readoutName' : 'CDCHHits',
    'zResolution' : 1.00000,
    'xyResolution' : 0.100000,
    'debugMode' : False,
    'inputSimHits' : DataHandle('inputSimHits', 'R', 'DataWrapper<edm4hep::SimTrackerHitCollection>'),
    'outputDigiHits' : DataHandle('outputDigiHits', 'W', 'DataWrapper<extension::DriftChamberDigiCollection>'),
    'outputSimDigiAssociation' : DataHandle('outputSimDigiAssociation', 'W', 'DataWrapper<extension::MCRecoDriftChamberDigiAssociationCollection>'),
  }
  _propertyDocDct = { 
    'ExtraInputs' : """  [DataHandleHolderBase<PropertyHolder<CommonMessaging<implements<IAlgorithm,IDataHandleHolder,IProperty,IStateful> > > >] """,
    'ExtraOutputs' : """  [DataHandleHolderBase<PropertyHolder<CommonMessaging<implements<IAlgorithm,IDataHandleHolder,IProperty,IStateful> > > >] """,
    'OutputLevel' : """ output level [Gaudi::Algorithm] """,
    'Enable' : """ should the algorithm be executed or not [Gaudi::Algorithm] """,
    'ErrorMax' : """ [[deprecated]] max number of errors [Gaudi::Algorithm] """,
    'AuditInitialize' : """ trigger auditor on initialize() [Gaudi::Algorithm] """,
    'AuditReinitialize' : """ trigger auditor on reinitialize() [Gaudi::Algorithm] """,
    'AuditRestart' : """ trigger auditor on restart() [Gaudi::Algorithm] """,
    'AuditExecute' : """ trigger auditor on execute() [Gaudi::Algorithm] """,
    'AuditFinalize' : """ trigger auditor on finalize() [Gaudi::Algorithm] """,
    'AuditStart' : """ trigger auditor on start() [Gaudi::Algorithm] """,
    'AuditStop' : """ trigger auditor on stop() [Gaudi::Algorithm] """,
    'Timeline' : """ send events to TimelineSvc [Gaudi::Algorithm] """,
    'MonitorService' : """ name to use for Monitor Service [Gaudi::Algorithm] """,
    'RegisterForContextService' : """ flag to enforce the registration for Algorithm Context Service [Gaudi::Algorithm] """,
    'Cardinality' : """ how many clones to create - 0 means algo is reentrant [Gaudi::Algorithm] """,
    'NeededResources' : """ named resources needed during event looping [Gaudi::Algorithm] """,
    'Asynchronous' : """ whether algorithm is asynchronous and uses Boost Fiber to suspend while offloaded code is running. [Gaudi::Algorithm] """,
    'FilterCircularDependencies' : """ filter out circular data dependencies [Gaudi::Algorithm] """,
    'readoutName' : """ Name of the detector readout [DCHsimpleDigitizerExtendedEdm] """,
    'zResolution' : """ Spatial resolution in the z direction (from reading out the wires at both sides) [mm] [DCHsimpleDigitizerExtendedEdm] """,
    'xyResolution' : """ Spatial resolution in the xy direction [mm] [DCHsimpleDigitizerExtendedEdm] """,
    'debugMode' : """ Flag to produce debugging distributions [DCHsimpleDigitizerExtendedEdm] """,
    'inputSimHits' : """ Input sim tracker hit collection name [unknown owner type] """,
    'outputDigiHits' : """ Output digitized tracker hit collection name [unknown owner type] """,
    'outputSimDigiAssociation' : """ Output name for the association between digitized and simulated hit collections [unknown owner type] """,
  }
  __declaration_location__ = 'DCHsimpleDigitizerExtendedEdm.cpp:10'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(DCHsimpleDigitizerExtendedEdm, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'DCHdigi'
  def getType( self ):
      return 'DCHsimpleDigitizerExtendedEdm'
  pass # class DCHsimpleDigitizerExtendedEdm
