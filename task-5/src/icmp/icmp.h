#pragma once
#include "../layer_link/ethernet.h"
#include "../layer_internet/ipv4.h"

namespace ICMP {
struct Header {
  uint8_t type; /* message type */
  uint8_t code; /* type sub-code */
  uint16_t checksum;
  uint16_t identifier;
  uint16_t sequence;
};

struct Frame {
  Header hdr;
  uint8_t payload[];
} __attribute__((__packed__));

#define ICMP_ECHOREPLY 0 /* Echo Reply			*/
#define ICMP_ECHO 8      /* Echo Request			*/

class Protocol {
private:
  IPv4::Protocol *ipv4_handler;

public:
  Protocol(IPv4::Protocol *handler) { ipv4_handler = handler; };
  void handle_packet(const Ethernet::Address &src_mac, const IPv4::Address &src_ip,
                     const IPv4::Address &dst_ip, const uint8_t *buffer, size_t buffer_len);

  void send(const Frame *req_frame, size_t frame_len, const Ethernet::Address &dst_mac,
            const IPv4::Address &dst_ip);
};
} // namespace ICMP
