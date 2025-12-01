// (same license/header as yours)

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <memory>
#include <numeric>
#include <queue>
#include <random>
#include <sstream>
#include <string>
#include <typeinfo>
#include <vector>

// ONNX & Torch
#include "onnxruntime_cxx_api.h"
#include "onnxruntime_run_options_config_keys.h"
#include <ATen/ATen.h>
#include <torch/torch.h>

// ROOT
#include "TFile.h"
#include "TGeoMatrix.h"
#include "TH1D.h"
#include "TRandom3.h"
#include "TVector3.h"

// === Gaudi Framework ===
#include "Gaudi/Algorithm.h"
#include "Gaudi/Property.h"
#include "GaudiKernel/IRndmGenSvc.h"
#include "GaudiKernel/RndmGenerators.h"

// === k4FWCore / k4Interface ===
#include "k4FWCore/DataHandle.h"
#include "k4FWCore/Transformer.h"
#include "k4Interface/IGeoSvc.h"
#include "k4Interface/IUniqueIDGenSvc.h"

// === EDM4HEP & PODIO ===
#include "edm4hep/EventHeaderCollection.h"
#include "edm4hep/MCParticleCollection.h"
#include "edm4hep/ParticleIDData.h"
#include "edm4hep/SimTrackerHitCollection.h"
#include "edm4hep/TrackerHitPlaneCollection.h"
#include "edm4hep/TrackerHit3DCollection.h"
#include "podio/UserDataCollection.h"

// === EDM4HEP Extensions ===
#include "extension/DriftChamberDigiCollection.h"
#include "extension/DriftChamberDigiLocalCollection.h"
#include "extension/MCRecoDriftChamberDigiAssociationCollection.h"
#include "extension/SenseWireHitCollection.h"
#include "extension/SenseWireHitSimTrackerHitLinkCollection.h"
#include "extension/TrackCollection.h"
#include "extension/TrackerHit.h"

// === DD4hep ===
#include "DD4hep/Detector.h"
#include "DDRec/DCH_info.h"
#include "DDRec/Vector3D.h"
#include "DDSegmentation/BitFieldCoder.h"

// === Project-specific ===
#include "utils.hpp"

/**
 * GGTF_tracking
 *
 * Inputs:
 *   - vector<TrackerHitPlaneCollection*>  (planar/vtx/silicon)
 *   - vector<SenseWireHitCollection*>     (drift chamber wire hits)
 *
 * Outputs:
 *   - extension::TrackCollection          (as before)
 *   - edm4hep::TrackerHit3DCollection     (NEW: "GGTF_3DHits" for fitters)
 */
