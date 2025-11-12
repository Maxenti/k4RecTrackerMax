// AUTOMATICALLY GENERATED FILE - DO NOT EDIT

#include "extension/SenseWireHitObj.h"
#include "podio/ObjectID.h"

namespace extension {

SenseWireHitObj::SenseWireHitObj() :
  data(),
  m_nElectrons(new std::vector<std::uint16_t>())
{  }

SenseWireHitObj::SenseWireHitObj(const podio::ObjectID& id_, const SenseWireHitData& data_) :
  id(id_), data(data_)
{  }

SenseWireHitObj::SenseWireHitObj(const SenseWireHitObj& other) :
  data(other.data),
  m_nElectrons(new std::vector<std::uint16_t>(*(other.m_nElectrons)))
{
}

SenseWireHitObj::~SenseWireHitObj() {
  if (id.index == podio::ObjectID::untracked) {
    delete m_nElectrons;
  }
}
} // namespace extension

