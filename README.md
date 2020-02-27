# taro
Job management library

## Feature priority
### Mandatory
1. ~~Logging - normal to stdout and errors to stderr (https://docs.python.org/3/library/logging.handlers.html)~~
2. ~~(Config)~~
3. ~~Current executing jobs~~
4. Stop, interrupt, kill
5. Progress of currently executing jobs
6. SNS notifications
7. Execution history
8. Log rotation

### Optional
- job timeout
- job post checks

## Premature termination
### General
A process can be terminated either by stop or interrupt operations.
When a process is stopped its termination (final) state is set to STOPPED.
When a process is interrupted its termination (final) state is set to INTERRUPTED which is a failure state.
Choosing one of these options a user can decided whether the termination is a failure or not.

### Exec command
A child process executed with `exec` command is stopped or interrupted by sending kill signal.
Received SIGTERM (normal kill) or SIGINT (Ctrl+C) signals trigger interrupt operation.
It is expected for terminated child process to stop executing otherwise this process will continue waiting for the child.

## Implementation notes

### Termination / Signals
#### SIGTERM handler
Python does not register a handler for the SIGTERM signal. That means that the system will take the default action.
On linux, the default action for a SIGTERM is to terminate the process:
 - the process will simply not be allocated any more time slices during which it can execute code
 - the process's memory and other resources (open files, network sockets, etc...) will be released back to the rest of the system

#### sys.exit()
Signal handler suspends current execution in the main thread and executes the handler code. When an exception is raised from the handler
the exception is propagated back in the main thread stack. An observed traceback:
```
...
  File "/usr/lib/python3.8/subprocess.py", line 1804, in _wait
    (pid, sts) = self._try_wait(0)
  File "/usr/lib/python3.8/subprocess.py", line 1762, in _try_wait
    (pid, sts) = os.waitpid(self.pid, wait_flags)
  File "/home/stan/Projects/taro-suite/taro/taro/term.py", line 15, in terminate << handler code
    sys.exit()
SystemExit
```

### Color Print
termcolor module
https://github.com/tartley/colorama
https://github.com/erikrose/blessings
https://github.com/timofurrer/colorful

### Table Print
https://stackoverflow.com/questions/9535954/printing-lists-as-tabular-data
https://github.com/foutaise/texttable/
https://github.com/astanin/python-tabulate

### Misc

Logging config: https://stackoverflow.com/questions/14058453/making-python-loggers-output-all-messages-to-stdout-in-addition-to-log-file

STDOUT to file: https://stackoverflow.com/questions/4965159/how-to-redirect-output-with-subprocess-in-python

Reading subprocess stdout:
https://zaiste.net/realtime_output_from_shell_command_in_python/

https://stackoverflow.com/questions/13398261/how-to-run-a-subprocess-with-python-wait-for-it-to-exit-and-get-the-full-stdout
https://stackoverflow.com/questions/19961052/what-is-the-difference-if-i-dont-use-stdout-subprocess-pipe-in-subprocess-popen
https://stackoverflow.com/questions/803265/getting-realtime-output-using-subprocess

Log files location:
https://superuser.com/questions/1293842/where-should-userspecific-application-log-files-be-stored-in-gnu-linux?rq=1
https://stackoverflow.com/questions/25897836/where-should-i-write-a-user-specific-log-file-to-and-be-xdg-base-directory-comp

Bin location:
https://unix.stackexchange.com/questions/36871/where-should-a-local-executable-be-placed

Default ranger config:
/usr/lib/python3.7/site-packages/ranger/config/rc.conf

User specific site-packages:
/home/stan/.local/lib/python3.7/site-packages