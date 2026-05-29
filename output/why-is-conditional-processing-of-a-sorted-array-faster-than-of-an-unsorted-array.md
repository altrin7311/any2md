---
title: "Why is conditional processing of a sorted array faster than of an unsorted array?"
source_url: "https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster-than-processing-an-unsorted-array"
source_type: stackoverflow
upload_date: 2012-06-27
extraction_date: 2026-05-29
author: "GManNickG"
score: 27530
tags: [branch prediction, sorting, optimization]
---

# Why is conditional processing of a sorted array faster than of an unsorted array?

> **Summary:** Conditional processing of a sorted array is faster than unsorted due to branch prediction. Modern compilers can optimize away branching and use conditional moves, which eliminate the penalty.

Key concepts: [[https://en.wikipedia.org/wiki/Branch_predictor]], [[https://gcc.gnu.org/onlinedocs/gcc-11.1.0/gcc/Branch-Prediction.html]]

## Question

In this C++ code, sorting the data (before the timed region) makes the primary loop ~6x faster:
#include 
#include 
#include 

int main()
{
    // Generate data
    const unsigned arraySize = 32768;
    int data[arraySize];

    for (unsigned c = 0; c = 128)
                sum += data[c];
        }
    }

    double elapsedTime = static_cast(clock()-start) / CLOCKS_PER_SEC;

    std::cout 

Without std::sort(data, data + arraySize);, the code runs in 11.54 seconds.
With the sorted data, the code runs in 1.93 seconds.

(Sorting itself takes more time than this one pass over the array, so it's not actually worth doing if we needed to calculate this for an unknown array.)

Initially, I thought this might be just a language or compiler anomaly, so I tried Java:
import java.util.Arrays;
import java.util.Random;

public class Main
{
    public static void main(String[] args)
    {
        // Generate data
        int arraySize = 32768;
        int data[] = new int[arraySize];

        Random rnd = new Random(0);
        for (int c = 0; c = 128)
                    sum += data[c];
            }
        }

        System.out.println((System.nanoTime() - start) / 1000000000.0);
        System.out.println("sum = " + sum);
    }
}

With a similar but less extreme result.

My first thought was that sorting brings the data into the cache, but that's silly because the array was just generated.

What is going on?
Why is processing a sorted array faster than processing an unsorted array?

The code is summing up some independent terms, so the order should not matter.

Related / follow-up Q&As with more modern C++ compilers

Why is processing an unsorted array the same speed as processing a sorted array with modern x86-64 clang? - modern C++ compilers auto-vectorize the loop, especially when SSE4.1 or AVX2 is available.  This avoids any data-dependent branching so performance isn't data-dependent.
gcc optimization flag -O3 makes code slower than -O2 - branchless scalar with cmov can result in a longer dependency chain (especially when GCC chooses poorly), creating a latency bottleneck that makes it slower than branchy asm for the sorted case.

## Answers


**Mysticial** (score: 35286) (accepted)

You are a victim of branch prediction fail.

What is Branch Prediction?

Consider a railroad junction:

Image by Mecanismo, via Wikimedia Commons. Used under the CC-By-SA 3.0 license.

Now for the sake of argument, suppose this is back in the 1800s - before long-distance or radio communication.

You are a blind operator of a junction and you hear a train coming. You have no idea which way it is supposed to go. You stop the train to ask the driver which direction they want. And then you set the switch appropriately.

Trains are heavy and have a lot of inertia, so they take forever to start up and slow down.

Is there a better way? You guess which direction the train will go!

If you guessed right, it continues on.
If you guessed wrong, the driver will stop, back up, and yell at you to flip the switch. Then it can restart down the other path.

If you guess right every time, the train will never have to stop.
If you guess wrong too often, the train will spend a lot of time stopping, backing up, and restarting.

Consider an if-statement: At the processor level, it is a branch instruction:

= 128) compiles into a jump-if-less-than processor instruction." />

You are a processor and you see a branch. You have no idea which way it will go. What do you do? You halt execution and wait until the previous instructions are complete. Then you continue down the correct path.

Modern processors are complicated and have long pipelines. This means they take forever to "warm up" and "slow down".

Is there a better way? You guess which direction the branch will go!

If you guessed right, you continue executing.
If you guessed wrong, you need to flush the pipeline and roll back to the branch. Then you can restart down the other path.

If you guess right every time, the execution will never have to stop.
If you guess wrong too often, you spend a lot of time stalling, rolling back, and restarting.

