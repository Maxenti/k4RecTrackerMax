// AUTOMATICALLY GENERATED FILE - DO NOT EDIT

#include "extension/SenseWireHitSIOBlock.h"
#include "extension/SenseWireHitCollection.h"

#include "podio/CollectionBuffers.h"
#include "podio/CollectionBufferFactory.h"

#include <sio/block.h>
#include <sio/io_device.h>
#include <sio/version.h>

namespace extension {


void SenseWireHitSIOBlock::read(sio::read_device& device, sio::version_type version) {
  const auto& bufferFactory = podio::CollectionBufferFactory::instance();
  // TODO:
  // - Error handling of empty optional
  auto maybeBuffers = bufferFactory.createBuffers("extension::SenseWireHitCollection", sio::version::major_version(version), m_subsetColl);
  m_buffers = maybeBuffers.value_or(podio::CollectionReadBuffers{});

  if (not m_subsetColl) {
    unsigned size(0);
    device.data( size );
    auto* dataVec = m_buffers.dataAsVector<extension::SenseWireHitData>();
    dataVec->resize(size);
    podio::handlePODDataSIO(device, dataVec->data(), size);
  }

  //---- read ref collections -----
  auto* refCols = m_buffers.references;
  for( auto& refC : *refCols ){
    unsigned size{0};
    device.data( size ) ;
    refC->resize(size) ;
    podio::handlePODDataSIO( device ,  refC->data(), size ) ;
  }

  if (not m_subsetColl) {
    //---- read vector members
    auto* vecMemInfo = m_buffers.vectorMembers;
    unsigned size{0};

    auto* vec0 = reinterpret_cast<std::vector<std::uint16_t>*>(vecMemInfo->at(0).second);
    size = 0u;
    device.data(size);
    vec0->resize(size);
    podio::handlePODDataSIO(device, vec0->data(), size);

  }
}

void SenseWireHitSIOBlock::write(sio::write_device& device) {
  if (not m_subsetColl) {
    auto* dataVec = podio::CollectionWriteBuffers::asVector<extension::SenseWireHitData>(m_buffers.data);
    unsigned size = dataVec->size() ;
    device.data( size ) ;
    podio::handlePODDataSIO( device ,  dataVec->data(), size ) ;
  }

  //---- write ref collections -----
  auto* refCols = m_buffers.references;
  for( auto& refC : *refCols ){
    unsigned size = refC->size() ;
    device.data( size ) ;
    podio::handlePODDataSIO( device ,  refC->data(), size ) ;
  }

  if (not m_subsetColl) {
    //---- write vector members
    auto* vecMemInfo = m_buffers.vectorMembers;
    unsigned size{0};

    auto* vec0 = *reinterpret_cast<std::vector<std::uint16_t>**>(vecMemInfo->at(0).second);
    size = vec0->size();
    device.data(size);
    podio::handlePODDataSIO(device, &(*vec0)[0], size);


  }
}

namespace {
  // Create one instance of the type in order to ensure that the SioBlock
  // library actually needs linking to the core library. Otherwise it is
  // possible that the registry is not populated when the SioBlock library is
  // loaded, e.g. when using the python bindings.
  const auto elemSenseWireHit = extension::SenseWireHit{};
}

} // namespace extension

