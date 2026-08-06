# Memory

Forecast AI stores local runtime state under `MEMORY_STORE_DIR`.

Default:

```env
MEMORY_STORE_DIR=memory_data
```

The directory can contain:

- forecast history;
- evidence cache;
- agent reputation state;
- optional spend-guard state.

Runtime memory is ignored by Git and is not included in the public repository.

For containers, mount a persistent volume and point `MEMORY_STORE_DIR` to it:

```env
MEMORY_STORE_DIR=/data/memory
```

If no persistent volume is attached, container restarts may erase history and reputation updates.