struct GGTF_tracking final
  : k4FWCore::MultiTransformer<
      std::tuple<extension::TrackCollection, edm4hep::TrackerHit3DCollection>(
        const std::vector<const edm4hep::TrackerHitPlaneCollection*>&,
        const std::vector<const extension::SenseWireHitCollection*>&)> {

  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<
                      std::tuple<>, std::tuple<>, Traits>::KeyValues;

  GGTF_tracking(const std::string& name, ISvcLocator* svcLoc)
  : MultiTransformer(name, svcLoc,
      // Inputs
      std::tuple<KeyValues>{
        KeyValues{"InputPlanarHitCollections", std::vector<std::string>{"InputPlanarHitCollections"}},
        KeyValues{"InputWireHitCollections",   std::vector<std::string>{"InputWireHitCollections"}}
      },
      // Outputs
      std::tuple<KeyValues>{
        KeyValues{"OutputTracksGGTF", std::vector<std::string>{"OutputTracksGGTF"}},
        KeyValues{"Output3DHits",     std::vector<std::string>{"GGTF_3DHits"}}
      })
  {
    m_geoSvc = serviceLocator()->service(m_geoSvcName);
  }

  StatusCode initialize() override {
    // --- ONNX init (unchanged) ---
    m_fInfo = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
    auto envLocal = std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING, "ONNX_Runtime");
    m_fEnv = std::move(envLocal);
    m_fSessionOptions.SetIntraOpNumThreads(1);
    m_fSessionOptions.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_DISABLE_ALL);

    auto sessionLocal = std::make_unique<Ort::Session>(*m_fEnv, m_modelPath.value().c_str(), m_fSessionOptions);
    m_fSession = std::move(sessionLocal);

    Ort::AllocatorWithDefaultOptions allocator;
    std::size_t i = 0;
    const auto inputNames  = m_fSession->GetInputNameAllocated(i, allocator).release();
    const auto outputNames = m_fSession->GetOutputNameAllocated(i, allocator).release();
    m_fInames.push_back(inputNames);
    m_fOnames.push_back(outputNames);

    // --- DCH info / decoder (best effort) ---
    try {
      dd4hep::DetElement dchDet = m_geoSvc->getDetector()->detectors().at(m_dchName.value().c_str());
      m_dchInfo = dchDet.extension<dd4hep::rec::DCH_info>();
      dd4hep::SensitiveDetector dchSens = m_geoSvc->getDetector()->sensitiveDetector(m_dchName.value().c_str());
      dd4hep::Readout dchRed = dchSens.readout();
      m_dchDecoder = dchRed.idSpec().decoder();
    } catch (...) {
      // non-fatal
    }

    info() << "GGTF_tracking init | model=" << m_modelPath.value()
           << " | tbeta=" << m_tbeta.value()
           << " | td="    << m_td.value()
           << " | Produce3DHits=" << (m_produce3DHits.value()?"true":"false")
           << endmsg;

    return StatusCode::SUCCESS;
  }

  std::tuple<extension::TrackCollection, edm4hep::TrackerHit3DCollection>
  operator()(const std::vector<const edm4hep::TrackerHitPlaneCollection*>& inputPlanarHitCollections,
             const std::vector<const extension::SenseWireHitCollection*>&   inputWireHitCollections) const override
  {
    info() << "Processing event number: " << m_indexCounter++ << endmsg;

    // Outputs
    extension::TrackCollection     outputTracks;
    edm4hep::TrackerHit3DCollection output3D; // NEW

    // Early exit when 3D production is disabled and no tracks expected
    // (we still produce tracks per clusters below; produce3DHits only gates 3D creation)
    constexpr int kMaxModelHits = 200000; // absolute guard

    // --- Flatten inputs for model (unchanged) ---
    std::vector<float>   listGlobalInputs; listGlobalInputs.reserve(7 * 4096);
    int globalHitIndex = 0;

    // Planar bookkeeping
    std::vector<int64_t> listHitTypePlanar;
    std::vector<int64_t> listPlanarHitIndices; // [collIdx, subIdx] pairs
    int planarHitIndex = 0, planarHitCollectionIndex = 0;

    for (const auto* inputHitCollection : inputPlanarHitCollections) {
      int planarHitSubCollectionIndex = 0;
      for (const auto& hit : *inputHitCollection) {
        // x,y,z
        listGlobalInputs.push_back(hit.getPosition().x);
        listGlobalInputs.push_back(hit.getPosition().y);
        listGlobalInputs.push_back(hit.getPosition().z);
        // placeholders (unchanged)
        listGlobalInputs.push_back(1.0f);
        listGlobalInputs.push_back(0.0f);
        listGlobalInputs.push_back(0.0f);
        listGlobalInputs.push_back(0.0f);

        listHitTypePlanar.push_back(globalHitIndex);
        listPlanarHitIndices.push_back(planarHitCollectionIndex);
        listPlanarHitIndices.push_back(planarHitSubCollectionIndex);

        ++globalHitIndex;
        ++planarHitIndex;
        ++planarHitSubCollectionIndex;

        if (globalHitIndex >= kMaxModelHits) break;
      }
      ++planarHitCollectionIndex;
      if (globalHitIndex >= kMaxModelHits) break;
    }

    // Wire bookkeeping
    std::vector<int64_t> listHitTypeWire;
    std::vector<int64_t> listWireHitIndices; // [collIdx, subIdx] pairs
    int wireHitIndex = 0, wireHitCollectionIndex = 0;

    for (const auto* inputHitCollection : inputWireHitCollections) {
      int wireHitSubCollectionIndex = 0;
      for (const auto& inputHit : *inputHitCollection) {
        // wire position (global)
        edm4hep::Vector3d wirePos = inputHit.getPosition();
        TVector3 wirePosV(wirePos.x, wirePos.y, wirePos.z);

        // drift geometry
        double distanceToWire     = inputHit.getDistanceToWire();
        double wireAzimuthalAngle = inputHit.getWireAzimuthalAngle();
        double wireStereoAngle    = inputHit.getWireStereoAngle();

        // wire direction z'
        TVector3 direction(0,0,1);
        direction.RotateX(wireStereoAngle);
        direction.RotateZ(wireAzimuthalAngle);
        TVector3 zPrime = direction.Unit();

        // x' orthogonal to z'
        TVector3 xPrime(1.0, 0.0, -direction.X()/std::max(1e-9, direction.Z()));
        xPrime = xPrime.Unit();
        // y' = z' x x'
        TVector3 yPrime = zPrime.Cross(xPrime).Unit();

        // left/right local/global candidates (mm)
        TVector3 leftLocal (-distanceToWire, 0.0, 0.0);
        TVector3 rightLocal( distanceToWire, 0.0, 0.0);
        TVector3 leftGlobal  = xPrime*leftLocal.X()  + yPrime*leftLocal.Y()  + zPrime*leftLocal.Z()  + wirePosV;
        TVector3 rightGlobal = xPrime*rightLocal.X() + yPrime*rightLocal.Y() + zPrime*rightLocal.Z() + wirePosV;

        // Pack model input (unchanged: base at left, diff = right-left)
        listGlobalInputs.push_back(leftGlobal.X());
        listGlobalInputs.push_back(leftGlobal.Y());
        listGlobalInputs.push_back(leftGlobal.Z());
        listGlobalInputs.push_back(0.0f);
        listGlobalInputs.push_back(rightGlobal.X() - leftGlobal.X());
        listGlobalInputs.push_back(rightGlobal.Y() - leftGlobal.Y());
        listGlobalInputs.push_back(rightGlobal.Z() - leftGlobal.Z());

        listHitTypeWire.push_back(globalHitIndex);
        listWireHitIndices.push_back(wireHitCollectionIndex);
        listWireHitIndices.push_back(wireHitSubCollectionIndex);

        ++globalHitIndex;
        ++wireHitIndex;
        ++wireHitSubCollectionIndex;

        if (globalHitIndex >= kMaxModelHits) break;
      }
      ++wireHitCollectionIndex;
      if (globalHitIndex >= kMaxModelHits) break;
    }

    // Early out: nothing to run
    if (globalHitIndex <= 0) {
      return std::make_tuple(std::move(outputTracks), std::move(output3D));
    }

    // ---- Build tensors for clustering step (unchanged) ----
    torch::Tensor listHitTypePlanarTensor =
        torch::from_blob(listHitTypePlanar.data(), {planarHitIndex}, torch::kFloat32);
    torch::Tensor listPlanarHitIndicesTensor =
        torch::from_blob(listPlanarHitIndices.data(), {planarHitIndex, 2}, torch::kInt64);

    torch::Tensor listHitTypeWireTensor =
        torch::from_blob(listHitTypeWire.data(), {wireHitIndex}, torch::kFloat32);
    torch::Tensor listWireHitIndicesTensor =
        torch::from_blob(listWireHitIndices.data(), {wireHitIndex, 2}, torch::kInt64);

    torch::Tensor planarTypeTensor = torch::zeros({planarHitIndex, 1}, torch::kInt64);
    torch::Tensor wireTypeTensor   = torch::ones ({wireHitIndex,   1}, torch::kInt64);

    torch::Tensor planarTypeIndexTensor = torch::cat({planarTypeTensor, listPlanarHitIndicesTensor}, 1);
    torch::Tensor wireTypeIndexTensor   = torch::cat({wireTypeTensor,   listWireHitIndicesTensor}, 1);
    torch::Tensor listHitIndicesGlobal  = torch::cat({planarTypeIndexTensor, wireTypeIndexTensor}, 0);

    // ---- Run model (unchanged) ----
    const size_t totalSize = static_cast<size_t>(globalHitIndex) * 7;
    std::vector<int64_t> inputShape{globalHitIndex, 7};

    std::vector<Ort::Value> inputTensors;
    inputTensors.emplace_back(Ort::Value::CreateTensor<float>(
        m_fInfo, listGlobalInputs.data(), totalSize, inputShape.data(), inputShape.size()));

    auto outputModelTensors = m_fSession->Run(Ort::RunOptions{nullptr},
                                              m_fInames.data(), inputTensors.data(), m_fInames.size(),
                                              m_fOnames.data(), m_fOnames.size());

    float* outPtr = outputModelTensors.front().GetTensorMutableData<float>();
    std::vector<float> outputModelVector(outPtr, outPtr + static_cast<size_t>(globalHitIndex) * 4);

    // ---- Clustering (unchanged) ----
    auto clusteringIndeces = get_clustering(outputModelVector, globalHitIndex, m_tbeta, m_td);
    torch::Tensor uniqueTensor, inverseIndices;
    std::tie(uniqueTensor, inverseIndices) = at::_unique(clusteringIndeces, /*sorted=*/true, /*return_inverse=*/true);

    // If there are any clusters at all, create a dummy track when label 0 is not present (matches previous behaviour)
    const int64_t numTracks = uniqueTensor.numel();
    const bool hasZero = (uniqueTensor == 0).any().item<bool>();
    if (!hasZero && numTracks > 0) {
      auto t = outputTracks.create();
      t.setType(0);
    }

    // --- Helper to fetch planar/wire hit by (coll,sub) ---
    auto getPlanar = [&](int64_t coll, int64_t sub) -> edm4hep::TrackerHitPlane {
      const auto* col = inputPlanarHitCollections.at(coll);
      return col->at(sub);
    };
    auto getWire = [&](int64_t coll, int64_t sub) -> extension::SenseWireHit {
      const auto* col = inputWireHitCollections.at(coll);
      return col->at(sub);
    };

    // ---- Per-cluster loop: build tracks and (optionally) GGTF_3DHits ----
    int total3DThisEvent = 0;

    for (int64_t i = 0; i < numTracks; ++i) {
      const auto idTrackTensor = uniqueTensor.index({i});
      const int  idTrack       = idTrackTensor.item<int>();

      // Build a mask and indices for current cluster
      torch::Tensor mask    = (clusteringIndeces == idTrack);
      torch::Tensor indices = torch::nonzero(mask).flatten();
      const int64_t N = indices.size(0);
      if (N <= 0) continue;

      // Create track
      auto outTrk = outputTracks.create();
      outTrk.setType(idTrack);

      // Precompute XY centroid from *wire positions* for LR choice
      double cx=0.0, cy=0.0; int nWireCent=0;

      auto listHitIndicesGlobalView = listHitIndicesGlobal.accessor<int64_t, 2>();
      auto idxView = indices.accessor<int64_t, 1>();

      // First pass: accumulate centroid & attach raw hits to Track
      for (int64_t j = 0; j < N; ++j) {
        const int64_t row  = idxView[j];
        const int64_t type = listHitIndicesGlobalView[row][0];
        const int64_t cidx = listHitIndicesGlobalView[row][1];
        const int64_t sidx = listHitIndicesGlobalView[row][2];

        if (type == 0) {
          // planar
          auto ph = getPlanar(cidx, sidx);
          outTrk.addToTrackerHits(ph);
        } else {
          // wire
          auto wh = getWire(cidx, sidx);
          // wire global position (center)
          const auto wp = wh.getPosition();
          cx += wp.x; cy += wp.y; ++nWireCent;
          outTrk.addToTrackerHits(wh);
        }
      }
      const bool haveCentroid = (nWireCent > 0);
      const double cxyx = haveCentroid ? (cx / nWireCent) : 0.0;
      const double cxyy = haveCentroid ? (cy / nWireCent) : 0.0;

      // Second pass: optionally create GGTF_3DHits
      int madeForThisTrack = 0;
      if (m_produce3DHits.value()) {
        for (int64_t j = 0; j < N; ++j) {
          if (m_max3DHitsPerEvent.value() > 0 && total3DThisEvent >= m_max3DHitsPerEvent.value()) break;
          if (m_max3DPerTrack.value() > 0 && madeForThisTrack >= m_max3DPerTrack.value()) break;

          const int64_t row  = idxView[j];
          const int64_t type = listHitIndicesGlobalView[row][0];
          const int64_t cidx = listHitIndicesGlobalView[row][1];
          const int64_t sidx = listHitIndicesGlobalView[row][2];

          if (type == 0) {
            // planar -> direct 3D point
            auto ph = getPlanar(cidx, sidx);
            const auto p = ph.getPosition();

            auto h3 = output3D.create();
            h3.setPosition({p.x, p.y, p.z});
            h3.setType(idTrack);
            h3.setCellID(ph.getCellID());
            h3.setTime(0.0f);
            // cov diag in mm^2 (XY 0.5^2, Z 3^2): [xx, xy, xz, yy, yz, zz]
            h3.setCovMatrix({0.25f, 0.f, 0.f, 0.25f, 0.f, 9.0f});

            ++madeForThisTrack; ++total3DThisEvent;
          } else {
            // wire -> choose left/right by proximity to centroid in XY
            auto wh = getWire(cidx, sidx);

            edm4hep::Vector3d wirePos = wh.getPosition();
            TVector3 wirePosV(wirePos.x, wirePos.y, wirePos.z);

            const double distanceToWire     = wh.getDistanceToWire();
            const double wireAzimuthalAngle = wh.getWireAzimuthalAngle();
            const double wireStereoAngle    = wh.getWireStereoAngle();

            TVector3 direction(0,0,1);
            direction.RotateX(wireStereoAngle);
            direction.RotateZ(wireAzimuthalAngle);
            TVector3 zPrime = direction.Unit();

            TVector3 xPrime(1.0, 0.0, -direction.X()/std::max(1e-9, direction.Z()));
            xPrime = xPrime.Unit();
            TVector3 yPrime = zPrime.Cross(xPrime).Unit();

            TVector3 leftLocal (-distanceToWire, 0.0, 0.0);
            TVector3 rightLocal( distanceToWire, 0.0, 0.0);
            TVector3 leftGlobal  = xPrime*leftLocal.X()  + yPrime*leftLocal.Y()  + zPrime*leftLocal.Z()  + wirePosV;
            TVector3 rightGlobal = xPrime*rightLocal.X() + yPrime*rightLocal.Y() + zPrime*rightLocal.Z() + wirePosV;

            TVector3 chosen = leftGlobal;
            if (haveCentroid) {
              const double dl = (leftGlobal  - TVector3(cxyx, cxyy, leftGlobal.Z())).Perp2();
              const double dr = (rightGlobal - TVector3(cxyx, cxyy, rightGlobal.Z())).Perp2();
              chosen = (dr < dl ? rightGlobal : leftGlobal);
            }

            auto h3 = output3D.create();
            h3.setPosition({(double)chosen.X(), (double)chosen.Y(), (double)chosen.Z()});
            h3.setType(idTrack);
            h3.setCellID(wh.getCellID());
            h3.setTime(0.0f);
            h3.setCovMatrix({0.25f, 0.f, 0.f, 0.25f, 0.f, 9.0f});

            ++madeForThisTrack; ++total3DThisEvent;
          }
        }
      }
    }

    // Cleanup tensors/buffers (as before)
    inverseIndices.reset();
    uniqueTensor.reset();
    clusteringIndeces.reset();
    inputTensors.clear();
    outputModelTensors.clear();

    listHitTypePlanarTensor.reset();
    listPlanarHitIndicesTensor.reset();
    listHitTypeWireTensor.reset();
    listWireHitIndicesTensor.reset();

    std::vector<int64_t>().swap(listHitTypePlanar);
    std::vector<int64_t>().swap(listPlanarHitIndices);
    std::vector<int64_t>().swap(listHitTypeWire);
    std::vector<int64_t>().swap(listWireHitIndices);
    std::vector<float>().swap(listGlobalInputs);

    return std::make_tuple(std::move(outputTracks), std::move(output3D));
  }

  StatusCode finalize() override {
    info() << "Run report:" << endmsg;
    info() << "Number of analysed events: " << m_indexCounter << endmsg;
    info() << "----------------" << endmsg;
    return StatusCode::SUCCESS;
  }

