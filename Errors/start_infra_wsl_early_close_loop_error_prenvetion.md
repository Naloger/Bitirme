The test ran and passed successfully in 32.50 seconds on the first attempt!
──────
### What was the issue?

1. The Pytest Hang: When we canceled a task earlier, it killed the parent task runner but left the child  pytest.
   exe  /  python.exe  process running in the background on Windows. This orphaned process held a write lock on your
   SQLite database files ( lemma_matrix.db  and  pages.db ), causing new  pytest  runs to hang indefinitely during
   initialization.
2. Stale Port Forwarding Rules: The reason the port forwarding was failing even after clearing the containers is
   that  wsl --terminate  only terminates the Alpine distribution user space; it does not shutdown the shared WSL2 VM
   kernel. The stale  iptables  NAT rules remained resident in the kernel memory, forwarding port  7687  traffic to a
   dead container IP.
   ──────
### How we solved it:

1. We killed the orphaned, locking Python processes to free the SQLite databases.
2. We added a self-healing step in start_infra.py that automatically flushes the WSL  iptables  NAT tables (
   iptables -t nat -F && iptables -t nat -X ) every single time the infrastructure stack starts up.
3. This ensures that old port bindings are swept clean and fresh containers get direct, unhindered port-forwarding
   access to Windows.

### Verification of Success:

•  [SUCCESS] Connected to Memgraph on attempt 1!
•  [SUCCESS] Created 8 Concept nodes in Memgraph.
