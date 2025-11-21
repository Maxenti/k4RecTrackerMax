#Mon Nov 17 21:54:58 2025"""Automatically generated. DO NOT EDIT please"""
from GaudiKernel.DataHandle import DataHandle
from GaudiKernel.Proxy.Configurable import *

class ARCdigitizer( ConfigurableAlgorithm ) :
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
    'flatSiPMEfficiency' : -1.00000,
    'applySiPMEffiToDigiHits' : False,
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
    'flatSiPMEfficiency' : """ Flat value for SiPM quantum efficiency (<0 := disabled) [ARCdigitizer] """,
    'applySiPMEffiToDigiHits' : """ Apply the SiPM efficiency to digitized hits instead of simulated hits [ARCdigitizer] """,
    'inputSimHits' : """ Input sim tracker hit collection name [unknown owner type] """,
    'outputDigiHits' : """ Output digitized tracker hit collection name [unknown owner type] """,
  }
  __declaration_location__ = 'ARCdigitizer.cpp:13'
  def __init__(self, name = Configurable.DefaultName, **kwargs):
      super(ARCdigitizer, self).__init__(name)
      for n,v in kwargs.items():
         setattr(self, n, v)
  def getDlls( self ):
      return 'ARCdigi'
  def getType( self ):
      return 'ARCdigitizer'
  pass # class ARCdigitizer
