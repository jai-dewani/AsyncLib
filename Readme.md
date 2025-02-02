This is an attempt to create your own async library - in Python. The original video can be found here - [Build Your Own Async - David Beazley](https://youtu.be/Y4Gt3Xjd7G8?si=M0kjCvr0LoBbyhVt)

## Chapter 1 - Introduction
Assume you have two functions - `coutdown` and `countup`. Both count down and up respectively with a setup of 1 second break. If we run these two functions like 
```
coutdown(5)
coutup(5)
```
This results in sequential execution. How can we move them to concurrent execution phase? 

The most classing solution would be to use threads. 
```
import threading 
threading.Thread(target=countdown, args=(5,)).start()
threading.Thread(target=countup, args=(5,)).start()
```

## Chapter 2 - Scheduler
Now let's try to do what we did earlier but without threads. 

This problem can be attempted by creating a list of functions that are ready to be execute, and a Scheduler which can start executing them when the main thread is free. But to make this work, the functions need to be rewritten to use the scheduler's APIs for looping or queuing the next step of processing.

## Chapter 3 - Producer/Consumer


## Chapter 4 