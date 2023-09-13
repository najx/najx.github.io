---
title: A Study Reveals the Most Energy-hungry Programming Languages
date: 2023-06-16 11:58:47 +07:00
modified: 2023-06-16 11:58:47 +07:00
tags: [Code 👨‍💻, Eco 🌱]
description: Which programming languages consume the least energy? This is the question that six researchers from three Portuguese universities sought to answer in a study titled "Energy Efficiency Across Programming Languages". In their research, they examined execution time, memory usage, and most importantly, the energy consumption of 27 well-known programming languages.
comments: true
---

<figure>
<img src="/assets/img/1/blindgridmakerimage.jpg" alt="">
<figcaption></figcaption>
</figure>

**Which programming languages consume the least energy?** This is the question that six researchers from three Portuguese universities sought to answer in a study titled "Energy Efficiency Across Programming Languages". In their research, they examined execution time, memory usage, and most importantly, the energy consumption of 27 well-known programming languages.

The primary goal of their efforts was to understand energy efficiency across various programming languages. This might seem like a straightforward task, but it's not as trivial as it might appear. Indeed, to properly compare energy efficiency across different languages, one needs to secure comparable implementations of solutions to a representative set of problems.

# First, the methodology

To gather a set of comparable, representative, and comprehensive programs written in most of the popular and widely-used programming languages, the researchers turned to the Computer Language Benchmarks Game (CLBG). The CLBG initiative provides a framework to run, test, and compare consistent solutions implemented for a set of well-known and varied programming problems. Its aim is to allow those who wish to compare solutions, whether within the same language or across different programming languages. At the time of their research, the CLBG offered solutions for 13 benchmark problems, ensuring that the solutions to each of these problems adhere to a given algorithm and specific implementation guidelines. Solutions to each problem are expressed in up to 28 different programming languages.

<figure>
<img src="/assets/img/1/tble02.png" alt="">
<figcaption></figcaption>
</figure>


Of the 28 languages considered in the CLBG, the researchers excluded Smalltalk because the compiler for this language is proprietary. Additionally, for comparability reasons, they ruled out problems that had a language coverage lower than 80%. The language coverage of a problem is the percentage of programming languages (out of the 27) in which solutions are available for that problem. This criterion led to the exclusion of three problems from the study.

For each of the remaining 10 problems, researchers then selected the most efficient source code version (i.e., the fastest) for the 27 programming languages under consideration. The CLBG documentation also provides information on the specific version of the compiler/runner used for each language, as well as on the considered compilation/execution options. The researchers claimed to have "strictly followed these instructions," ensuring that they installed the correct compiler versions and also made sure that each solution was compiled/executed with the same options as those used in the CLBG.

They also tested each chosen solution to ensure that they could run it error-free and that the obtained result was the expected one. The next step was to gather information on energy consumption, execution time, and peak memory usage for each of the compilable and executable solutions in each language.

It's worth noting that the CLBG already has measured information on both execution time and peak memory usage. The researchers measured both not only to verify the consistency of their results compared to the CLBG's but also because different hardware specifications would yield different results.

To measure energy consumption, they utilized Intel's RAPL (Running Average Power Limit) tool, capable of providing very accurate energy estimates, as has been evidenced in various studies. Each solution was executed 10 times, and associated performance was measured "to reduce the impact of cold starts and cache effects, analyze measurement consistency, and avoid outlier values." They report that "measured results are fairly consistent." For further consistency, all tests were carried out on a desktop computer running Linux Ubuntu Server 16.10, with 16GB of RAM and an Intel Core i5-4460 processor clocked at 3.20 GHz.

After taking all these precautions to ensure relevant results, what did the researchers' findings reveal?

# Now, the results of the study:

## Which are the best languages by criterion?

The table below presents the overall results (on average) for energy consumption (Energy), execution time (Time), and peak memory usage (Mb), all normalized relative to the most efficient language for the measured criterion. The first column lists the names of the programming languages, prefixed by the letters (c), (i), or (v), indicating respectively whether the language is compiled, interpreted, or is a virtual machine language. For example, in terms of energy consumed, we see that C has a value of 1.00, while Lisp has a value of 2.27. This essentially means that C is the language that consumes the least energy, and Lisp consumes 2.27 times more energy than C.

<figure>
<img src="/assets/img/1/tble04.png" alt="">
<figcaption></figcaption>
</figure>

The top 5 languages that consume the least energy are **C (1.00)**, **Rust (1.03)**, **C++ (1.34)**, **Ada (1.70)**, and **Java (1.98)**. On the opposite end, the most energy-hungry languages are **Perl (79.58)**, **Python (75.88)**, **Ruby (69.91)**, **Jruby (46.54)**, and **Lua (45.98)**.

In terms of language speed, the top 5 remain unchanged: C, Rust, C++, Ada, and Java. So, are the fastest languages also those that consume the least energy? The researchers address this in their study, but we can already see that this isn't perfectly the case, although there seems to be a strong correlation. Among the slowest languages, Lua, Ruby, Perl, and Python again make the top 5, with TypeScript joining them this time.

