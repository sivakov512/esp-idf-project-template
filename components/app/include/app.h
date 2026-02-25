#pragma once

#include <embedlibs/sugar.h>
#include <esp_err.h>

EXTERN_C_BEGIN

typedef struct {
} app_ctx_t;

esp_err_t app_init(app_ctx_t *ctx);
esp_err_t app_run(app_ctx_t *ctx);

EXTERN_C_END
