#include "icmp.h"
#include "../logging.h"
#include <cstring>

using namespace ICMP;

void Protocol::handle_packet(const Ethernet::Address &src_mac, const IPv4::Address &src_ip,
                             const IPv4::Address &dst_ip, const uint8_t *buffer,
                             size_t buffer_len) {
                        
  if (buffer_len < sizeof(Header)) return;

  auto *icmp = reinterpret_cast<const Header * > (buffer);

  if (icmp->type == ICMP_ECHO && icmp->code == 0)
  {
    log_icmp_ping();

    //preparing reply  (same size as request)
    std::vector<uint8_t> reply_buf(buffer_len);
    memcpy(reply_buf.data(), buffer, buffer_len);

    auto *reply = reinterpret_cast<Header *>(reply_buf.data());
    reply->type = ICMP_ECHOREPLY;
    reply->code = 0;
    reply->checksum = 0;

    // calc new checksum
    reply->checksum = IPv4::Protocol::checksum(reply_buf.data(), buffer_len); 

    log_icmp_pong();

    // send repli 
    send(reinterpret_cast<Frame *>(reply_buf.data()), buffer_len, src_mac, src_ip);
  }
}

void Protocol::send(const Frame *req_frame, size_t frame_len, const Ethernet::Address &dst_mac,
                    const IPv4::Address &dst_ip) {

  ipv4_handler->send(dst_mac, dst_ip, IPPROTO_ICMP, (uint8_t *)req_frame, frame_len);
}
