#pragma once

#include "sugar.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

EXTERN_C_BEGIN

/*
   ringbuf: single-producer/single-consumer ring buffer with a non-consuming iterator
   Policy: OVERWRITE-OLDEST (writer always accepts new data; oldest data is dropped)

   Assumptions:
   - Exactly one writer and one reader.
   - No concurrent access between writer and reader (synchronize externally if needed).
   - Elements are stored BY VALUE with a fixed elem_size (bytes).
*/

/* ----------------------- Ring buffer ----------------------- */

/**
 * @brief Ring buffer descriptor.
 */
typedef struct {
  uint8_t *buf;     /**< Backing memory: cap * elem_size bytes (owned by caller). */
  size_t cap;       /**< Capacity in elements (>= 1). */
  size_t elem_size; /**< Size of one element in bytes (>= 1). */
  size_t head;      /**< Next write index (monotonic counter). */
  size_t tail;      /**< Next read  index (monotonic counter). */
} ringbuf_t;

/**
 * @brief Initialize the ring buffer (no allocation).
 *
 * @param ringbuf            Pointer to ring buffer descriptor.
 * @param mem                Pointer to memory block of size (capacity_elems * elem_size_bytes)
 * bytes.
 * @param capacity_elems     Capacity in number of elements (>= 1).
 * @param elem_size_bytes    Size of one element in bytes (>= 1).
 */
void ringbuf_init(ringbuf_t *ringbuf, void *mem, size_t capacity_elems, size_t elem_size_bytes);

/**
 * @brief Clear the buffer. Reader will see it as empty.
 *
 * @param ringbuf Pointer to ring buffer descriptor.
 */
void ringbuf_reset(ringbuf_t *ringbuf);

/**
 * @brief Number of elements currently available to read (global).
 *
 * @param ringbuf Pointer to ring buffer descriptor.
 * @return Count of readable elements between tail and head.
 */
size_t ringbuf_available(const ringbuf_t *ringbuf);

/**
 * @brief Number of free slots before an overwrite would occur (informational).
 *
 * @param ringbuf Pointer to ring buffer descriptor.
 * @return Free slots in [0..cap].
 */
size_t ringbuf_free(const ringbuf_t *ringbuf);

/**
 * @brief Append a batch of elements (BY VALUE).
 *
 * Always accepts all @p n elements; if not enough space, advances tail to make room
 * (overwrite-oldest). Performs up to two memcpy operations (wrap handling).
 *
 * @param ringbuf Pointer to ring buffer descriptor.
 * @param src     Pointer to an array of @p n elements.
 * @param n       Number of elements to append.
 * @return        Number of elements written (always @p n).
 */
size_t ringbuf_write(ringbuf_t *ringbuf, const void *src, size_t n);

/**
 * @brief Append a single element (BY VALUE). Shortcut to ringbuf_write(..., 1).
 *
 * @param ringbuf Pointer to ring buffer descriptor.
 * @param elem    Pointer to element to append.
 */
void ringbuf_push(ringbuf_t *ringbuf, const void *elem);

/* ----------------------- Iterator (snapshot, non-consuming) ----------------------- */

/**
 * @brief Iterator over a snapshot of the buffer.
 *
 * Captures head/tail at begin(). Cursor starts at snap_tail. Traversal does NOT consume data.
 * Use commit functions to advance the global tail when you decide how much you have processed.
 */
typedef struct {
  const ringbuf_t *rb; /**< Associated buffer (read-only view). */
  size_t snap_head;    /**< Head captured at begin(). */
  size_t snap_tail;    /**< Tail captured at begin(). */
  size_t cursor;       /**< Current logical index inside the snapshot. */
} ringbuf_iter_t;

/**
 * @brief Begin a new iteration snapshot (captures head and tail).
 *
 * The iterator will see only data present at the moment of this call.
 *
 * @param ringbuf Pointer to ring buffer descriptor.
 * @param ringbuf_it Pointer to iterator to initialize.
 */
void ringbuf_iter_begin(const ringbuf_t *ringbuf, ringbuf_iter_t *ringbuf_it);

/**
 * @brief Remaining elements in this snapshot from cursor up to snap_head.
 *
 * @param ringbuf_it Iterator.
 * @return Number of elements not yet traversed in this snapshot.
 */
size_t ringbuf_iter_remaining(const ringbuf_iter_t *ringbuf_it);

/**
 * @brief Return the next contiguous span (zero-copy) and advance cursor by its length.
 *
 * The span is limited by the physical end of the backing array; call repeatedly to
 * traverse the snapshot (the next call will continue from the next position and may
 * return the "head" part after wrap). If no data remains, *ptr = NULL and *len = 0.
 *
 * @param ringbuf_it Iterator (cursor is advanced by returned length).
 * @param ptr        Out: pointer to the first element of the span, or NULL if none.
 * @param len        Out: number of contiguous elements in the span (<= remaining).
 */
void ringbuf_iter_next_span(ringbuf_iter_t *ringbuf_it, const void **ptr, size_t *len);

/**
 * @brief Return a pointer to the next single element (zero-copy) and advance cursor by 1.
 *
 * If no data remains, *elem_ptr = NULL and cursor is not advanced.
 *
 * @param ringbuf_it Iterator.
 * @param elem_ptr   Out: pointer to the element, or NULL if none.
 */
void ringbuf_iter_next_ptr(ringbuf_iter_t *ringbuf_it, const void **elem_ptr);

/**
 * @brief Get a pointer to the current cursor element (does NOT advance).
 *
 * Returns NULL if cursor is at/beyond the snapshot head.
 *
 * @param ringbuf_it Iterator.
 * @return Pointer to current element, or NULL if none.
 */
const void *ringbuf_iter_cursor_ptr(const ringbuf_iter_t *ringbuf_it);

/**
 * @brief Advance the iterator cursor by @p n elements (clamped to remaining).
 *
 * @param ringbuf_it Iterator.
 * @param n          Elements to skip from the current cursor.
 */
void ringbuf_iter_advance_count(ringbuf_iter_t *ringbuf_it, size_t n);

/**
 * @brief Advance the iterator cursor directly to a pointer (inclusive).
 *
 * Cursor becomes positioned AFTER the element pointed by @p ptr.
 * The @p ptr must be a pointer previously returned by this buffer within this snapshot.
 *
 * @param ringbuf_it Iterator.
 * @param ptr        Pointer to an element in the backing array.
 * @return true if @p ptr is valid for this snapshot and the cursor was advanced; false otherwise.
 */
bool ringbuf_iter_advance_to_ptr(ringbuf_iter_t *ringbuf_it, const void *ptr);

/* ----------------------- Commit (advance global tail) ----------------------- */

/**
 * @brief Consume (commit) @p n elements from the current global tail (clamped to available).
 *
 * @param ringbuf Ring buffer.
 * @param n       Number of elements to consume.
 */
void ringbuf_commit_count(ringbuf_t *ringbuf, size_t n);

/**
 * @brief Consume (commit) up to the element addressed by @p ptr (inclusive).
 *
 * After success, the next read will start AFTER this element.
 * The @p ptr must lie within the currently readable logical range [tail..head).
 *
 * @param ringbuf Ring buffer.
 * @param ptr     Pointer to an element in the backing array (returned by this buffer).
 * @return true if @p ptr was valid and commit succeeded; false otherwise.
 */
bool ringbuf_commit_to_ptr(ringbuf_t *ringbuf, const void *ptr);

EXTERN_C_END
