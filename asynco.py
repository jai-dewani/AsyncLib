import time
from collections import deque


class Scheduler: 
    def __init__(self):
        self.ready = deque()        # Functions ready to execute
        self.sleeping = []          # Sleeping functions 

    def call_soon(self, func):
        self.ready.append(func)

    def call_later(self, delay, func):
        deadline = time.time() + delay
        self.sleeping.append((deadline,func))
        self.sleeping.sort()

    def run(self):
        while self.ready or self.sleeping: 
            if not self.ready: 
                # Find the nearest deadline 
                deadline, func = self.sleeping.pop(0)
                delta = deadline - time.time()
                if delta > 0:
                    time.sleep(delta)
                self.ready.append(fund)

            while self.ready: 
                func = self.ready.popleft()
                func()

sched = Scheduler()

def countdown(n):
    if n > 0:
        print('Down', n)
        time.sleep(1)
        sched.call_soon(4, lambda: countdown(n-1))


def countup(stop, x=0):
    if x < stop:
        print('Up', x)
        time.sleep(1)
        sched.call_soon(1, lambda: countup(stop, x+1))

# Problem: How to achieve concurrency without threads? 
# Issue: Figure out how to switch between tasks.
sched.call_soon(lambda: countdown(5))
sched.call_soon(lambda: countup(5))
sched.run()