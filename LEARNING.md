# Learnings: Build Your Own Async — David Beazley

> **Source**: [Build Your Own Async (PyCon India 2019)](https://www.youtube.com/watch?v=Y4Gt3Xjd7G8) — David Beazley  
> A live-coded workshop covering the foundations of asynchronous programming in Python — from first principles.

---

## Core Problem: Concurrency Without Threads

The starting point is two simple functions that count down and count up, each sleeping 1 second between steps.

```python
def countdown(n):
    while n > 0:
        print('Down', n)
        time.sleep(1)
        n -= 1

def countup(stop):
    x = 0
    while x < stop:
        print('Up', x)
        time.sleep(1)
        x += 1
```

Running them sequentially means `countup` cannot start until `countdown` finishes. The classic fix is **threads**:

```python
import threading
threading.Thread(target=countdown, args=(5,)).start()
threading.Thread(target=countup, args=(5,)).start()
```

**The challenge the tutorial sets**: achieve the same concurrent behaviour *without* threads.

---

## Chapter 1 — Why Threads Are Not Always the Answer

- Threads share memory and require locks for safety.
- They have OS-level overhead (stack allocation per thread, context switching).
- Debugging race conditions and deadlocks is notoriously difficult.
- The question becomes: **can we fake concurrency at the application level?**

---

## Chapter 2 — Callback-Based Scheduler

### Key Insight
Instead of blocking inside a function (e.g. `time.sleep(1)`), **schedule the next step** of the function to run later and yield control back to a central scheduler.

### Scheduler Design

```python
from collections import deque
import heapq, time

class Scheduler:
    def __init__(self):
        self.ready    = deque()   # tasks ready to run immediately
        self.sleeping = []        # tasks waiting for a future time (min-heap)

    def call_soon(self, func):
        self.ready.append(func)

    def call_later(self, delay, func):
        deadline = time.time() + delay
        heapq.heappush(self.sleeping, (deadline, func))

    def run(self):
        while self.ready or self.sleeping:
            if not self.ready:
                deadline, func = heapq.heappop(self.sleeping)
                delta = deadline - time.time()
                if delta > 0:
                    time.sleep(delta)          # only sleep the exact remaining delta
                self.ready.append(func)

            while self.ready:
                func = self.ready.popleft()
                func()
```

### How Functions Must Be Rewritten

Functions can no longer block; they must schedule their own "next step":

```python
def countdown(n):
    if n > 0:
        print('Down', n)
        sched.call_later(4, lambda: countdown(n - 1))

def countup(stop, x=0):
    if x < stop:
        print('Up', x)
        sched.call_later(1, lambda: countup(stop, x + 1))

sched.call_soon(lambda: countdown(5))
sched.call_soon(lambda: countup(20))
sched.run()
```

### Takeaways
| Concept | Detail |
|---|---|
| `ready` queue | `deque` — O(1) append/popleft for FIFO ordering |
| `sleeping` heap | `heapq` (min-heap by deadline) — efficiently finds the next wake-up time |
| No threads | The main thread runs the scheduler loop; tasks voluntarily hand control back |
| Downside | Every function must be refactored into continuation-passing style (callbacks), which hurts readability |

---

## Chapter 3 — Generator-Based Task Switching

### Key Insight
Python generators can be **paused and resumed** using `yield`. A scheduler can drive multiple generators by calling `next()` on each one in turn — this is cooperative multitasking.

```python
class Scheduler:
    def __init__(self):
        self.ready = deque()

    def new_task(self, gen):
        self.ready.append(gen)

    def run(self):
        while self.ready:
            self.current = self.ready.popleft()
            try:
                next(self.current)          # run until the next yield
                if self.current:
                    self.ready.append(self.current)   # re-queue for next turn
            except StopIteration:
                pass                        # generator exhausted — drop it
```

Functions become generators by adding `yield` at the cooperative handoff point:

```python
def countdown(n):
    while n > 0:
        print('Down', n)
        time.sleep(1)   # still blocking here — a remaining problem
        yield           # give the scheduler a chance to run something else
        n -= 1
```

### Takeaways
- `yield` is the voluntary preemption point — the function says "I'm done with this step, you can run someone else now".
- The scheduler calls `next()` to advance each generator by one step.
- **Limitation**: `time.sleep()` inside a generator still blocks the entire scheduler. To fix this, sleeping must also be handed off to the scheduler (combining with the callback approach from Chapter 2).

---

## Chapter 4 — Producer / Consumer with AsyncQueue

### Problem
How do you safely pass data between two concurrently-running tasks without threads or blocking I/O?

### The `Result` Wrapper

Callbacks must handle both success values and exceptions. A `Result` object unifies both:

```python
class Result:
    def __init__(self, value=None, exc=None):
        self.value = value
        self.exc   = exc

    def result(self):
        if self.exc:
            raise self.exc
        return self.value
```

### `QueueClosed` Signal

When a producer is done, it closes the queue. Consumers waiting on a closed, empty queue receive this exception:

```python
class QueueClosed(Exception):
    pass
```

### `AsyncQueue`

```python
class AsyncQueue:
    def __init__(self):
        self.items   = deque()
        self.waiting = deque()   # callbacks waiting for items
        self._closed = False

    def close(self):
        self._closed = True
        if self.waiting and not self.items:
            for func in self.waiting:
                sched.call_soon(func)   # wake up all blocked consumers

    def put(self, item):
        if self._closed:
            raise QueueClosed()
        self.items.append(item)
        if self.waiting:
            func = self.waiting.popleft()
            sched.call_soon(func)       # schedule via scheduler, NOT direct call

    def get(self, callback):
        if self.items:
            callback(Result(value=self.items.popleft()))
        else:
            if self._closed:
                callback(Result(exc=QueueClosed()))
            else:
                self.waiting.append(lambda: self.get(callback))
```

### Why `sched.call_soon(func)` Instead of `func()` Directly?

Calling `func()` directly from inside `put()` risks deep call stacks and unexpected re-entrancy. Routing through the scheduler keeps execution depth flat and predictable.

### Producer & Consumer

```python
def producer(q, count):
    def _run(n):
        if n < count:
            print('Producing', n)
            q.put(n)
            sched.call_later(1, lambda: _run(n + 1))
        else:
            q.close()
            print('Producing done')
    _run(0)

def consumer(q):
    def _consume(result):
        try:
            item = result.result()
            print('Consuming', item)
            sched.call_soon(lambda: consumer(q))
        except QueueClosed:
            print('Consumer done')
    q.get(callback=_consume)
```

### Takeaways
| Concept | Detail |
|---|---|
| `AsyncQueue` | Decouples producer and consumer timing without OS primitives |
| `waiting` deque | Holds callbacks that are blocked on an empty queue |
| `close()` | Signals end-of-stream; wakes blocked consumers with a `QueueClosed` result |
| Callback scheduling | Always go through the scheduler — never call callbacks directly to avoid stack blowup |

---

## Fundamental Concepts Illustrated

### Cooperative vs Preemptive Multitasking
| | Cooperative (this tutorial) | Preemptive (OS threads) |
|---|---|---|
| Who decides when to switch? | The task itself (`yield` / callback) | The OS scheduler |
| Shared data safety | Safer (no switching mid-expression) | Requires locks |
| Overhead | Very low | Stack per thread + context-switch |
| Risk | One task that never yields starves others | Race conditions |

### Event Loop Pattern
The `Scheduler.run()` loop is the simplest form of an **event loop**:
1. Pop the next ready task.
2. Execute it until it yields/returns.
3. Enqueue any newly scheduled tasks.
4. Repeat until nothing is left.

This is exactly the same pattern used by `asyncio`'s event loop internally.

### Callback Hell
The callback-based approach (Chapter 2) works but breaks normal control flow. Code becomes deeply nested and hard to reason about. This motivates the generator/coroutine approach.

### Generators as Coroutines
A generator function that uses `yield` to hand control back to a scheduler is a **coroutine** in spirit. Python formalised this with `async def` / `await` in Python 3.5, but the underlying mechanism is the same cooperative scheduling idea.

### `async`/`await` Is Syntactic Sugar
The `async def` / `await` syntax is essentially:
- `async def` → marks a function as a coroutine (generator)
- `await` → equivalent to `yield` in a coroutine — pause here and let the scheduler do something else

`asyncio` ships a production-ready event loop that handles I/O, timers, and tasks on top of these same primitives.

---

## Mental Model Summary

```
Task A          Task B          Scheduler
  |               |                 |
  |--call_soon--->|                 |
  |               |                 |
  |<--run()-------|-----------------|
  |               |                 |
  |--yield / callback               |
  |               |                 |
  |               |<--run()---------|
  |               |                 |
  |               |--yield / callback
  |               |                 |
  (repeat)
```

- Tasks give up control voluntarily.
- The scheduler decides what runs next.
- No OS threads required.

---

## Key Python Primitives Used

| Primitive | Purpose |
|---|---|
| `collections.deque` | O(1) FIFO queue for the ready list and waiting consumers |
| `heapq` | Min-heap to efficiently find the soonest sleeping task |
| `generator` / `yield` | Pause a function mid-execution and resume it later |
| `lambda` | Lightweight closures to capture state for callbacks |
| `Exception` subclass | `QueueClosed` — typed signal for end-of-stream |

---

## Relationship to `asyncio`

| This Tutorial | `asyncio` Equivalent |
|---|---|
| `Scheduler` | `asyncio.BaseEventLoop` |
| `call_soon(func)` | `loop.call_soon(callback)` |
| `call_later(delay, func)` | `loop.call_later(delay, callback)` |
| `AsyncQueue` | `asyncio.Queue` |
| `generator` + `yield` | `async def` + `await` |
| `Result` | `asyncio.Future` |
| `QueueClosed` exception | `asyncio.QueueEmpty` / sentinel values |

The tutorial deliberately builds these from scratch so you understand what `asyncio` is doing under the hood — it is not magic, just a well-structured event loop on top of Python generators.
