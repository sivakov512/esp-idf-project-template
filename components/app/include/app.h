#pragma once

#include <embedlibs/sugar.h>
#include <esp_err.h>

EXTERN_C_BEGIN

/**
 * Initialize application
 *
 * @return ESP_OK on successful initialization, error code on failure
 */
esp_err_t app_init();

/**
 * Run application
 *
 * @return ESP_OK on successful run, error code on failure
 */
esp_err_t app_run();

EXTERN_C_END
