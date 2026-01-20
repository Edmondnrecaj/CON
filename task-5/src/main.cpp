#include "layer_link/ethernet.h"
#include "layer_internet/arp.h"
#include "layer_internet/ipv4.h"
#include "logging.h"

#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <memory>

#include <arpa/inet.h>     // inet_aton
#include <netinet/ether.h> // ether_aton_r
#include <pcap/pcap.h>

// Use unique_ptr as RAII wrapper for pcap types.
// https://dev.krzaq.cc/post/you-dont-need-a-stateful-deleter-in-your-unique_ptr-usually/
template <typename T, T *func> struct function_caller {
  template <typename... Us>
  auto operator()(Us &&... us) const -> decltype(func(std::forward<Us...>(us...))) {
    return func(std::forward<Us...>(us...));
  }
};
using pcap_file_ptr = std::unique_ptr<pcap_t, function_caller<void(pcap_t *), &pcap_close>>;
using pcap_dumper_ptr =
    std::unique_ptr<pcap_dumper_t, function_caller<void(pcap_dumper_t *), &pcap_dump_close>>;

pcap_dumper_ptr pcap_outfile_dump;
pcap_file_ptr pcap_device;

void send_bytes(char *buf, size_t bufsiz) {
  if (pcap_outfile_dump) {
    pcap_pkthdr pkthdr;
    memset(&pkthdr, 0, sizeof(pkthdr));
    pkthdr.caplen = bufsiz;
    pkthdr.len = bufsiz;
    pcap_dump((u_char *)pcap_outfile_dump.get(), &pkthdr, (u_char *)buf);
  } else if (pcap_device) {
    if (pcap_inject(pcap_device.get(), buf, bufsiz) == -1) {
      fprintf(stderr, "Could not send packet on this interface: %s\n",
              pcap_geterr(pcap_device.get()));
      exit(-1);
    }
  }
}

int main(int argc, char **argv) {
  char errbuf[PCAP_ERRBUF_SIZE];
  Ethernet::Address mac_addr;
  IPv4::Address ip_addr;
  ether_aton_r("00:00:00:00:00:00", (ether_addr *)&mac_addr);
  inet_aton("127.0.0.1", (in_addr *)&ip_addr);

  char *infile = nullptr;
  char *outfile = nullptr;
  char *dev = nullptr;
  bool respond = false;

  // parse arguments
  for (int i = 1; i < argc; i++) {
    int remaining = argc - i;
    if (strcmp("-i", argv[i]) == 0 && remaining > 1) {
      infile = argv[i + 1];
      i++;
    } else if (strcmp("-o", argv[i]) == 0 && remaining > 1) {
      outfile = argv[i + 1];
      i++;
    } else if (strcmp("-d", argv[i]) == 0 && remaining > 1) {
      dev = argv[i + 1];
      i++;
    } else if (strcmp("--respond", argv[i]) == 0 && remaining > 2) {
      ether_aton_r(argv[i + 1], (ether_addr *)&mac_addr);
      inet_aton(argv[i + 2], (in_addr *)&ip_addr);

      respond = true;
      i += 2;
    } else if (strcmp("--csv", argv[i]) == 0) {
      log_format = LOG_FORMAT_CSV;
    } else {
      fprintf(stderr, "Unknown or incomplete parameter: %s\n", argv[i]);
      exit(-1);
    }
  }

  if (!infile && !dev) {
    fprintf(stderr,
            "Usage: %s [-d <network device>] [-i <input file>] [--respond <mac "
            "address> <ip address>] [-o <output file>] [--csv]\n",
            argv[0]);
    exit(-1);
  }

  pcap_file_ptr pcap_infile;
  if (infile) {
    pcap_infile = pcap_file_ptr{pcap_open_offline(infile, errbuf)};
    if (!pcap_infile.get()) {
      fprintf(stderr, "Could not open input file: %s\n", errbuf);
      exit(-1);
    }
  }

  pcap_file_ptr pcap_outfile;
  if (outfile) {
    pcap_outfile = pcap_file_ptr{pcap_open_dead(1, 0)};
    if (!pcap_outfile.get()) {
      fprintf(stderr, "Opening fake pcap device failed: %s\n", errbuf);
      exit(-1);
    }
    pcap_outfile_dump = pcap_dumper_ptr{pcap_dump_open(pcap_outfile.get(), outfile)};
    if (!pcap_outfile_dump.get()) {
      fprintf(stderr, "Could not open output file: %s %s\n", outfile, errbuf);
      exit(-1);
    }
  }

  if (dev) {
    pcap_device = pcap_file_ptr{pcap_open_live(dev, BUFSIZ, 1, 1000, errbuf)};
    if (!pcap_device.get()) {
      fprintf(stderr, "Could not open device %s: %s\n", dev, errbuf);
      exit(-1);
    }
  }

  // Initialize the network stack
  auto ipv4 = std::make_unique<IPv4::Protocol>(ip_addr);
  auto arp = std::make_unique<ARP::Protocol>();
  auto ethernet =
      std::make_unique<Ethernet::Protocol>(mac_addr, ipv4, arp, respond ? send_bytes : nullptr);

  arp->set_ethernet_handler(ethernet);
  arp->set_ipv4_handler(ipv4);
  ipv4->set_ethernet_handler(ethernet);

  auto handle_bytes = [](u_char *user, const struct pcap_pkthdr *h, const u_char *bytes) {
    auto layer2 = reinterpret_cast<Ethernet::Protocol *>(user);
    layer2->handle_packet(bytes, h->len);
  };

  // call handle_bytes for all frames from the input source
  pcap_t *pcap_input_handle = infile ? pcap_infile.get() : pcap_device.get();
  if (pcap_loop(pcap_input_handle, 0, handle_bytes, (u_char *)ethernet.get()) < 0) {
    fprintf(stderr, "pcap_loop() failed: %s\n", pcap_geterr(pcap_input_handle));
  }
  return 0;
}
