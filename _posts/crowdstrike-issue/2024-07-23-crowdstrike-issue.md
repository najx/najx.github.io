---
title: "Understand the great CrowdStrike-Windows meltdown"
date: 2024-07-23 07:19:15 +01:00
modified: 2024-07-23 07:19:15 +01:00
tags: [Code 👨‍💻]
description: On July 19, 2024, a single line of code in a Crowdstrike system driver caused half the world's Windows computers to crash. The issue arose from the driver accessing a reserved memory address (0x00) with system-level privileges, leading to a blue screen of death (BSOD) and forcing a restart. This incident disrupted critical systems in hospitals, railway stations, factories, and more, highlighting the importance of meticulous software testing and the potential widespread impact of minor coding errors.
comments: true
---

<figure>
<img src="/assets/img/1/3.jpg" alt="blue screen">
<figcaption>Blue Screens of Death in Indira Gandhi International Airport. Photo by Kabir Jhangiani / NurPhoto via Getty Images</figcaption>
</figure>

On July 19, 2024, a developer unintentionally caused half the world's Windows computers to crash with a single line of code. The incident left people worldwide puzzled and concerned, wondering how such a thing could happen. Here’s a detailed breakdown of the events and technicalities that led to this global disruption.

# The Culprit: Crowdstrike's System Driver

Crowdstrike, an American cybersecurity company, was at the heart of the problem. Their system driver, which had a critical flaw, was the source of the chaos.

### Understanding Computer Memory

To comprehend what went wrong, it's essential to understand how computer memory works. A computer primarily consists of a processor (CPU) and memory (RAM) to store and quickly access information. While the hard drive stores data long-term, the RAM is used for immediate tasks because of its speed.

### Memory Addressing

Memory addresses are a way to identify locations in RAM where data is stored. These addresses can be represented in hexadecimal (base 16). For example, if you have 1 byte of RAM, the addresses range from `0x00` to `0xFF`. With 4 gigabytes of RAM, addresses extend from `0x00000000` to `0xFFFFFFFF`, representing about 4.3 billion bytes.

### Reserved Addresses

Certain memory addresses are reserved for critical system functions. The first (0x00) and the last memory addresses are typically reserved by the operating system for loading essential libraries and the OS itself.

## The Critical Mistake: Null Pointer Dereferencing

In C++, developers often use 0x00 as a null address to indicate that a pointer does not point to any valid memory location. However, attempting to access this reserved address results in a system crash.

### Privilege Levels

Operating systems have different privilege levels to ensure security:

- **User Privilege:** If a user-level program tries to access the 0x00 address, Windows will terminate the program but continue running other processes normally.
- **System Privilege:** If a system-level program accesses the 0x00 address, Windows triggers a blue screen of death (BSOD) as a protective measure, requiring a restart.

## The Blue Screen Catastrophe

The program from Crowdstrike, running with system-level privileges, attempted to access the 156th address in RAM. This address falls well within the reserved range, leading to immediate system crashes (BSOD) across all affected machines.

## The Global Impact

On that fateful Friday, half of the Windows computers globally experienced sudden shutdowns, affecting:

- Hospital systems
- Railway station computers
- Factory control systems
- Other critical infrastructures

<figure>
<img src="/assets/img/1/2.jpg" alt="blue screen">
<figcaption>Blue screens at John F. Kennedy International Airport in New York.</figcaption>
</figure>

The cascading effect of this malfunction caused significant disruptions for businesses, governments, and individuals worldwide.

<figure>
<img src="/assets/img/1/1.jpg" alt="blue screen">
<figcaption>Unusable self-checkout terminals of a supermarket in Sydney, Australia. Photo by SAEED KHAN/AFP via Getty Images</figcaption>
</figure>

# Conclusion

The Crowdstrike incident is a stark reminder of the importance of rigorous software testing and the potential widespread impact of seemingly minor coding errors. By understanding the intricate details of how memory and privilege levels work, we can better appreciate the complexity and the critical need for caution in software development.

Now you know the full story behind one of the most significant computer disruptions in recent history.
