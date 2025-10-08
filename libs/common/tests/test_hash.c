#include "common/hash.h"
#include "unity.h"

void setUp() {}
void tearDown() {}

#define HASH_CASES(X)                                                                              \
  X(0x13F4A7C2U, 0x3620AF22U, 0x2D87F3F6U)                                                         \
  X(0x8B92D0E5U, 0x1C71AB55U, 0xDC761452U)                                                         \
  X(0xCAFEBABEU, 0x2334EB5EU, 0x79FF04E8U)                                                         \
  X(0x7FFFFFFFU, 0xE1C8864FU, 0xF9CC0EA8U)                                                         \
  X(0x00000000U, 0x00000000U, 0x00000000U)                                                         \
  X(0xFFFFFFFFU, 0x61C8864FU, 0x81F16F39U)

static void run_hash32_knuth_case(uint32_t input, uint32_t expected) { // NOLINT
  TEST_ASSERT_EQUAL_HEX32(expected, hash32_knuth(input));
}

static void run_hash32_fmix_case(uint32_t input, uint32_t expected) { // NOLINT
  TEST_ASSERT_EQUAL_HEX32(expected, hash32_fmix(input));
}

#define DEF_TEST(input, knuth_expected, fmix_expected)                                             \
  static void test_hash32_##input##_knuth() {                                                      \
    run_hash32_knuth_case(input, knuth_expected);                                                  \
  }                                                                                                \
  static void test_hash32_##input##_fmix() {                                                       \
    run_hash32_fmix_case(input, fmix_expected);                                                    \
  }
HASH_CASES(DEF_TEST)
#undef DEF_TEST

int main() {
  UNITY_BEGIN();

#define RUN(input, knuth_expected, fmix_expected)                                                  \
  RUN_TEST(test_hash32_##input##_knuth);                                                           \
  RUN_TEST(test_hash32_##input##_fmix);
  HASH_CASES(RUN)
#undef RUN

  return UNITY_END();
}
