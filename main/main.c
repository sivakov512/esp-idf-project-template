#include "app.h"
#include <embedlibs/log.h>
#include <stdint.h>

#define TAG "main"

void app_main() {
  LOGI("Initializing app...");
  esp_err_t err = app_init();
  if (err != ESP_OK) {
    LOGE("Failed to initialize app, %s", esp_err_to_name(err));
    goto err;
  }

  LOGI("Running app...");
  err = app_run();
  if (err != ESP_OK) {
    LOGE("Failed to run app, %s", esp_err_to_name(err));
    goto err;
  }

  LOGI("App started");

err:
  ESP_ERROR_CHECK(err);
}
