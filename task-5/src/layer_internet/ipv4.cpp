#include "ipv4.h"
#include "../layer_link/ethernet.h"
#include "../icmp/icmp.h"
#include "../logging.h"

#include <algorithm>
#include <cstring>

using namespace IPv4;

Protocol::Protocol(const Address &address) : ipAddress(address) {
  icmp_handler = std::make_unique<ICMP::Protocol>(this);
}

void Protocol::handle_packet(const Ethernet::Address &src_mac, const uint8_t *buffer,
                             size_t buffer_len) {
                              
  if (buffer_len < sizeof(Header))  return;

  auto *ip = reinterpret_cast<const Header *>(buffer);

  if (ip->ip_v != 4) return;

  Address src_ip = ip->ip_src; 
  Address dst_ip = ip->ip_dst;

  log_ip_packet(&src_ip, &dst_ip);

  // only mine
  if (!isOwnIpAddress(dst_ip)) return;

  // only ICMP  
  if (ip->ip_p != IPPROTO_ICMP) return;

  uint32_t header_len = ip->ip_hl * 4;
  if (header_len > buffer_len) return;

  const uint8_t *icmp_start = buffer + header_len;
  size_t icmp_len = buffer_len - header_len;

  icmp_handler->handle_packet(src_mac, src_ip, dst_ip, icmp_start, icmp_len); 

}

void Protocol::send(const Ethernet::Address &dst_mac, const IPv4::Address &dst_ip,
                    const uint16_t protocol, uint8_t *payload, size_t payload_len) {

  size_t ip_header_len = sizeof(Header);
  size_t total_len = ip_header_len + payload_len;

  std::vector<uint8_t> packet(total_len);
  auto *ip = reinterpret_cast<Header *>(packet.data());

  memset(ip, 0, ip_header_len);

  ip->ip_v = 4;
  ip->ip_hl = 5;
  ip->ip_tos = 0;
  ip->ip_len = htons(total_len);
  ip->ip_id  = 0;
  ip->ip_off = 0;
  ip->ip_ttl = 64;
  ip->ip_p = protocol;
  ip->ip_src  = ipAddress;
  ip->ip_dst = dst_ip;

  ip->ip_sum = 0;
  ip->ip_sum = checksum(ip, ip_header_len);

  memcpy(packet.data() + ip_header_len, payload, payload_len);

  log_ip_packet(&ipAddress, &dst_ip);

  ethernet_handler->send(dst_mac, Ethernet::TYPE_IP, packet.data(), packet.size());
}
