.PHONY: libs-test-build libs-test libs-test-clean libs-lint esp-build _check-jq esp-sanitize-db esp-lint check-format libs-checks esp-checks all-checks lint test

CLANG_TIDY ?= clang-tidy
CLANG_FORMAT ?= clang-format

# Esp configuration
ESP_BUILD_DIR := build
ESP_TIDY_DB_DIR := $(ESP_BUILD_DIR)/tidy

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
	HOST_TRIPLE := $(shell uname -m)-apple-darwin
else
	HOST_TRIPLE := x86_64-unknown-linux-gnu
endif
ESP_TIDY_FLAGS := -p $(ESP_TIDY_DB_DIR) --config-file=.clang-tidy --header-filter=''

# Libs Unity test configuration
LIBS_UNITY_DIR := libs/unity
LIBS_UNITY_BUILD_DIR := $(LIBS_UNITY_DIR)/build

# === Individual commands ===

# Libs commands
libs-test-build:
	cmake -S ${LIBS_UNITY_DIR} -B ${LIBS_UNITY_BUILD_DIR} -DCMAKE_BUILD_TYPE=Debug
	cmake --build ${LIBS_UNITY_BUILD_DIR} -j

libs-test: libs-test-build
	ctest --test-dir ${LIBS_UNITY_BUILD_DIR} --output-on-failure -V

libs-test-clean:
	rm -rf ${LIBS_UNITY_BUILD_DIR}

libs-lint: libs-test-build
	find libs/ -type f \( -name "*.c" -o -name "*.cpp" \) \
		! -path "libs/unity/build/*" \
		| xargs ${CLANG_TIDY} -p ${LIBS_UNITY_BUILD_DIR} --header-filter=''

# ESP commands
esp-build:
	idf.py build

_check-jq:
	@command -v jq >/dev/null || { echo "ERROR: jq not found. Install jq."; exit 1; }

esp-sanitize-db: _check-jq esp-build
	@mkdir -p "$(ESP_TIDY_DB_DIR)"
	@echo ">> sanitize $(ESP_BUILD_DIR)/compile_commands.json -> $(ESP_TIDY_DB_DIR)/compile_commands.json (target=$(HOST_TRIPLE))"
	@./sanitize_compile_db.sh "$(ESP_BUILD_DIR)/compile_commands.json" "$(ESP_TIDY_DB_DIR)/compile_commands.json" "$(HOST_TRIPLE)"

esp-lint: esp-sanitize-db
	find . -type f \( -name "*.c" -o -name "*.cpp" \) \
		\( -path "./main/*" -o -path "./components/*" \) \
		| xargs ${CLANG_TIDY} ${ESP_TIDY_FLAGS}

# Formatting
check-format:
	find . -type f \( -name "*.c" -o -name "*.h" -o -name "*.cpp" -o -name "*.hpp" \) \
		! -path "./build/*" ! -path "./.cache/*" ! -path "./libs/unity/build/*" \
		| xargs ${CLANG_FORMAT} --dry-run --Werror

# === Convenience targets ===

libs-checks: libs-test libs-lint
esp-checks: esp-lint
all-checks: check-format libs-checks esp-checks

lint: check-format libs-lint esp-lint
test: libs-test
