#pragma once
#include <cstdint>

namespace IPv4 {
struct Address {
  uint32_t s_addr;
};
} // namespace IPv4

#include "../icmp/icmp.h"

#include <map>
#include <memory>

namespace ICMP {
class Protocol;
}

namespace IPv4 {

// Definitions for IP Fragmentation
#define IP_RF 0x8000      /* reserved fragment flag */
#define IP_DF 0x4000      /* dont fragment flag */
#define IP_MF 0x2000      /* more fragments flag */
#define IP_OFFMASK 0x1fff /* mask for fragmenting bits */

struct Header {
  unsigned int ip_hl : 4; /* header length */
  unsigned int ip_v : 4;  /* version */

  uint8_t ip_tos;        /* type of service */
  unsigned short ip_len; /* total length */
  unsigned short ip_id;  /* identification */
  unsigned short ip_off; /* fragment offset field */

  uint8_t ip_ttl;         /* time to live */
  uint8_t ip_p;           /* protocol */
  unsigned short ip_sum;  /* checksum */
  Address ip_src, ip_dst; /* source and dest address */
} __attribute__((__packed__));

struct Frame {
  Header hdr;
  uint8_t payload[];
} __attribute__((__packed__));

class Protocol {
private:
  Address ipAddress;
  Ethernet::Protocol *ethernet_handler;
  std::unique_ptr<ICMP::Protocol> icmp_handler;

public:
  Protocol(const Address &address);

  bool isOwnIpAddress(const Address &address) { return ipAddress.s_addr == address.s_addr; }

  void handle_packet(const Ethernet::Address &src_mac, const uint8_t *buffer, size_t buffer_len);

  void send(const Ethernet::Address &dst_mac, const IPv4::Address &dst_ip, const uint16_t protocol,
            uint8_t *payload, size_t payload_len);

  void set_ethernet_handler(const std::unique_ptr<Ethernet::Protocol> &handler) {
    ethernet_handler = handler.get();
  }

  static uint16_t checksum(void *data, size_t len) {
    auto p = reinterpret_cast<const uint16_t *>(data);
    uint32_t sum = 0;
    if (len & 1) {
      // len is odd
      sum = reinterpret_cast<const uint8_t *>(p)[len - 1];
    }
    len /= 2;
    while (len--) {
      sum += *p++;
      if (sum & 0xffff0000) {
        sum = (sum >> 16) + (sum & 0xffff);
      }
    }
    return static_cast<uint16_t>(~sum);
  }
};
} // namespace IPv4
