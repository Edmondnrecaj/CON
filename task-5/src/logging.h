#pragma once
#include "layer_link/ethernet.h" // Ethernet::Address
#include "layer_internet/ipv4.h"     // IPv4::Address

#include <cstddef> // size_t

#define LOG_FORMAT_HUMAN_READABLE 0
#define LOG_FORMAT_CSV 1
extern size_t log_format;

// Ethernet
void log_ethernet_frame(const Ethernet::Address *src, const Ethernet::Address *dst);

// IP
void log_ip_packet(const IPv4::Address *src, const IPv4::Address *dst);

// ARP
void log_arp_request(const Ethernet::Address *src_mac, const IPv4::Address *src_ip,
                     const Ethernet::Address *dst_mac, const IPv4::Address *dst_ip);
void log_arp_reply(const Ethernet::Address *src_mac, const IPv4::Address *src_ip,
                   const Ethernet::Address *dst_mac, const IPv4::Address *dst_ip);
// ICMP
void log_icmp_ping();
void log_icmp_pong();

// HTTP
void log_http_response(const char *status_code);
void log_http_request(const char *request_method, const char *resource_path);
void log_http_request_host(const char *host);
void log_http_request_cookie(const char *cookie);
void log_http_request_auth(const char *decoded_login_data);
