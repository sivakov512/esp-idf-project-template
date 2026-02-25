#include "app.h"
#include <slog.h>
#include <stdint.h>

SLOG_REGISTER("main");

void app_main() {
  SLOGI("Initializing app...");

  static app_ctx_t ctx = {};

  esp_err_t err = app_init(&ctx);
  if (err != ESP_OK) {
    SLOGE("Failed to initialize app, %s", esp_err_to_name(err));
    goto err;
  }

  SLOGI("Running app...");
  err = app_run(&ctx);
  if (err != ESP_OK) {
    SLOGE("Failed to run app, %s", esp_err_to_name(err));
    goto err;
  }

  SLOGI("App started");
  return;

err:
  ESP_ERROR_CHECK(err);
}
