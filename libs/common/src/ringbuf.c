// Power-of-two optimized ringbuf implementation.
// Assumes ringbuf->cap is a power of two (2,4,8,...). No runtime asserts here.

#include "common/ringbuf.h"
#include <stdint.h>
#include <string.h>

/* ---------- internal helpers ---------- */

static inline size_t ringbuf__available(const ringbuf_t *ringbuf) {
  return ringbuf->head - ringbuf->tail;
}

static inline size_t ringbuf__min_size(size_t a,   // NOLINT(readability-identifier-length)
                                       size_t b) { // NOLINT(readability-identifier-length)
  return (a < b) ? a : b;
}

/* Fast modulo helpers for power-of-two cap */
static inline size_t ringbuf__mask(const ringbuf_t *ringbuf) {
  return ringbuf->cap - 1; // valid only if cap is power of two
}
static inline size_t ringbuf__idx(const ringbuf_t *ringbuf, size_t logical_index) {
  return logical_index & ringbuf__mask(ringbuf);
}

/* Convert a backing pointer to physical slot [0..cap-1].
   Returns true on success; false if ptr is out of buffer or misaligned. */
static bool ringbuf__ptr_to_slot(const ringbuf_t *ringbuf, const void *ptr, size_t *out_slot) {
  const uint8_t *base = ringbuf->buf;
  const uint8_t *as_bytes = (const uint8_t *) ptr;
  size_t total_bytes = ringbuf->cap * ringbuf->elem_size;

  if (as_bytes < base) {
    return false;
  }
  size_t off = (size_t) (as_bytes - base);
  if (off >= total_bytes) {
    return false;
  }
  if (off % ringbuf->elem_size != 0) {
    return false;
  }

  *out_slot = off / ringbuf->elem_size;
  return true;
}

/* Distance forward on a ring [0..cap-1] from start_slot to slot (0..cap-1).
   Power-of-two cap: use mask instead of % cap. */
static inline size_t ringbuf__slot_dist_forward(
    size_t slot, size_t start_slot, size_t cap) { // NOLINT(bugprone-easily-swappable-parameters)
  size_t mask = cap - 1;
  return (slot - start_slot) & mask;
}

/* Write 'cnt' elements from src into logical position 'idx' (handles wraparound). */
static void ringbuf__write_at(ringbuf_t *ringbuf, size_t idx, const void *src, size_t cnt) {
  if (!cnt) {
    return;
  }

  size_t start_elem = ringbuf__idx(ringbuf, idx);
  size_t first_elems = ringbuf->cap - start_elem;
  if (first_elems > cnt) {
    first_elems = cnt;
  }

  size_t first_bytes = first_elems * ringbuf->elem_size;
  memcpy(ringbuf->buf + (start_elem * ringbuf->elem_size), src, first_bytes);

  size_t remain_elems = cnt - first_elems;
  if (remain_elems) {
    memcpy(ringbuf->buf, (const uint8_t *) src + first_bytes, remain_elems * ringbuf->elem_size);
  }
}

/* ---------- ring API ---------- */

void ringbuf_init(ringbuf_t *ringbuf, void *mem,
                  size_t capacity_elems, // NOLINT(bugprone-easily-swappable-parameters)
                  size_t elem_size_bytes) {
  // NOTE: capacity_elems MUST be a power of two.
  ringbuf->buf = (uint8_t *) mem;
  ringbuf->cap = capacity_elems;
  ringbuf->elem_size = elem_size_bytes;
  ringbuf->head = 0;
  ringbuf->tail = 0;
}

void ringbuf_reset(ringbuf_t *ringbuf) {
  ringbuf->head = ringbuf->tail = 0;
}

size_t ringbuf_available(const ringbuf_t *ringbuf) {
  return ringbuf__available(ringbuf);
}

size_t ringbuf_free(const ringbuf_t *ringbuf) {
  size_t used = ringbuf__available(ringbuf);
  return (used < ringbuf->cap) ? (ringbuf->cap - used) : 0;
}

size_t ringbuf_write(ringbuf_t *ringbuf, const void *src, size_t n) {
  if (!n) {
    return 0;
  }

  size_t free_now = ringbuf_free(ringbuf);
  if (n > free_now) {
    /* Overwrite-oldest: advance tail to make room. */
    ringbuf->tail += (n - free_now);
  }
  ringbuf__write_at(ringbuf, ringbuf->head, src, n);
  ringbuf->head += n;
  return n;
}

void ringbuf_push(ringbuf_t *ringbuf, const void *elem) {
  (void) ringbuf_write(ringbuf, elem, 1);
}

/* ---------- iterator API ---------- */