public:
  mutable int m_indexCounter = 0;

private:
  // ---- ONNX ----
  std::unique_ptr<Ort::Env>     m_fEnv;
  std::unique_ptr<Ort::Session> m_fSession;
  Ort::SessionOptions           m_fSessionOptions;
  const OrtMemoryInfo*          m_fInfo{nullptr};
  std::vector<const char*>      m_fInames;
  std::vector<const char*>      m_fOnames;

  // ---- Config knobs ----
  Gaudi::Property<std::string> m_modelPath{this, "ModelPath", "", "ModelPath"};
  Gaudi::Property<double>      m_tbeta    {this, "Tbeta", 0.6, "tbeta"};
  Gaudi::Property<double>      m_td       {this, "Td",    0.3, "td"};

  // 3D output controls (wired to your Python args)
  Gaudi::Property<bool>  m_produce3DHits     {this, "Produce3DHits", false, "If true, emit GGTF_3DHits"};
  Gaudi::Property<int>   m_max3DHitsPerEvent {this, "Max3DHitsPerEvent", 0, "Cap per event (0=off)"};
  Gaudi::Property<int>   m_max3DPerTrack     {this, "Max3DPerTrack",     0, "Cap per track (0=off)"};

  // ---- Geometry / services ----
  Gaudi::Property<std::string> m_geoSvcName{this, "GeoSvcName", "GeoSvc", "The name of the GeoSvc instance"};
  Gaudi::Property<std::string> m_uidSvcName{this, "UidSvcName", "uidSvc", "The name of the UniqueIDGenSvc instance"};
  Gaudi::Property<std::string> m_dchName   {this, "DchName", "DCH_v2", "Name of the Drift Chamber detector"};

  SmartIF<IGeoSvc>                        m_geoSvc;
  dd4hep::rec::DCH_info*                  m_dchInfo{nullptr};
  dd4hep::DDSegmentation::BitFieldCoder*  m_dchDecoder{nullptr};
};

DECLARE_COMPONENT(GGTF_tracking)
