#include "logging.h"

#include <cstdio>

#include <arpa/inet.h>     // inet_ntop
#include <netinet/ether.h> // ether_ntoa

#define ETHERNET_ADDRSTRLEN 18

size_t log_format = 0;

// clang-format off
static const char *LOG_FORMATS[2][12] = {
  {"\n[ETHERNET] frame  %s -> %s\n",
   "[IPv4    ] packet %s -> %s\n",
   "[TCP     ] segment port: %u -> %u, seq: %u, ack: %u, flags: [%s %s %s]\n",
   "[ARP     ] request: who has %s tell %s (%s)\n",
   "[ARP     ] reply: %s is at %s\n",
   "[ICMP    ] PING",
   "[ICMP    ] PONG",
   "[HTTP    ] Response: code %s\n",
   "[HTTP    ] Request: %s %s\n",
   "[HTTP    ] Host: %s\n",
   "[HTTP    ] Cookie: %s\n",
   "[HTTP    ] Basic Auth (decoded): %s\n"},
  {"ETHERNET;%s;%s\n",
   "IPv4;%s;%s\n",
   "TCP;%u;%u;%u,%u;%s;%s;%s\n",
   "ARP;request;%s;%s;%s\n",
   "ARP;reply;%s;%s\n",
   "ICMP;PING",
   "ICMP;PONG",
   "HTTP;response;%s\n",
   "HTTP;request;%s;%s\n",
   "HTTP;Host;%s\n",
   "HTTP;Cookie;%s\n",
   "HTTP;Basic Auth;%s\n"}
};
// clang-format on

static char *ether_ntoa_r_custom(const Ethernet::Address *addr, char *buf) {
  sprintf(buf, "%02x:%02x:%02x:%02x:%02x:%02x", addr->ether_addr_octet[0],
          addr->ether_addr_octet[1], addr->ether_addr_octet[2], addr->ether_addr_octet[3],
          addr->ether_addr_octet[4], addr->ether_addr_octet[5]);
  return buf;
}

void log_ethernet_frame(const Ethernet::Address *src, const Ethernet::Address *dest) {
  char src_str[ETHERNET_ADDRSTRLEN];
  char dest_str[ETHERNET_ADDRSTRLEN];
  ether_ntoa_r_custom(src, src_str);
  ether_ntoa_r_custom(dest, dest_str);
  printf(LOG_FORMATS[log_format][0], src_str, dest_str);
}

void log_ip_packet(const IPv4::Address *src, const IPv4::Address *dest) {
  char src_str[INET_ADDRSTRLEN];
  char dest_str[INET_ADDRSTRLEN];
  inet_ntop(AF_INET, src, src_str, INET_ADDRSTRLEN);
  inet_ntop(AF_INET, dest, dest_str, INET_ADDRSTRLEN);
  printf(LOG_FORMATS[log_format][1], src_str, dest_str);
}

void log_arp_request(const Ethernet::Address *src_mac, const IPv4::Address *src_ip,
                     const Ethernet::Address * /*dest_mac*/, const IPv4::Address *dest_ip) {
  char src_str[INET_ADDRSTRLEN];
  char dest_str[INET_ADDRSTRLEN];
  inet_ntop(AF_INET, src_ip, src_str, INET_ADDRSTRLEN);
  inet_ntop(AF_INET, dest_ip, dest_str, INET_ADDRSTRLEN);
  printf(LOG_FORMATS[log_format][3], dest_str, src_str, ether_ntoa((ether_addr *)src_mac));
}

void log_arp_reply(const Ethernet::Address *src_mac, const IPv4::Address *src_ip,
                   const Ethernet::Address * /*dest_mac*/, const IPv4::Address * /*dest_ip*/) {
  char src_str[INET_ADDRSTRLEN];
  inet_ntop(AF_INET, src_ip, src_str, INET_ADDRSTRLEN);
  printf(LOG_FORMATS[log_format][4], src_str, ether_ntoa((ether_addr *)src_mac));
}

void log_icmp_ping() { puts(LOG_FORMATS[log_format][5]); }

void log_icmp_pong() { puts(LOG_FORMATS[log_format][6]); }

void log_http_response(const char *status_code) { printf(LOG_FORMATS[log_format][7], status_code); }

void log_http_request(const char *request_method, const char *resource_path) {
  printf(LOG_FORMATS[log_format][8], request_method, resource_path);
}

void log_http_request_host(const char *host) { printf(LOG_FORMATS[log_format][9], host); }

void log_http_request_cookie(const char *cookie) { printf(LOG_FORMATS[log_format][10], cookie); }

void log_http_request_auth(const char *decoded_login_data) {
  printf(LOG_FORMATS[log_format][11], decoded_login_data);
}
