#include "arp.h"
#include "../layer_link/ethernet.h"
#include "../layer_internet/ipv4.h"
#include "../logging.h"

#define ARPPRO_IP 2048

using namespace ARP;

void Protocol::handle_packet(const uint8_t *buffer, size_t buffer_len) {
  
if (buffer_len < sizeof(Packet)) return;

    auto *arp = reinterpret_cast<const Packet * >(buffer);

    if (ntohs(arp->hdr.ar_hrd) != ARPHRD_ETHER) return;
    if (ntohs(arp->hdr.ar_pro) != ARPPRO_IP) return;

    if (ntohs(arp->hdr.ar_op) == ARPOP_REQUEST)
    {
        // log every request 
        log_arp_request(&arp->src_mac, &arp->src_ip, &arp->dst_mac, &arp->dst_ip);

        // check if for me
        if (ipv4_handler->isOwnIpAddress(arp->dst_ip))
        {
            send(ethernet_handler->mac, arp->dst_ip, arp->src_mac, arp->src_ip);
        }
    }
}

void Protocol::send(const Ethernet::Address &src_mac, const IPv4::Address &src_ip,
                    const Ethernet::Address &dst_mac, const IPv4::Address &dst_ip) {
                        
  Packet reply;

  reply.hdr.ar_hrd = htons(ARPHRD_ETHER);
  reply.hdr.ar_pro = htons(ARPPRO_IP);
  reply.hdr.ar_hln = ETH_ALEN;
  reply.hdr.ar_pln = 4;
  reply.hdr.ar_op = htons(ARPOP_REPLY);

  reply.src_mac  = src_mac;
  reply.src_ip = src_ip;  
  reply.dst_mac = dst_mac;
  reply.dst_ip = dst_ip;

  log_arp_reply(&src_mac, &src_ip, &dst_mac, &dst_ip);

  ethernet_handler->send(dst_mac, ETHERTYPE_ARP, (uint8_t *)&reply, sizeof(Packet));
}
