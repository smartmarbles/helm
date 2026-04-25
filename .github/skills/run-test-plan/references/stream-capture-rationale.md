# Why not `2>&1` piping

`... 2>&1 | Tee-Object` merges the two streams and loses the stdout-vs-stderr distinction that many assertions depend on (e.g., "validator prints results on stderr, JSON on stdout"). Always redirect to separate temp files.
