#Mon Nov 17 21:55:00 2025"""Automatically generated. DO NOT EDIT please"""
from GaudiKernel.DataHandle import DataHandle
from GaudiKernel.Proxy.Configurable import *

class VTXdigitizer( ConfigurableAlgorithm ) :
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
    'detectorName' : 'Vertex',
    'readoutName' : 'VertexBarrelCollection',
    'xResolution' : [ 0.100000 ],
    'yResolution' : [ 0.100000 ],
    'tResolution' : [ 0.100000 ],
    'forceHitsOntoSurface' : False,
    'inputSimHits' : DataHandle('inputSimHits', 'R', 'DataWrapper<edm4hep::SimTrackerHitCollection>'),
    'outputDigiHits' : DataHandle('outputDigiHits', 'W', 'DataWrapper<edm4hep::TrackerHit3DCollection>'),
    'outputSimDigiAssociation' : DataHandle('outputSimDigiAssociation', 'W', 'DataWrapper<podio::LinkCollection<edm4hep::TrackerHit,edm4hep::SimTrackerHit> >'),
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
    'detectorName' : """ Name of the detector (default: Vertex) [VTXdigitizer] """,
    'readoutName' : """ Name of the detector readout [VTXdigitizer] """,
    'xResolution' : """ Spatial resolutions in the x direction per layer [mm] (r-phi direction in barrel, z direction in disks) [VTXdigitizer] """,
    'yResolution' : """ Spatial resolutions in the y direction per layer [mm] (r direction in barrel, r-phi direction in disks) [VTXdigitizer] """,
    'tResolution' : """ Time resolutions per layer [ns] [VTXdigitizer] """,
    'forceHitsOntoSurface' : """ Project hits onto the surface in case they are not yet on the surface (default: false [VTXdigitizer] """,
    'inputSimHits' : """ Input sim vertex hit collection name [unknown owner type] """,
    'outputDigiHits' : """ Output digitized vertex hit collection name [unknown owner type] """,
    'outputSimDigiAssociation' : """ Output link between sim hits and digitized hits [unknown owner type] """,
  }
  __declaration_location__ = 'VTXdigitizer.cpp:3'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(VTXdigitizer, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'VTXdigi'
  def getType( self ):
      return 'VTXdigitizer'
  pass # class VTXdigitizer
