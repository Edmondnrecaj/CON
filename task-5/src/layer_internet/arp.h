#pragma once
#include "../layer_link/ethernet.h"
#include "../layer_internet/ipv4.h"

#include <memory>

#include <net/if_arp.h> // struct arphdr

namespace IPv4 {
class Protocol;
}

namespace ARP {
/* ARP protocol opcodes. */
#define ARPOP_REQUEST 1 /* ARP request.  */
#define ARPOP_REPLY 2   /* ARP reply.  */

/* ARP protocol HARDWARE identifiers. */
#define ARPHRD_ETHER 1 /* Ethernet 10/100Mbps.  */

struct Header {
  unsigned short int ar_hrd; /* Format of hardware address.  */
  unsigned short int ar_pro; /* Format of protocol address.  */
  unsigned char ar_hln;      /* Length of hardware address.  */
  unsigned char ar_pln;      /* Length of protocol address.  */
  unsigned short int ar_op;  /* ARP opcode (command).  */
} __attribute__((packed));

struct Packet {
  Header hdr;
  Ethernet::Address src_mac;
  IPv4::Address src_ip;
  Ethernet::Address dst_mac;
  IPv4::Address dst_ip;
} __attribute__((packed));

class Protocol {
private:
  Ethernet::Protocol *ethernet_handler;
  IPv4::Protocol *ipv4_handler;

public:
  void set_ethernet_handler(const std::unique_ptr<Ethernet::Protocol> &handler) {
    ethernet_handler = handler.get();
  }

  void set_ipv4_handler(const std::unique_ptr<IPv4::Protocol> &handler) {
    ipv4_handler = handler.get();
  }

  void handle_packet(const uint8_t *buffer, size_t buffer_len);

  void send(const Ethernet::Address &src_mac, const IPv4::Address &src_ip,
            const Ethernet::Address &dst_mac, const IPv4::Address &dst_ip);
};
} // namespace ARP
