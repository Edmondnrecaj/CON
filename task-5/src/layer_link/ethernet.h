#pragma once
#include <cstdint>
#include <memory>
#include <vector>

#include <net/ethernet.h> // struct ether_header, struct ether_addr
#include <netinet/in.h>   // ntohs

namespace IPv4 {
class Protocol;
}
namespace ARP {
class Protocol;
}

namespace Ethernet {

#define ETH_ALEN 6 /* Octets in one ethernet addr	 */

// Ethernet protocol IDs
enum { TYPE_IP = 0x0800, TYPE_ARP = 0x0806 };

struct Address {
  uint8_t ether_addr_octet[ETH_ALEN];
} __attribute__((__packed__));

struct Header {
  uint8_t ether_dhost[ETH_ALEN]; /* destination eth addr	*/
  uint8_t ether_shost[ETH_ALEN]; /* source ether addr	*/
  uint16_t ether_type;           /* packet type ID field	*/
} __attribute__((__packed__));

struct Frame {
  Header hdr;
  uint8_t payload[];
} __attribute__((__packed__));

class Protocol {
  using send_callback = void (*)(char *buf, size_t bufsiz);

public:
  Address mac;

  Protocol(Address mac, const std::unique_ptr<IPv4::Protocol> &ipv4_handler,
           const std::unique_ptr<ARP::Protocol> &arp_handler, send_callback send_bytes)
      : mac(mac), ipv4_handler(ipv4_handler.get()), arp_handler(arp_handler.get()),
        send_bytes(send_bytes) {}

  void handle_packet(const uint8_t *buffer, size_t buffer_len);

  void send(const Address &dst, uint16_t ether_type, uint8_t *payload, size_t payload_len);

private:
  IPv4::Protocol *ipv4_handler;
  ARP::Protocol *arp_handler;
  send_callback send_bytes = nullptr;

  void send(uint8_t *data, size_t data_len) {
    if (send_bytes)
      send_bytes((char *)data, data_len);
  }
};
} // namespace Ethernet
