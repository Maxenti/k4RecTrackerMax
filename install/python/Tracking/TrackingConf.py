#Wed Nov 12 20:19:12 2025"""Automatically generated. DO NOT EDIT please"""
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
    'InputPlanarHitCollections' : [ 'InputPlanarHitCollections' ],
    'InputWireHitCollections' : [ 'InputWireHitCollections' ],
    'OutputTracksGGTF' : [ 'OutputTracksGGTF' ],
    'ModelPath' : '',
    'Tbeta' : 0.60000000,
    'Td' : 0.30000000,
    'GeoSvcName' : 'GeoSvc',
    'UidSvcName' : 'uidSvc',
    'DchName' : 'DCH_v2',
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
    'InputPlanarHitCollections' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::TrackCollection> (std::vector<edm4hep::TrackerHitPlaneCollection const*,std::allocator<edm4hep::TrackerHitPlaneCollection const*> > const&,std::vector<extension::SenseWireHitCollection const*,std::allocator<extension::SenseWireHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'InputWireHitCollections' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::TrackCollection> (std::vector<edm4hep::TrackerHitPlaneCollection const*,std::allocator<edm4hep::TrackerHitPlaneCollection const*> > const&,std::vector<extension::SenseWireHitCollection const*,std::allocator<extension::SenseWireHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'OutputTracksGGTF' : """  [k4FWCore::details::MultiTransformer<std::tuple<extension::TrackCollection> (std::vector<edm4hep::TrackerHitPlaneCollection const*,std::allocator<edm4hep::TrackerHitPlaneCollection const*> > const&,std::vector<extension::SenseWireHitCollection const*,std::allocator<extension::SenseWireHitCollection const*> > const&),Gaudi::Functional::Traits::use_<> >] """,
    'ModelPath' : """ ModelPath [GGTF_tracking] """,
    'Tbeta' : """ tbeta [GGTF_tracking] """,
    'Td' : """ td [GGTF_tracking] """,
    'GeoSvcName' : """ The name of the GeoSvc instance [GGTF_tracking] """,
    'UidSvcName' : """ The name of the UniqueIDGenSvc instance [GGTF_tracking] """,
    'DchName' : """ Name of the Drift Chamber detector [GGTF_tracking] """,
  }
  __declaration_location__ = 'GGTF_tracking.cpp:501'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(GGTF_tracking, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'Tracking'
  def getType( self ):
      return 'GGTF_tracking'
  pass # class GGTF_tracking

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
