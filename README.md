# Mage
**A Clojure-like Lisp interpreter written in Python**

## Goals

1. Implement Clojure's sequence abstraction
2. Implement immutable base datastructures
3. Provide Python interop

## Usage

Clone this repo, and run the REPL script:

```sh
python repl.py
```

Within the REPL functions may be defined as `Vars` which are interned into a
namespace:

```clojure
(def fib (fn [n]
  (if (< n 2)
    1
    (+ (fib (- n 1)) (fib (- n 2))))))
```

Now with `fib` defined:

```clojure
=> (map fib (range 0 10))
(1 1 2 3 5 8 13 21 34 55)
```

## Work In Progress

This is a project that isn't intended to be used for anything serious: it's for
fun and edificiation.
