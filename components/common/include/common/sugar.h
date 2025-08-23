#pragma once

#ifdef __cplusplus
#define EXTERN_C_BEGIN extern "C" {
#define EXTERN_C_END }

#else
#define EXTERN_C_BEGIN
#define EXTERN_C_END

#endif

EXTERN_C_BEGIN

#ifndef MIN
#define MIN(a, b) (((a) < (b)) ? (a) : (b))
#endif /* MIN */

#ifndef MAX
#define MAX(a, b) (((a) > (b)) ? (a) : (b))
#endif /* MAX */

EXTERN_C_END
