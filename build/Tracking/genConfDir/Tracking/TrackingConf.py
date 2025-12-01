#Fri Nov 21 17:28:11 2025"""Automatically generated. DO NOT EDIT please"""
from GaudiKernel.DataHandle import DataHandle
from GaudiKernel.Proxy.Configurable import *

class GGTF_tracking( ConfigurableAlgorithm ) :
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
    'inputPlanarHits' : [ 'inputPlanarHits' ],
    'inputWireHits' : [ 'inputWireHits' ],
    'outputTracks' : [ 'outputTracks' ],
    'output3DHits' : [ 'GGTF_3DHits' ],
    'modelPath' : '',
    'tbeta' : 0.60000000,
    'td' : 0.30000000,
    'produce3DHits' : True,
    'GeoSvcName' : 'GeoSvc',
    'DCH_name' : 'DCH_v2',
    'maxHitsPerEvent' : 0,
    'onnxChunk' : 4096,
    'wireGateMM' : 3.0000000,
    'max3DHitsPerEvent' : 100000,
    'max3DPerTrack' : 10000,
    'propagateScalars' : True,
    'defaultSigmaXYMM' : 0.10000000,
    'defaultSigmaZMM' : 1.0000000,
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
    'inputPlanarHits' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::TrackCollection,edm4hep::TrackerHit3DCollection> (std::vector<edm4hep::TrackerHitPlaneCollection const*,std::allocator<edm4hep::TrackerHitPlaneCollection const*> > const&,std::vector<extension::SenseWireHitCollection const*,std::allocator<extension::SenseWireHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'inputWireHits' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::TrackCollection,edm4hep::TrackerHit3DCollection> (std::vector<edm4hep::TrackerHitPlaneCollection const*,std::allocator<edm4hep::TrackerHitPlaneCollection const*> > const&,std::vector<extension::SenseWireHitCollection const*,std::allocator<extension::SenseWireHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'outputTracks' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::TrackCollection,edm4hep::TrackerHit3DCollection> (std::vector<edm4hep::TrackerHitPlaneCollection const*,std::allocator<edm4hep::TrackerHitPlaneCollection const*> > const&,std::vector<extension::SenseWireHitCollection const*,std::allocator<extension::SenseWireHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'output3DHits' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::TrackCollection,edm4hep::TrackerHit3DCollection> (std::vector<edm4hep::TrackerHitPlaneCollection const*,std::allocator<edm4hep::TrackerHitPlaneCollection const*> > const&,std::vector<extension::SenseWireHitCollection const*,std::allocator<extension::SenseWireHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'modelPath' : """ Path to ONNX model [GGTF_tracking] """,
    'tbeta' : """ clustering beta threshold [GGTF_tracking] """,
    'td' : """ clustering distance threshold [GGTF_tracking] """,
    'produce3DHits' : """ If false, do not create GGTF_3DHits (returns empty collection) [GGTF_tracking] """,
    'GeoSvcName' : """ GeoSvc instance name [GGTF_tracking] """,
    'DCH_name' : """ Drift chamber name [GGTF_tracking] """,
    'maxHitsPerEvent' : """ If >0, hard-limit number of input hits per event (prevents OOM) [GGTF_tracking] """,
    'onnxChunk' : """ Chunk size for ONNX inference (nHits per slice) [GGTF_tracking] """,
    'wireGateMM' : """ XY residual gate for wire projection (mm) [GGTF_tracking] """,
    'max3DHitsPerEvent' : """ Hard cap on number of 3D hits created per event [GGTF_tracking] """,
    'max3DPerTrack' : """ Hard cap on number of 3D hits created per track [GGTF_tracking] """,
    'propagateScalars' : """ Copy cellID/time/quality/EDep/EDepError into 3D hits [GGTF_tracking] """,
    'defaultSigmaXYMM' : """ Fallback σX/Y [mm] for planar (and wires without error) [GGTF_tracking] """,
    'defaultSigmaZMM' : """ Fallback σZ [mm] for planar (and wires without error) [GGTF_tracking] """,
  }
  __declaration_location__ = 'GGTF_tracking.cpp:573'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(GGTF_tracking, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'Tracking'
  def getType( self ):
      return 'GGTF_tracking'
  pass # class GGTF_tracking

class GenFit2DCHFitter( ConfigurableAlgorithm ) :
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
    'inputHits' : [ 'GGTF_3DHits' ],
    'outputTracks' : [ 'GenFitTracks' ],
    'Bz' : 2.0000000,
    'PDG' : 13,
    'UseMaterialEffects' : True,
    'PositionUnitScale' : 0.10000000,
    'InternalLengthToMeters' : 0.010000000,
    'HitSigmaXYMM' : 0.50000000,
    'HitSigmaZMM' : 2.0000000,
    'SeedPosSigmaMM' : 80.000000,
    'SeedMomSigmaGeV' : 5.0000000,
    'SeedPTMinGeV' : 0.20000000,
    'SeedPTMaxGeV' : 200.00000,
    'SeedPMinGeV' : 0.80000000,
    'SortHits' : True,
    'DeduplicateHits' : True,
    'DedupTolMM' : 0.25000000,
    'MinGroupSize' : 6,
    'UseFallbackClustering' : True,
    'FallbackEpsCM' : 2.0000000,
    'FallbackMinPts' : 6,
    'RetryIfNoFitterInfo' : True,
    'RetryMeasInfl' : 4.0000000,
    'RetrySeedPosInfl' : 3.0000000,
    'RetrySeedMomInfl' : 3.0000000,
    'MaxMeasPerGroup' : 0,
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
    'inputHits' : """  [k4FWCore::details::Transformer<edm4hep::TrackCollection (edm4hep::TrackerHit3DCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'outputTracks' : """  [k4FWCore::details::Transformer<edm4hep::TrackCollection (edm4hep::TrackerHit3DCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'Bz' : """ Bz field [T] [GenFit2DCHFitter] """,
    'PDG' : """ PDG hypothesis [GenFit2DCHFitter] """,
    'UseMaterialEffects' : """ Use TGeoMaterialInterface for GenFit MaterialEffects [GenFit2DCHFitter] """,
    'PositionUnitScale' : """ Multiply positions (0.1: mm->cm) [GenFit2DCHFitter] """,
    'InternalLengthToMeters' : """ Length to meters (0.01: cm->m) [GenFit2DCHFitter] """,
    'HitSigmaXYMM' : """ XY sigma [mm] [GenFit2DCHFitter] """,
    'HitSigmaZMM' : """ Z  sigma [mm] [GenFit2DCHFitter] """,
    'SeedPosSigmaMM' : """ Seed pos sigma [mm] [GenFit2DCHFitter] """,
    'SeedMomSigmaGeV' : """ Seed mom sigma [GeV] [GenFit2DCHFitter] """,
    'SeedPTMinGeV' : """ Min pT [GeV] [GenFit2DCHFitter] """,
    'SeedPTMaxGeV' : """ Max pT [GeV] [GenFit2DCHFitter] """,
    'SeedPMinGeV' : """ Min |p| [GeV] [GenFit2DCHFitter] """,
    'SortHits' : """ Sort hits along seed direction [GenFit2DCHFitter] """,
    'DeduplicateHits' : """ Drop nearly-identical hits [GenFit2DCHFitter] """,
    'DedupTolMM' : """ Dedup tol [mm] [GenFit2DCHFitter] """,
    'MinGroupSize' : """ Minimum hits per group [GenFit2DCHFitter] """,
    'UseFallbackClustering' : """ Enable DBSCAN fallback [GenFit2DCHFitter] """,
    'FallbackEpsCM' : """ DBSCAN epsilon in cm [GenFit2DCHFitter] """,
    'FallbackMinPts' : """ DBSCAN minPts [GenFit2DCHFitter] """,
    'RetryIfNoFitterInfo' : """ Retry if no FitterInfo [GenFit2DCHFitter] """,
    'RetryMeasInfl' : """ Measurement variance inflation factor [GenFit2DCHFitter] """,
    'RetrySeedPosInfl' : """ Seed position sigma inflation factor [GenFit2DCHFitter] """,
    'RetrySeedMomInfl' : """ Seed momentum sigma inflation factor [GenFit2DCHFitter] """,
    'MaxMeasPerGroup' : """ If >0, downsample measurements per group [GenFit2DCHFitter] """,
  }
  __declaration_location__ = 'GenFit2DCHFitter.cpp:616'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(GenFit2DCHFitter, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'Tracking'
  def getType( self ):
      return 'GenFit2DCHFitter'
  pass # class GenFit2DCHFitter

class GenFitter( ConfigurableAlgorithm ) :
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
    'inputHits' : DataHandle('inputHits', 'R', 'DataWrapper<edm4hep::TrackerHit3DCollection>'),
    'outputTracks' : DataHandle('outputTracks', 'W', 'DataWrapper<edm4hep::TrackCollection>'),
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
    'inputHits' : """ Input tracker hit collection name [unknown owner type] """,
    'outputTracks' : """ Output track collection name [unknown owner type] """,
  }
  __declaration_location__ = 'GenFitter.cpp:3'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(GenFitter, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'Tracking'
  def getType( self ):
      return 'GenFitter'
  pass # class GenFitter

class PlotTrackHitDistances( ConfigurableAlgorithm ) :
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
    'InputSimTrackerHits' : [ 'DCHCollection' ],
    'InputTracksFromGenParticlesAssociation' : [ 'TracksFromGenParticlesAssociation' ],
    'Bz' : 2.00000,
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
    'InputSimTrackerHits' : """  [k4FWCore::details::Consumer<void (edm4hep::SimTrackerHitCollection const&,podio::LinkCollection<edm4hep::Track,edm4hep::MCParticle> const&),Gaudi::Functional::Traits::use_<> >] """,
    'InputTracksFromGenParticlesAssociation' : """  [k4FWCore::details::Consumer<void (edm4hep::SimTrackerHitCollection const&,podio::LinkCollection<edm4hep::Track,edm4hep::MCParticle> const&),Gaudi::Functional::Traits::use_<> >] """,
    'Bz' : """ Z component of the (assumed constant) magnetic field in Tesla. [PlotTrackHitDistances] """,
  }
  __declaration_location__ = 'PlotTrackHitResiduals.cpp:93'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(PlotTrackHitDistances, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'Tracking'
  def getType( self ):
      return 'PlotTrackHitDistances'
  pass # class PlotTrackHitDistances

class SimpleFitDCHFitter( ConfigurableAlgorithm ) :
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
    'inputHits' : [ 'GGTF_3DHits' ],
    'outputTracks' : [ 'SimpleTracks' ],
    'Bz' : 2.0000000,
    'PDG' : 13,
    'MinGroupSize' : 6,
    'DBSCAN_EpsMM' : 20.000000,
    'DBSCAN_MinPts' : 6,
    'DeduplicateHits' : True,
    'DedupTolMM' : 0.25000000,
    'HistStream' : 'simple',
    'MaxEventsY' : 2000,
    'PtBins' : 100,
    'PtMax' : 100.00000,
    'EtaMax' : 3.0000000,
    'UseMaterialEffects' : False,
    'UseTGeoPath' : True,
    'FallbackXOverX0' : 0.020000000,
    'MS_K_GeV' : 0.013600000,
    'MS_Scale' : 1.0000000,
    'BaseVar_d0' : 1.00000,
    'BaseVar_phi' : 0.00100000,
    'BaseVar_omega' : 1.00000e-08,
    'BaseVar_z0' : 1.00000,
    'BaseVar_tanLambda' : 0.0100000,
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
    'inputHits' : """  [k4FWCore::details::Transformer<edm4hep::TrackCollection (edm4hep::TrackerHit3DCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'outputTracks' : """  [k4FWCore::details::Transformer<edm4hep::TrackCollection (edm4hep::TrackerHit3DCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'Bz' : """ Uniform Bz [T] (for pT conversion/logging) [SimpleFitDCHFitter] """,
    'PDG' : """ PDG hypothesis (charge sign) [SimpleFitDCHFitter] """,
    'MinGroupSize' : """ Minimum hits per cluster to fit [SimpleFitDCHFitter] """,
    'DBSCAN_EpsMM' : """ DBSCAN epsilon [mm] [SimpleFitDCHFitter] """,
    'DBSCAN_MinPts' : """ DBSCAN minPts [SimpleFitDCHFitter] """,
    'DeduplicateHits' : """ Drop consecutive near-duplicates [SimpleFitDCHFitter] """,
    'DedupTolMM' : """ Dedup tolerance [mm] [SimpleFitDCHFitter] """,
    'HistStream' : """ THistSvc stream (file logical name) [SimpleFitDCHFitter] """,
    'MaxEventsY' : """ Y span for 2D 'vs event' plots [SimpleFitDCHFitter] """,
    'PtBins' : """ pT bins [SimpleFitDCHFitter] """,
    'PtMax' : """ pT max [GeV] [SimpleFitDCHFitter] """,
    'EtaMax' : """ |eta| max [SimpleFitDCHFitter] """,
    'UseMaterialEffects' : """ If true, estimate X/X0 per cluster and inflate covariances [SimpleFitDCHFitter] """,
    'UseTGeoPath' : """ If true and gGeoManager present, estimate X/X0 via TGeo midpoints [SimpleFitDCHFitter] """,
    'FallbackXOverX0' : """ Fallback integrated material (X/X0) if TGeo not available [SimpleFitDCHFitter] """,
    'MS_K_GeV' : """ Highland constant (13.6 MeV) in GeV [SimpleFitDCHFitter] """,
    'MS_Scale' : """ Extra scale factor on MS variance additions [SimpleFitDCHFitter] """,
    'BaseVar_d0' : """ base var(d0) [mm^2] [SimpleFitDCHFitter] """,
    'BaseVar_phi' : """ base var(phi) [rad^2] [SimpleFitDCHFitter] """,
    'BaseVar_omega' : """ base var(omega) [(GeV^-1)^2] (placeholder) [SimpleFitDCHFitter] """,
    'BaseVar_z0' : """ base var(z0) [mm^2] [SimpleFitDCHFitter] """,
    'BaseVar_tanLambda' : """ base var(tanLambda) [1] [SimpleFitDCHFitter] """,
  }
  __declaration_location__ = 'SimpleFitDCHFitter.cpp:464'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(SimpleFitDCHFitter, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'Tracking'
  def getType( self ):
      return 'SimpleFitDCHFitter'
  pass # class SimpleFitDCHFitter

class ThreePointFitter( ConfigurableAlgorithm ) :
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
    'inputHits' : [ 'GGTF_3DHits' ],
    'outputTracks' : [ 'ThreePointTracks' ],
    'Bz' : 2.0000000,
    'PDG' : 13,
    'MinHitsPerGroup' : 3,
    'MinChordMM' : 5.0000000,
    'MinRadiusMM' : 100.00000,
    'MinDeltaPhi' : 0.10000000,
    'FitTanLambda' : True,
    'PrintDiagnostics' : True,
    'DiagEveryN' : 1,
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
    'inputHits' : """  [k4FWCore::details::Transformer<edm4hep::TrackCollection (edm4hep::TrackerHit3DCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'outputTracks' : """  [k4FWCore::details::Transformer<edm4hep::TrackCollection (edm4hep::TrackerHit3DCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'Bz' : """ Uniform B [Tesla] for pT conversion [ThreePointFitter] """,
    'PDG' : """ PDG hypothesis (charge sign only) [ThreePointFitter] """,
    'MinHitsPerGroup' : """ Minimum hits per GGTF label to fit [ThreePointFitter] """,
    'MinChordMM' : """ Min chord length among the 3 picked points [mm] [ThreePointFitter] """,
    'MinRadiusMM' : """ Reject tiny circles R < this [mm] [ThreePointFitter] """,
    'MinDeltaPhi' : """ Require φ_max-φ_min >= this [rad] (about origin) [ThreePointFitter] """,
    'FitTanLambda' : """ Estimate tanLambda from z(phi) linear fit [ThreePointFitter] """,
    'PrintDiagnostics' : """ Print per-track geometry diagnostics [ThreePointFitter] """,
    'DiagEveryN' : """ Print every N-th track (per event grouping) [ThreePointFitter] """,
  }
  __declaration_location__ = 'ThreePointFitter.cpp:300'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(ThreePointFitter, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'Tracking'
  def getType( self ):
      return 'ThreePointFitter'
  pass # class ThreePointFitter

class TrackdNdxDelphesBased( ConfigurableAlgorithm ) :
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
    'InputLinkCollection' : [ 'TrackMCParticleLinks' ],
    'HeaderName' : [ 'EventHeader' ],
    'OutputCollection' : [ 'RecDqdxCollection' ],
    'ZmaxParameterName' : 'DCH_gas_Lhalf',
    'ZminParameterName' : 'DCH_gas_Lhalf',
    'RminParameterName' : 'DCH_gas_inner_cyl_R',
    'RmaxParameterName' : 'DCH_gas_outer_cyl_R',
    'GasSel' : 0,
    'FillFactor' : 1.0000000,
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
    'InputLinkCollection' : """  [k4FWCore::details::Transformer<edm4hep::RecDqdxCollection (podio::LinkCollection<edm4hep::Track,edm4hep::MCParticle> const&,edm4hep::EventHeaderCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'HeaderName' : """  [k4FWCore::details::Transformer<edm4hep::RecDqdxCollection (podio::LinkCollection<edm4hep::Track,edm4hep::MCParticle> const&,edm4hep::EventHeaderCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'OutputCollection' : """  [k4FWCore::details::Transformer<edm4hep::RecDqdxCollection (podio::LinkCollection<edm4hep::Track,edm4hep::MCParticle> const&,edm4hep::EventHeaderCollection const&),Gaudi::Functional::Traits::use_<> >] """,
    'ZmaxParameterName' : """ Name of XML file parameter describing the z extent of the active volume (max value in +z direction) [TrackdNdxDelphesBased] """,
    'ZminParameterName' : """ Name of XML file parameter describing the z extent of the active volume (min value in -z direction). For forward-backward symmetric detectors, use same name as for ZmaxParameterName. This value is then automatically converted into the negative value. [TrackdNdxDelphesBased] """,
    'RminParameterName' : """ Name of XML file parameter describing the inner radius of the active volume. [TrackdNdxDelphesBased] """,
    'RmaxParameterName' : """ Name of XML file parameter describing the outer radius of the active volume. [TrackdNdxDelphesBased] """,
    'GasSel' : """ Gas selection: 0: He(90%)-Isobutane(10%), 1: pure He, 2: Ar(50%)-Ethane(50%), 3: pure Ar. [TrackdNdxDelphesBased] """,
    'FillFactor' : """ Factor (between 0 and 1) describing the fraction of the detector volume that is active (e.g., for Straw Tube Tracker the factor is significantly below 1 due to gaps between tubes). The factor is used to scale the calculated track length and thus the corresponding number of clusters. [TrackdNdxDelphesBased] """,
  }
  __declaration_location__ = 'TrackdNdxDelphesBased.cpp:21'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(TrackdNdxDelphesBased, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'Tracking'
  def getType( self ):
      return 'TrackdNdxDelphesBased'
  pass # class TrackdNdxDelphesBased

class TracksFromGenParticles( ConfigurableAlgorithm ) :
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
    'InputGenParticles' : [ 'MCParticles' ],
    'InputSimTrackerHits' : [ 'SimTrackerHits' ],
    'OutputTracks' : [ 'TracksFromGenParticles' ],
    'OutputMCRecoTrackParticleAssociation' : [ 'TracksFromGenParticlesAssociation' ],
    'ExtrapolateToECal' : False,
    'KeepOnlyBestExtrapolation' : True,
    'MinimumParticleMomentum' : 0.0100000,
    'TrackerIDs' : [  ],
    'SystemEncoding' : 'system:5',
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
    'InputGenParticles' : """  [k4FWCore::details::MultiTransformer<std::tuple<edm4hep::TrackCollection,podio::LinkCollection<edm4hep::Track,edm4hep::MCParticle> > (edm4hep::MCParticleCollection const&,std::vector<edm4hep::SimTrackerHitCollection const*,std::allocator<edm4hep::SimTrackerHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'InputSimTrackerHits' : """  [k4FWCore::details::MultiTransformer<std::tuple<edm4hep::TrackCollection,podio::LinkCollection<edm4hep::Track,edm4hep::MCParticle> > (edm4hep::MCParticleCollection const&,std::vector<edm4hep::SimTrackerHitCollection const*,std::allocator<edm4hep::SimTrackerHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'OutputTracks' : """  [k4FWCore::details::MultiTransformer<std::tuple<edm4hep::TrackCollection,podio::LinkCollection<edm4hep::Track,edm4hep::MCParticle> > (edm4hep::MCParticleCollection const&,std::vector<edm4hep::SimTrackerHitCollection const*,std::allocator<edm4hep::SimTrackerHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'OutputMCRecoTrackParticleAssociation' : """  [k4FWCore::details::MultiTransformer<std::tuple<edm4hep::TrackCollection,podio::LinkCollection<edm4hep::Track,edm4hep::MCParticle> > (edm4hep::MCParticleCollection const&,std::vector<edm4hep::SimTrackerHitCollection const*,std::allocator<edm4hep::SimTrackerHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'ExtrapolateToECal' : """ Calculate track state at ECal inner face or not [TracksFromGenParticles] """,
    'KeepOnlyBestExtrapolation' : """ Keep only extrapolation with shortest time or not [TracksFromGenParticles] """,
    'MinimumParticleMomentum' : """ Keep only particles with momentum (in GeV) greater than MinimumParticleMomentum [TracksFromGenParticles] """,
    'TrackerIDs' : """ System IDs of tracking subdetectors [TracksFromGenParticles] """,
    'SystemEncoding' : """ System encoding string [TracksFromGenParticles] """,
  }
  __declaration_location__ = 'TracksFromGenParticles.cpp:453'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(TracksFromGenParticles, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'Tracking'
  def getType( self ):
      return 'TracksFromGenParticles'
  pass # class TracksFromGenParticles