This is branch prediction. I admit it's not the best analogy since the train could just signal the direction with a flag. But in computers, the processor doesn't know which direction a branch will go until the last moment.

How would you strategically guess to minimize the number of times that the train must back up and go down the other path? You look at the past history! If the train goes left 99% of the time, then you guess left. If it alternates, then you alternate your guesses. If it goes one way every three times, you guess the same...

In other words, you try to identify a pattern and follow it. This is more or less how branch predictors work.

Most applications have well-behaved branches. Therefore, modern branch predictors will typically achieve >90% hit rates. But when faced with unpredictable branches with no recognizable patterns, branch predictors are virtually useless.

Further reading: "Branch predictor" article on Wikipedia.

As hinted from above, the culprit is this if-statement:
if (data[c] >= 128)
    sum += data[c];

Notice that the data is evenly distributed between 0 and 255. When the data is sorted, roughly the first half of the iterations will not enter the if-statement. After that, they will all enter the if-statement.

This is very friendly to the branch predictor since the branch consecutively goes the same direction many times. Even a simple saturating counter will correctly predict the branch except for the few iterations after it switches direction.

Quick visualization:
T = branch taken
N = branch not taken

data[] = 0, 1, 2, 3, 4, ... 126, 127, 128, 129, 130, ... 250, 251, 252, ...
branch = N  N  N  N  N  ...   N    N    T    T    T  ...   T    T    T  ...

       = NNNNNNNNNNNN ... NNNNNNNTTTTTTTTT ... TTTTTTTTTT  (easy to predict)

However, when the data is completely random, the branch predictor is rendered useless, because it can't predict random data. Thus there will probably be around 50% misprediction (no better than random guessing).
data[] = 226, 185, 125, 158, 198, 144, 217, 79, 202, 118,  14, 150, 177, 182, ...
branch =   T,   T,   N,   T,   T,   T,   T,  N,   T,   N,   N,   T,   T,   T  ...

       = TTNTTTTNTNNTTT ...   (completely random - impossible to predict)

What can be done?

If the compiler isn't able to optimize the branch into a conditional move, you can try some hacks if you are willing to sacrifice readability for performance.

Replace:
if (data[c] >= 128)
    sum += data[c];

with:
int t = (data[c] - 128) >> 31;
sum += ~t & data[c];

This eliminates the branch and replaces it with some bitwise operations.

