#include "ethernet.h"
#include "../layer_internet/arp.h"
#include "../layer_internet/ipv4.h"
#include "../logging.h"

#include <cstring>
#include <algorithm>

using namespace Ethernet;

void Protocol::handle_packet(const uint8_t *buffer, size_t buffer_len) {
  if (buffer_len < sizeof(Frame))
    return;

  auto frame = reinterpret_cast<const Frame * >(buffer);
  log_ethernet_frame(reinterpret_cast<const Address *>(frame->hdr.ether_shost),
                     reinterpret_cast<const Address *>(frame->hdr.ether_dhost));

  uint16_t ether_type = ntohs(frame->hdr.ether_type);
  const uint8_t *payload = buffer + sizeof(Header);
  size_t payload_len = buffer_len - sizeof(Header);

  if (ether_type == TYPE_IP)
  { 
    ipv4_handler->handle_packet(*reinterpret_cast<const Address * >(frame->hdr.ether_shost), payload, payload_len);
  }
  else if (ether_type == TYPE_ARP)
  {
    arp_handler->handle_packet(payload, payload_len);
  }
}

void Protocol::send(const Address &dst, uint16_t ether_type, uint8_t *payload, size_t payload_len) {
  
  std::vector<uint8_t> packet(sizeof(Header) + payload_len);

  auto *header = reinterpret_cast<Header * >(packet.data());
  memcpy(header->ether_dhost, &dst, ETH_ALEN);
  memcpy(header->ether_shost, &mac, ETH_ALEN);
  header->ether_type = htons(ether_type); 

  memcpy(packet.data() + sizeof(Header), payload, payload_len);

  log_ethernet_frame(&mac, &dst);

  send((uint8_t *)packet.data(), packet.size());
}