void ringbuf_iter_begin(const ringbuf_t *ringbuf, ringbuf_iter_t *ringbuf_it) {
  ringbuf_it->rb = ringbuf;
  ringbuf_it->snap_head = ringbuf->head;
  ringbuf_it->snap_tail = ringbuf->tail;
  ringbuf_it->cursor = ringbuf_it->snap_tail;
}

size_t ringbuf_iter_remaining(const ringbuf_iter_t *ringbuf_it) {
  if (ringbuf_it->cursor >= ringbuf_it->snap_head) {
    return 0;
  }
  return ringbuf_it->snap_head - ringbuf_it->cursor;
}

void ringbuf_iter_next_span(ringbuf_iter_t *ringbuf_it, const void **ptr, size_t *len) {
  size_t remaining = ringbuf_iter_remaining(ringbuf_it);
  if (remaining == 0) {
    *ptr = NULL;
    *len = 0;
    return;
  }

  const ringbuf_t *ringbuf_local = ringbuf_it->rb;
  size_t start_elem = ringbuf__idx(ringbuf_local, ringbuf_it->cursor);
  size_t to_end = ringbuf_local->cap - start_elem;
  size_t give_elems = ringbuf__min_size(to_end, remaining);

  *ptr = ringbuf_local->buf + start_elem * ringbuf_local->elem_size;
  *len = give_elems;

  ringbuf_it->cursor += give_elems;
}

void ringbuf_iter_next_ptr(ringbuf_iter_t *ringbuf_it, const void **elem_ptr) {
  size_t remaining = ringbuf_iter_remaining(ringbuf_it);
  if (remaining == 0) {
    *elem_ptr = NULL;
    return;
  }

  const ringbuf_t *ringbuf_local = ringbuf_it->rb;
  size_t slot = ringbuf__idx(ringbuf_local, ringbuf_it->cursor);
  *elem_ptr = ringbuf_local->buf + slot * ringbuf_local->elem_size;

  ringbuf_it->cursor += 1;
}

const void *ringbuf_iter_cursor_ptr(const ringbuf_iter_t *ringbuf_it) {
  if (ringbuf_it->cursor >= ringbuf_it->snap_head) {
    return NULL;
  }
  const ringbuf_t *ringbuf_local = ringbuf_it->rb;
  size_t slot = ringbuf__idx(ringbuf_local, ringbuf_it->cursor);
  return ringbuf_local->buf + (slot * ringbuf_local->elem_size);
}

void ringbuf_iter_advance_count(ringbuf_iter_t *ringbuf_it, size_t n) {
  size_t remaining = ringbuf_iter_remaining(ringbuf_it);
  if (n > remaining) {
    n = remaining;
  }
  ringbuf_it->cursor += n;
}

bool ringbuf_iter_advance_to_ptr(ringbuf_iter_t *ringbuf_it, const void *ptr) {
  const ringbuf_t *ringbuf_local = ringbuf_it->rb;

  size_t slot;
  if (!ringbuf__ptr_to_slot(ringbuf_local, ptr, &slot)) {
    return false;
  }

  size_t tail_slot = ringbuf__idx(ringbuf_local, ringbuf_it->snap_tail);
  size_t dist = ringbuf__slot_dist_forward(slot, tail_slot, ringbuf_local->cap);
  size_t snap_size = ringbuf_it->snap_head - ringbuf_it->snap_tail;

  if (dist >= snap_size) {
    return false; /* ptr is not within this snapshot */
  }

  /* Inclusive: cursor moves AFTER ptr. */
  ringbuf_it->cursor = ringbuf_it->snap_tail + dist + 1;
  return true;
}

/* ---------- commit API ---------- */

void ringbuf_commit_count(ringbuf_t *ringbuf, size_t n) {
  size_t avail = ringbuf__available(ringbuf);
  if (n > avail) {
    n = avail;
  }
  ringbuf->tail += n;
}

bool ringbuf_commit_to_ptr(ringbuf_t *ringbuf, const void *ptr) {
  size_t slot;
  if (!ringbuf__ptr_to_slot(ringbuf, ptr, &slot)) {
    return false;
  }

  size_t tail_slot = ringbuf__idx(ringbuf, ringbuf->tail);
  size_t dist = ringbuf__slot_dist_forward(slot, tail_slot, ringbuf->cap);
  size_t avail = ringbuf__available(ringbuf);

  if (dist >= avail) {
    return false; /* ptr outside [tail..head) */
  }

  /* Inclusive: tail becomes AFTER ptr. */
  ringbuf->tail = ringbuf->tail + dist + 1;
  return true;
}