Moving on to the languages that consume the least memory, the gold medal goes to **Pascal (1.00)**, followed by **Go (1.05)**, **C (1.17)**, **Fortran (1.24)**, and **C++ (1.34)** to round out the top 5. This time, Python (2.80) climbs to the first half of the rankings, while Perl (6.26) is again among the 5 worst languages.

# Which are the best languages when combining multiple criteria?

The table below presents four rankings by combining various goals: execution time and memory used, energy consumed and execution time, energy consumed and memory used, and finally all three criteria simultaneously. For each ranking, each row represents an optimal Pareto set, meaning a set of languages that are "equivalent" from the combined criteria perspective. The order of each row also represents the rank of the languages in the associated ranking.

<figure>
<img src="/assets/img/1/tble05.png" alt="">
<figcaption></figcaption>
</figure>

Some applications require considering two factors - for instance, energy consumption and execution time. In this case, as the table above shows, "the C language is the best solution as it dominates in both objectives," the researchers wrote. If you're trying to save time by using less memory, C, Pascal, and Go "are equivalent" and are the top choices. The same is true if you look at all three criteria (execution time, energy consumption, and memory use). But if you simply want to save energy while using less memory, the best possible choices are C or Pascal.

The researchers also compared the results of compiled and interpreted languages (with a separate category for languages executed on virtual machines). Their study also includes a comparison of various programming paradigms: functional, imperative, object-oriented, and scripting.

# Compiled Languages VS Interpreted Languages VS Languages Executed on Virtual Machines

As shown in the first table, the study reveals that "compiled languages tend to be faster and more energy-efficient. On average, compiled languages consumed 120 J to run solutions, whereas for virtual machine and interpreted languages, their average consumptions were 576 J and 2365 J, respectively."

This trend can also be observed in execution time. "Compiled languages took an average of 5103 ms, virtual machine languages, 20,623 ms, and interpreted languages, 87,614 ms." Moreover, as previously pointed out, "the top 5 languages requiring the least energy and time to execute solutions are: C, Rust, C++, Ada, and Java; among these, only Java is not compiled."

Also, the five slowest languages are all interpreted: Lua, Python, Perl, Ruby, and Typescript. And the five most energy-consuming languages are also interpreted: Perl, Python, Ruby, JRuby, and Lua. However, the researchers note that at the same time, when it comes to handling strings with a regular expression, three of the five most energy-efficient languages turn out to be interpreted languages (TypeScript, JavaScript, and PHP), "though they tend not to be very energy efficient in other scenarios."

Compiled languages also took the top five spots in the ranking of languages that use the least memory space. "On average, compiled languages needed 125 MB, virtual machine languages, 285 MB, and interpreted languages, 426 MB," the researchers pointed out. Interpreted languages like JRuby, Dart, Lua, and Perl occupied four of the bottom five spots, meaning they generally use more memory space.

# Comparison of Programming Paradigms

When comparing different paradigms, imperative programming is often the best solution. Languages in this group used far less energy on average - and executed much faster - than object-oriented, functional, and scripting languages. "On average, imperative languages consumed 125 J and took 5585 ms, object-oriented languages consumed 879 J and took 32,965 ms, functional languages consumed 1367 J and took 42,740 ms, and scripting languages consumed 2320 J and took 88,322 ms," the researchers stated. "For memory usage, imperative languages required 116 MB, 249 MB for object-oriented languages, 251 MB for functional languages, and 421 MB for scripting languages."

# Are the Fastest Languages the Greenest?

Researchers closely examined the common assumption that a faster program always consumes less energy and stressed that here it's not as straightforward as in physics where it's believed that a device's energy consumption is the product of operating time and power. The researchers believe that this assumes power is consistent over time, yet a language's energy consumption is affected by many factors (including the quality of the compiler and libraries used). Thus, as their results also demonstrate, they assert that a "faster language is not always more energy-efficient."

It's true that "the top five most energy-efficient languages maintain their position when ranked by execution time and with very small differences between energy consumption and execution time scores," but the same observation is not made when considering all languages. Indeed, "only four languages maintain the same rank for energy consumption and execution time (OCaml, Haskell, Racket, and Python), while the others are completely shuffled," the researchers observed.

<hr>

<p>
    <ul style="font-size: 12px;">
        <li><em>Source: <a href="https://greenlab.di.uminho.pt/wp-content/uploads/2017/10/sleFinal.pdf">Study Report</a></em></li>
        <li><em>Credit to: <a href="https://programmation.developpez.com/actu/253829/Programmation-une-etude-revele-les-langages-les-plus-voraces-en-energie-Perl-Python-et-Ruby-en-tete-C-Rust-et-Cplusplus-les-langages-les-plus-verts/">Michael Guilloux - Developpez.com</a></em></li>
    </ul>
</p>
