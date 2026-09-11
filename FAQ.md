# FAQ — Level 3 labs

**401, and the key looks right.** The key and the base URL travel together. A `mai_` key needs `OPENAI_BASE_URL` set to the class proxy; a personal `sk-` key needs that line absent. Both mixed combinations return a 401 that looks exactly like a bad key. Print what Python actually loaded before changing anything.

**"This key's practice window has ended."** Each level's key covers a two-week arc. Your L2 key does not work here — mint an L3 key at [study.modernaipro.com/practice](https://study.modernaipro.com/practice).

**It worked yesterday and today it does not.** Did you press "get my key" again? Minting revokes the previous key immediately. Paste the new one.

**The lab dumps every stage at once instead of pausing.** You are piping input, so it runs non-interactively by design. Run it directly in a terminal to step with Enter.

**The approval prompt never appears and everything is denied.** Same cause — non-interactive runs fail closed on purpose. That is the correct behaviour, not a bug.

**ModuleNotFoundError after a `git pull`.** New labs sometimes add dependencies. Re-run `pip install -r requirements.txt` inside the activated venv.

**429 / burst limit.** The class lane is shared. The kit waits and retries once — let it.

**Python on this laptop is a lost cause.** Use the browser Lab Bench at [study.modernaipro.com/learn/lab](https://study.modernaipro.com/learn/lab).