(Note that this hack is not strictly equivalent to the original if-statement. But in this case, it's valid for all the input values of data[].)

Benchmarks: Core i7 920 @ 3.5 GHz

C++ - Visual Studio 2010 - x64 Release

Scenario
Time (seconds)

Branching - Random data
11.777

Branching - Sorted data
2.352

Branchless - Random data
2.564

Branchless - Sorted data
2.587

Java - NetBeans 7.1.1 JDK 7 - x64

Scenario
Time (seconds)

Branching - Random data
10.93293813

Branching - Sorted data
5.643797077

Branchless - Random data
3.113581453

Branchless - Sorted data
3.186068823

Observations:

With the Branch: There is a huge difference between the sorted and unsorted data.
With the Hack: There is no difference between sorted and unsorted data.
In the C++ case, the hack is actually a tad slower than with the branch when the data is sorted.

A general rule of thumb is to avoid data-dependent branching in critical loops (such as in this example).

Update:

GCC 4.6.1 with -O3 or -ftree-vectorize on x64 is able to generate a conditional move, so there is no difference between the sorted and unsorted data - both are fast.  This is called "if-conversion" (to branchless) and is necessary for vectorization but also sometimes good for scalar.

(Or somewhat fast: for the already-sorted case, cmov can be slower especially if GCC puts it on the critical path instead of just add, especially on Intel before Broadwell where cmov has 2-cycle latency: gcc optimization flag -O3 makes code slower than -O2)

VC++ 2010 is unable to generate conditional moves for this branch even under /Ox.

Intel C++ Compiler (ICC) 11 does something miraculous. It interchanges the two loops, thereby hoisting the unpredictable branch to the outer loop. Not only is it immune to the mispredictions, it's also twice as fast as whatever VC++ and GCC can generate! In other words, ICC took advantage of the test-loop to defeat the benchmark...

If you give the Intel compiler the branchless code, it just outright vectorizes it... and is just as fast as with the branch (with the loop interchange).

Clang also vectorizes the if() version, as will GCC 5 and later with -O3, even though it takes quite a few instructions to sign-extend to the 64-bit sum on x86 without SSE4 or AVX2.  (-march=x86-64-v2 or v3).  See Why is processing an unsorted array the same speed as processing a sorted array with modern x86-64 clang?

This goes to show that even mature modern compilers can vary wildly in their ability to optimize code...


**Daniel Fischer** (score: 4767)

Branch prediction.

With a sorted array, the condition data[c] >= 128 is first false for a streak of values, then becomes true for all later values. That's easy to predict. With an unsorted array, you pay for the branching cost.


**WiSaGaN** (score: 3859)

The reason why performance improves drastically when the data is sorted is that the branch prediction penalty is removed, as explained beautifully in Mysticial's answer.

Now, if we look at the code
if (data[c] >= 128)
    sum += data[c];

we can find that the meaning of this particular if... else... branch is to add something when a condition is satisfied. This type of branch can be easily transformed into a conditional move statement, which would be compiled into a conditional move instruction: cmovl, in an x86 system. The branch and thus the potential branch prediction penalty is removed.

In C, thus C++, the statement, which would compile directly (without any optimization) into the conditional move instruction in x86, is the ternary operator ... ? ... : .... So we rewrite the above statement into an equivalent one:
sum += data[c] >=128 ? data[c] : 0;

While maintaining readability, we can check the speedup factor.

On an Intel Core i7-2600K @ 3.4 GHz and Visual Studio 2010 Release Mode, the benchmark is:

x86

Scenario
Time (seconds)

Branching - Random data
8.885

Branching - Sorted data
1.528

Branchless - Random data
3.716

Branchless - Sorted data
3.71

x64

Scenario
Time (seconds)

Branching - Random data
11.302

Branching - Sorted data
1.830

Branchless - Random data
2.736

Branchless - Sorted data
2.737

The result is robust in multiple tests. We get a great speedup when the branch result is unpredictable, but we suffer a little bit when it is predictable. In fact, when using a conditional move, the performance is the same regardless of the data pattern.

Now let's look more closely by investigating the x86 assembly they generate. For simplicity, we use two functions max1 and max2.

max1 uses the conditional branch if... else ...:
int max1(int a, int b) {
    if (a > b)
        return a;
    else
        return b;
}

max2 uses the ternary operator ... ? ... : ...:
int max2(int a, int b) {
    return a > b ? a : b;
}

On an x86-64 machine, GCC -S generates the assembly below.
:max1
    movl    %edi, -4(%rbp)
    movl    %esi, -8(%rbp)
    movl    -4(%rbp), %eax
    cmpl    -8(%rbp), %eax
    jle     .L2
    movl    -4(%rbp), %eax
    movl    %eax, -12(%rbp)
    jmp     .L4
.L2:
    movl    -8(%rbp), %eax
    movl    %eax, -12(%rbp)
.L4:
    movl    -12(%rbp), %eax
    leave
    ret

:max2
    movl    %edi, -4(%rbp)
    movl    %esi, -8(%rbp)
    movl    -4(%rbp), %eax
    cmpl    %eax, -8(%rbp)
    cmovge  -8(%rbp), %eax
    leave
    ret

max2 uses much less code due to the usage of instruction cmovge. But the real gain is that max2 does not involve branch jumps, jmp, which would have a significant performance penalty if the predicted result is not right.

So why does a conditional move perform better?

In a typical x86 processor, the execution of an instruction is divided into several stages. Roughly, we have different hardware to deal with different stages. So we do not have to wait for one instruction to finish to start a new one. This is called pipelining.

In a branch case, the following instruction is determined by the preceding one, so we cannot do pipelining. We have to either wait or predict.

In a conditional move case, the execution of conditional move instruction is divided into several stages, but the earlier stages like Fetch and Decode do not depend on the result of the previous instruction; only the latter stages need the result. Thus, we wait a fraction of one instruction's execution time. This is why the conditional move version is slower than the branch when the prediction is easy.

The book Computer Systems: A Programmer's Perspective, second edition explains this in detail. You can check Section 3.6.6 for Conditional Move Instructions, entire Chapter 4 for Processor Architecture, and Section 5.11.2 for special treatment for Branch Prediction and Misprediction Penalties.

Sometimes, some modern compilers can optimize our code to assembly with better performance, and sometimes some compilers can't (the code in question is using Visual Studio's native compiler). Knowing the performance difference between a branch and a conditional move when unpredictable can help us write code with better performance when the scenario gets so complex that the compiler can not optimize them automatically.

