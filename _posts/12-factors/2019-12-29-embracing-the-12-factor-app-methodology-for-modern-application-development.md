---
title: Embracing the 12-Factor App Methodology for Modern Application Development
date: 2019-12-29 11:58:47 +07:00
modified: 2023-07-23 11:58:47 +07:00
tags: [DevOps]
description: As the digital landscape continually evolves, developers are constantly tasked with creating applications that are scalable, maintainable, and capable of standing up to a diverse range of operational scenarios. This is where the 12-Factor App methodology comes into play.
---

As the digital landscape continually evolves, developers are constantly tasked with creating applications that are scalable, maintainable, and capable of standing up to a diverse range of operational scenarios. This is where the 12-Factor App methodology comes into play. Created by engineers at Heroku, this framework provides developers with a set of best practices aimed at building software-as-a-service apps that are both scalable and maintainable.

<figure>
<img src="/12-factors/12factors.png" alt="12 factors for your factory" style="width:50%;height:50%;">
</figure>

## The 12 Factors :

**1. Codebase:** One codebase tracked in version control, with many deploys. Each application should have its codebase that can be tracked in a version control system. It can have multiple deployments, including the staging and production environments, but they all share the same base code.

**2. Dependencies:** Explicitly declare and isolate dependencies. Your application should never assume the existence of system-wide packages. It should declare all dependencies explicitly using a dependency declaration manifest.

**3. Config:** Store configuration in the environment. Configuration options should always be separated from the application itself, ideally using environment variables.

**4. Backing services:** Treat backing services as attached resources. From the perspective of the application, all services it consumes (database, messaging system, caching system) should be treated as attached resources, accessed via an addressable URL.

**5. Build, release, run:** Strictly separate build and run stages. The build stage converts code into an executable bundle, the release stage combines the build with the current configuration, and the run stage (also called runtime) executes the application in the execution environment.

**6. Processes:** Execute the app as one or more stateless processes. The application should strive for statelessness and share-nothing architecture.

**7. Port binding:** The app is completely self-contained. It should not rely on runtime injection of a webserver into the execution environment to create a web-facing service.

**8. Concurrency:** Scale out via the process model. The app should be able to scale out according to the process model - in the case of a web app, that could be by spawning more processes.

**9. Disposability:** Maximize robustness with fast startup and graceful shutdown. The faster your application starts and stops, the more robust and resilient it can be.

**10. Dev/prod parity:** Keep development, staging, and production as similar as possible. This minimizes the number of bugs and issues that arise due to differences between the environments.

**11. Logs:** Treat logs as event streams. Instead of managing log files, your application should treat logs as event streams and output them to stdout.

**12. Admin processes:** Run admin/management tasks as one-off processes. These should be run in an identical environment as the regular long-running processes of the app.
The Takeaway

While the 12-Factor App methodology isn't a silver bullet for all software development challenges, it serves as an excellent guide for building applications that can thrive in the modern era of software as a service. Adopting these principles can significantly enhance your app's maintainability, scalability, and resilience, helping you meet both current and future development challenges head-on.

Remember, the key to a successful application lies not just in its functionality, but also in its ability to perform consistently and reliably under various conditions, and the 12-Factor App methodology provides a tried and tested framework for achieving this. Whether you're a seasoned developer or new to the field, it's worth taking the time to familiarize yourself with these principles and incorporate them into your development practices.

---

## Reference

- [12factors's website](https://12factor.net/)