#pragma once

#include "sugar.h"
#include <stdint.h>

EXTERN_C_BEGIN

#define HASH32_MULT_KNUTH 2654435761U

#define HASH32_MUR_FMIX1 0x85EBCA6BU
#define HASH32_MUR_FMIX2 0xC2B2AE35U

static inline uint32_t hash32_knuth(uint32_t key) {
  return key * HASH32_MULT_KNUTH;
}

static inline uint32_t hash32_fmix(uint32_t key) {
  key ^= key >> 16; // NOLINT(readability-magic-numbers)
  key *= HASH32_MUR_FMIX1;
  key ^= key >> 13; // NOLINT(readability-magic-numbers)
  key *= HASH32_MUR_FMIX2;
  key ^= key >> 16; // NOLINT(readability-magic-numbers)
  return key;
}

EXTERN_C_END
