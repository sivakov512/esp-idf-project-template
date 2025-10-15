.PHONY: _check-jq build sanitize-db lint check-format

CLANG_TIDY ?= clang-tidy
CLANG_FORMAT ?= clang-format

BUILD_DIR := build
TIDY_DB_DIR := $(BUILD_DIR)/tidy

HOST_TESTS_DIR := tests/host
HOST_TESTS_BUILD_DIR := $(HOST_TESTS_DIR)/build

host-tests-build:
	cmake -S ${HOST_TESTS_DIR} -B ${HOST_TESTS_BUILD_DIR} -DCMAKE_BUILD_TYPE=Debug
	cmake --build ${HOST_TESTS_BUILD_DIR} -j

host-tests: host-tests-build
	ctest --test-dir ${HOST_TESTS_BUILD_DIR} --output-on-failure -V

host-tests-clean:
	rm -rf ${HOST_TESTS_BUILD_DIR}

_check-jq:
	@command -v jq >/dev/null || { echo "ERROR: jq not found. Install jq."; exit 1; }

build:
	idf.py build

sanitize-db: _check-jq build
	@mkdir -p "$(TIDY_DB_DIR)"
	@echo ">> sanitize $(BUILD_DIR)/compile_commands.json -> $(TIDY_DB_DIR)/compile_commands.json"
	@./sanitize_compile_db.py "$(BUILD_DIR)/compile_commands.json" "$(TIDY_DB_DIR)/compile_commands.json"

lint: sanitize-db
	find . \
    	\( -type d \( -name "managed_components" -o -name build -o -name ".cache" -o -name ".git" \) -prune \) \
    	-o \
    	-type f \( -name "*.c" -o -name "*.h" -o -name "*.cpp" -o -name "*.hpp" \) \
        -print0 \
		| xargs -0 ${CLANG_TIDY} -p ${TIDY_DB_DIR}


check-format:
	find . \
    	\( -type d \( -name "managed_components" -o -name build -o -name ".cache" -o -name ".git" \) -prune \) \
		-o \
    	-type f \( -name "*.c" -o -name "*.h" -o -name "*.cpp" -o -name "*.hpp" \) \
        -print0 \
		| xargs -0 ${CLANG_FORMAT} --dry-run --Werror
