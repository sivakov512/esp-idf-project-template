#include "app.h"
#include <slog.h>
#include <slog/platform/esp.h>
#include <stdint.h>

#define TAG "main"

void app_main() {
  slog_esp_init();

  SLOGI("Initializing app...");
  esp_err_t err = app_init();
  if (err != ESP_OK) {
    SLOGE("Failed to initialize app, %s", esp_err_to_name(err));
    goto err;
  }

  SLOGI("Running app...");
  err = app_run();
  if (err != ESP_OK) {
    SLOGE("Failed to run app, %s", esp_err_to_name(err));
    goto err;
  }

  SLOGI("App started");

err:
  ESP_ERROR_CHECK(err);
}
