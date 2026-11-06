# Doc comments in headers

Headers carry Doxygen comments so `scripts/generate.py` can build the agent
reference. Only public headers; no comments in `.cpp`.

## Module preamble

The module's umbrella header (`<namespace_dir>/<Module>/<Module>.h` or `<Module>/<namespace_dir><Module>.h`, any case, or
`<namespace_dir>/<namespace_dir>.h` for the root module) opens with a `@file`
block: what the module is for, its main entry points, which platforms have it
(the build gate, if any), and the two or three rules an agent gets wrong
(threading, ownership, what to use instead). 5–15 lines.

```cpp
/** @file
    Threads, timers and the event loop. Everything here delivers on the main
    thread unless it says otherwise. ...
*/
```

A module with no umbrella header takes its preamble from a `/** @dir <path> ... */`
block in a `.dox` file in its folder, the path written from the repository root.

## Per header

A `/** @file <one sentence> */` saying what the header is for. This is the line
the module index shows.

## Per public symbol

One `///` line on each public class, struct, enum, free function and non-obvious
member. Say what the name can't:

- which thread a callback runs on; whether a call blocks
- who owns what; lifetime ("destroying it stops the timer")
- what happens on failure (returns empty, false, throws never)
- units and ranges (points vs pixels, 0..1, ms)
- what to use instead, when there's a better entry point

Never restate the name ("/// The timer class."). A self-explanatory getter gets
nothing. Plain short sentences, no acronyms left unexpanded.
