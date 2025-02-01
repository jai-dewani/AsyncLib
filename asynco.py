import time
from collections import deque
import heapq

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

def countdown(n):
    if n > 0:
        print('Down', n)
        # time.slee(4)          # Blocking call (nothing else can run)
        sched.call_later(4, lambda: countdown(n-1))


def countup(stop, x=0):
    if x < stop:
        print('Up', x)
        # time.slee(1)          # Blocking call (nothing else can run)
        sched.call_later(1, lambda: countup(stop, x+1))
        
sched.call_soon(lambda: countdown(5))
sched.call_soon(lambda: countup(20))
sched.run()

# Problem: How to achieve concurrency without threads? 
# Issue: Figure out how to switch between tasks.
