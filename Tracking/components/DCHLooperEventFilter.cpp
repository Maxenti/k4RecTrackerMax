#include "GaudiKernel/Algorithm.h"
#include "Gaudi/Property.h"

#include "k4FWCore/DataHandle.h"
#include "edm4hep/SimTrackerHitCollection.h"

#include <algorithm>
#include <limits>

class DCHLooperEventFilter : public Algorithm {
public:
  DCHLooperEventFilter(const std::string& name, ISvcLocator* svcLoc)
    : Algorithm(name, svcLoc) {}

  StatusCode initialize() override {
    // Nothing special; properties are configured via job options / python.
    info() << "DCHLooperEventFilter initialized with:"
           << " TmaxNs=" << m_tmaxNs
           << " NHitsMax=" << m_nHitsMax
           << " KeepEmpty=" << (m_keepEmpty ? "true" : "false")
           << endmsg;
    return Algorithm::initialize();
  }

  StatusCode execute() override {
    bool pass = true;

    const auto* hits = m_inHits.get();
    if (!hits) {
      // You can choose fail-open or fail-closed. Here: fail-open (don’t kill event).
      warning() << "InputSimHits collection not available; passing event." << endmsg;
      setFilterPassed(true);
      return StatusCode::SUCCESS;
    }

    const int n = static_cast<int>(hits->size());

    if (n == 0) {
      pass = m_keepEmpty;
      setFilterPassed(pass);
      return StatusCode::SUCCESS;
    }

    if (m_nHitsMax > 0 && n > m_nHitsMax) {
      pass = false;
      setFilterPassed(false);
      if (msgLevel(MSG::DEBUG)) {
        debug() << "VETO: nHits=" << n << " > NHitsMax=" << m_nHitsMax << endmsg;
      }
      return StatusCode::SUCCESS;
    }

    double tmax = -std::numeric_limits<double>::infinity();
    for (const auto& h : *hits) {
      tmax = std::max(tmax, static_cast<double>(h.getTime()));
    }

    pass = (tmax <= m_tmaxNs);
    setFilterPassed(pass);

    if (!pass && msgLevel(MSG::DEBUG)) {
      debug() << "VETO: tmax=" << tmax << " ns > TmaxNs=" << m_tmaxNs
              << " (nHits=" << n << ")" << endmsg;
    }

    return StatusCode::SUCCESS;
  }

private:
  // Configurable from python/job options:
  //   LooperFilter.InputSimHits = "DCHCollection"  (or whatever)
  k4FWCore::DataHandle<edm4hep::SimTrackerHitCollection> m_inHits{
      "InputSimHits", Gaudi::DataHandle::Reader, this};

  Gaudi::Property<double> m_tmaxNs{this, "TmaxNs", 450.0,
                                  "Keep event if max(hit.time) <= this [ns]"};

  Gaudi::Property<int> m_nHitsMax{this, "NHitsMax", 30000,
                                 "Keep event if nHits <= this (<=0 disables)"};

  Gaudi::Property<bool> m_keepEmpty{this, "KeepEmpty", false,
                                    "If true, keep events with 0 hits"};
};

DECLARE_COMPONENT(DCHLooperEventFilter)
