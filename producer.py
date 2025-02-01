
# Producer-consumer problem
# Challenge : How to implement the same functionality, but no threads.

import queue 
import threading
import time 
import heapq
from collections import deque

class Scheduler: 
    def __init__(self):
        self.ready = deque()        # Functions ready to execute
        self.sleeping = []          # Sleeping functions 

    def call_soon(self, func):
        self.ready.append(func)

    def call_later(self, delay, func):
        deadline = time.time() + delay
        heapq.heappush(self.sleeping, (deadline, func))

    def run(self):
        while self.ready or self.sleeping: 
            if not self.ready: 
                # Find the nearest deadline 
                deadline, func = heapq.heappop(self.sleeping)
                delta = deadline - time.time()
                if delta > 0:
                    time.sleep(delta)
                self.ready.append(func)

            while self.ready: 
                func = self.ready.popleft()
                func()

sched = Scheduler()

class Result: 
    def __init__(self, value=None, exc=None):
        self.value = value 
        self.exc = exc 

    def result(self):
        if self.exc:
            raise self.exc
        return self.value

class QueueClosed(Exception):
    pass

class AsyncQueue: 
    def __init__(self):
        self.items = deque()
        self.waiting = deque()      # All getters waiting for data
        self._closed = False        # Can queue be used anymore? 
    
    
    def close(self):
        self._closed = True

    def put(self, item):
        if self._closed:
            raise QueueClosed()
        
        self.items.append(item)
        if self.waiting:
            func = self.waiting.popleft()
            # Do we call it right away? 
            # No, let's rely on a scheduler to avoid scenarios like 
            # func() ---> might get deep calls, recursion, etc
            sched.call_soon(func)

    def get(self, callback):
        # Wait until an item is available. Then return it 
        # Queuestion: How does a closed queue interact with get()
        if self.items:
            callback(Result(value=self.items.popleft()))
        else:
            # No items available (must wait)
            if self._closed:
                callback(Result(exc=QueueClosed()))             # Error results
            self.waiting.append(lambda: self.get(callback))

def producer(q, count): 
    def _run(n):
        if n < count: 
            print('Producing', n)
            q.put(n)
            sched.call_later(1, lambda: _run(n+1))
        else:
            q.close()           # Means no more items will be produced
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

q = AsyncQueue()
sched.call_soon(lambda: producer(q, 10))
sched.call_soon(lambda: consumer(q))
sched.run()