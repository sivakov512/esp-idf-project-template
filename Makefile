CLANG_TIDY ?= clang-tidy
CLANG_FORMAT ?= clang-format

BUILD_DIR := build
TIDY_DB_DIR := $(BUILD_DIR)/tidy

HOST_TESTS_DIR := tests/host
HOST_TESTS_BUILD_DIR := $(HOST_TESTS_DIR)/build
HOST_LINT_LIBS :=

# Utils
quote = $(foreach d,$(1),"$(d)")

# Common
.PHONY: _check-jq check-format

_check-jq:
	@command -v jq >/dev/null || { echo "ERROR: jq not found. Install jq."; exit 1; }

check-format:
		find . \
    	\( -type d \( -name "managed_components" -o -name build -o -name ".cache" -o -name ".git" \) -prune \) \
			-o \
    	-type f \( -name "*.c" -o -name "*.h" -o -name "*.cpp" -o -name "*.hpp" \) \
        -print0 \
			| xargs -0 ${CLANG_FORMAT} --dry-run --Werror

# Host
.PHONY: host-test-build host-test host-test-clean host-lint

host-test-build:
	cmake -S ${HOST_TESTS_DIR} -B ${HOST_TESTS_BUILD_DIR} -DCMAKE_BUILD_TYPE=Debug
	cmake --build ${HOST_TESTS_BUILD_DIR} -j

host-test: host-test-build
	ctest --test-dir ${HOST_TESTS_BUILD_DIR} --output-on-failure -V

host-test-clean:
	rm -rf ${HOST_TESTS_BUILD_DIR}

host-lint: host-test-build
ifneq ($(strip $(HOST_LINT_LIBS)),)
	find $(call quote,$(HOST_LINT_LIBS)) \
       	\( -type d -name include_esp -prune \) \
       	-o \
	    \( -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) \
		-print0 \) \
	| xargs -0 $(CLANG_TIDY) -p "$(HOST_TESTS_BUILD_DIR)"
else
	@echo "HOST_LINT_LIBS is empty, skipping host-lint"
endif

# ESP
.PHONY: esp-build esp-sanitize-db esp-lint

esp-build:
	idf.py build

esp-sanitize-db: _check-jq esp-build
	@mkdir -p "$(TIDY_DB_DIR)"
	@echo ">> sanitize $(BUILD_DIR)/compile_commands.json -> $(TIDY_DB_DIR)/compile_commands.json"
	@./sanitize_compile_db.py "$(BUILD_DIR)/compile_commands.json" "$(TIDY_DB_DIR)/compile_commands.json"

esp-lint: esp-sanitize-db
	find . \
    	\( -type d \( -name "managed_components" -o -name build -o -name ".cache" -o -name ".git" \) -prune \) \
    	-o \
    	-type f \( -name "*.c" -o -name "*.h" -o -name "*.cpp" -o -name "*.hpp" \) \
        -print0 \
		| xargs -0 ${CLANG_TIDY} -p ${TIDY_DB_DIR}

# All in one
.PHONY: lint test

lint: check-format esp-lint host-lint
test: host-test
