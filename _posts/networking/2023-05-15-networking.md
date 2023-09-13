---
title: CIDR and Subnet Masks in Cloud Networking
date: 2023-05-15 21:58:47 +07:00
modified: 2023-05-15 21:58:47 +07:00
tags: [Cloud ☁️]
description: This article serves as an extensive resource for understanding CIDR and Subnet Masks, crucial components in cloud networking. It provides a detailed table to help in quick identification of available IP addresses per subnet.
comments: true
---

You do networking on Cloud like #Azure and you tried to remember CIDR, subnet mask to determine available addresses with no success ?

Here is THE solution:

| Subnet Mask     | CIDR | Binary Notation                     | Available Addresses Per Subnet |
| --------------- | ---- | ----------------------------------- | ------------------------------ |
| 255.255.255.255 | /32  | 11111111.11111111.11111111.11111111 | 1                              |
| 255.255.255.254 | /31  | 11111111.11111111.11111111.11111110 | 2                              |
| 255.255.255.252 | /30  | 11111111.11111111.11111111.11111100 | 4                              |
| 255.255.255.248 | /29  | 11111111.11111111.11111111.11111000 | 8                              |
| 255.255.255.240 | /28  | 11111111.11111111.11111111.11110000 | 16                             |
| 255.255.255.224 | /27  | 11111111.11111111.11111111.11100000 | 32                             |
| 255.255.255.192 | /26  | 11111111.11111111.11111111.11000000 | 64                             |
| 255.255.255.128 | /25  | 11111111.11111111.11111111.10000000 | 128                            |
| 255.255.255.0   | /24  | 11111111.11111111.11111111.00000000 | 256                            |
|                 |      |                                     |                                |
| 255.255.254.0   | /23  | 11111111.11111111.11111110.00000000 | 512                            |
| 255.255.252.0   | /22  | 11111111.11111111.11111100.00000000 | 1024                           |
| 255.255.248.0   | /21  | 11111111.11111111.11111000.00000000 | 2048                           |
| 255.255.240.0   | /20  | 11111111.11111111.11110000.00000000 | 4096                           |
| 255.255.224.0   | /19  | 11111111.11111111.11100000.00000000 | 8192                           |
| 255.255.192.0   | /18  | 11111111.11111111.11000000.00000000 | 16384                          |
| 255.255.128.0   | /17  | 11111111.11111111.10000000.00000000 | 32768                          |
| 255.255.0.0     | /16  | 11111111.11111111.00000000.00000000 | 65536                          |
|                 |      |                                     |                                |
| 255.254.0.0     | /15  | 11111111.11111110.00000000.00000000 | 131072                         |
| 255.252.0.0     | /14  | 11111111.11111100.00000000.00000000 | 262144                         |
| 255.248.0.0     | /13  | 11111111.11111000.00000000.00000000 | 524288                         |
| 255.240.0.0     | /12  | 11111111.11110000.00000000.00000000 | 1048576                        |
| 255.224.0.0     | /11  | 11111111.11100000.00000000.00000000 | 2097152                        |
| 255.192.0.0     | /10  | 11111111.11000000.00000000.00000000 | 4194304                        |
| 255.128.0.0     | /09  | 11111111.10000000.00000000.00000000 | 8388608                        |
| 255.0.0.0       | /08  | 11111111.00000000.00000000.00000000 | 16777216                       |
|                 |      |                                     |                                |
| 254.0.0.0       | /07  | 11111110.00000000.00000000.00000000 | 33554432                       |
| 252.0.0.0       | /06  | 11111100.00000000.00000000.00000000 | 67108864                       |
| 248.0.0.0       | /05  | 11111000.00000000.00000000.00000000 | 134217728                      |
| 240.0.0.0       | /04  | 11110000.00000000.00000000.00000000 | 268435456                      |
| 224.0.0.0       | /03  | 11100000.00000000.00000000.00000000 | 536870912                      |
| 192.0.0.0       | /02  | 11000000.00000000.00000000.00000000 | 1073741824                     |
| 128.0.0.0       | /01  | 10000000.00000000.00000000.00000000 | 2147483648                     |
| 0.0.0.0         | /00  | 00000000.00000000.00000000.00000000 | 4294967296                     |

# Why Understanding CIDR and Subnet Masks is Crucial ?

### For Resource Allocation

CIDR and subnet masks play a pivotal role in resource allocation. An improper CIDR block can lead to inadequate or wasteful distribution of IP addresses.

### For Security

Understanding these elements is also crucial for configuring firewalls and security groups, ensuring that only authorized traffic is allowed into your network.

### For Cost Optimization

Using CIDR and subnet masks effectively can lead to cost optimization, particularly in cloud environments where IP address allocation may incur additional charges.

# How to Use the Table ?
### Quick Reference

The table serves as a quick reference to find the number of available addresses for a given CIDR block or subnet mask.

### Planning Network Architecture

It can also be useful for planning your network architecture and deciding how to partition your IP address space.

# Summary

Understanding CIDR and subnet masks is critical for anyone involved in network planning, security, and resource allocation, particularly in cloud environments like Azure. This table should serve as a comprehensive guide for quick identification of available IP addresses per subnet, thus aiding in effective network management and optimization.
