# clang-tidy, clang-format and clangd come from Espressif LLVM (esp-clang and
# esp-clangd), the same versions locally, in the editor and in CI. Source the
# ESP-IDF export script first; esp-clang is installed with
#   python $IDF_PATH/tools/idf_tools.py install esp-clang
CLANG_TIDY ?= clang-tidy
CLANG_FORMAT ?= clang-format
CLANGD ?= clangd
CLANG_TIDY_EXTRAS ?=
# Show diagnostics only from headers inside this project's own source trees
CLANG_TIDY_HEADER_FILTER ?= $(CURDIR)/(main|components)/.*


# ---- Utils ----
.PHONY: _check-esp-clang

__quote = $(foreach d,$(1),"$(d)")

__ESP_CLANG_HINT := Source the ESP-IDF export script and install esp-clang: python \$$IDF_PATH/tools/idf_tools.py install esp-clang

# $(call __check_espressif,<tool>)
__check_espressif = $(1) --version 2>/dev/null | grep -q Espressif || { echo "ERROR: $(1) is not Espressif LLVM. $(__ESP_CLANG_HINT)"; exit 1; }

_check-esp-clang:
	@$(call __check_espressif,$(CLANG_TIDY))
	@$(call __check_espressif,$(CLANG_FORMAT))


# ---- Common ----
.PHONY: check-format

check-format: _check-esp-clang
		find . \
    	\( -type d \( -name "managed_components" -o -name build -o -name ".cache" -o -name ".git" \) -prune \) \
			-o \
    	-type f \( -name "*.c" -o -name "*.h" -o -name "*.cpp" -o -name "*.hpp" \) \
        -print0 \
			| xargs -0 ${CLANG_FORMAT} --dry-run --Werror


# ---- Editor (clangd) ----
.PHONY: use-host use-esp zed

# Point compile_commands.json at a prepared database (see sanitize_compile_db.py)
__ln_cc = ln -sf "$(1)/compile_commands.json" compile_commands.json

use-esp: esp-sanitize-db
	$(call __ln_cc,./$(__TIDY_DB_DIR))

use-host: host-sanitize-db
	$(call __ln_cc,./$(__HOST_TIDY_DB_DIR))

# Zed: use esp-clangd for this project only (.zed/settings.json, not committed)
zed:
	@$(call __check_espressif,$(CLANGD))
	@mkdir -p .zed
	@printf '%s\n' \
		'{' \
		'  "lsp": {' \
		'    "clangd": {' \
		'      "binary": {' \
		'        "path": "$(shell command -v $(CLANGD))",' \
		'        "arguments": ["--clang-tidy", "--background-index"]' \
		'      }' \
		'    }' \
		'  },' \
		'  "languages": {' \
		'    "C": { "format_on_save": "on", "formatter": "language_server" },' \
		'    "C++": { "format_on_save": "on", "formatter": "language_server" }' \
		'  }' \
		'}' > .zed/settings.json
	@echo ">> wrote .zed/settings.json (clangd: $(shell command -v $(CLANGD)))"


# ---- Host ----
.PHONY: host-build host-sanitize-db host-test host-clean host-lint

__HOST_TESTS_DIR := tests/host
__HOST_TESTS_BUILD_DIR := $(__HOST_TESTS_DIR)/build
__HOST_TIDY_DB_DIR := $(__HOST_TESTS_BUILD_DIR)/tidy
HOST_LINT_LIBS ?=

host-build:
	cmake -S ${__HOST_TESTS_DIR} -B ${__HOST_TESTS_BUILD_DIR} -DCMAKE_BUILD_TYPE=Debug
	cmake --build ${__HOST_TESTS_BUILD_DIR} -j

host-sanitize-db: host-build
	@echo ">> sanitize $(__HOST_TESTS_BUILD_DIR)/compile_commands.json -> $(__HOST_TIDY_DB_DIR)/compile_commands.json"
	@./sanitize_compile_db.py --host "$(__HOST_TESTS_BUILD_DIR)/compile_commands.json" "$(__HOST_TIDY_DB_DIR)/compile_commands.json"

host-test: host-build
	ctest --test-dir ${__HOST_TESTS_BUILD_DIR} --output-on-failure -V

host-clean:
	rm -rf ${__HOST_TESTS_BUILD_DIR}

host-lint: _check-esp-clang host-sanitize-db
ifneq ($(strip $(HOST_LINT_LIBS)),)
	find $(call __quote,$(HOST_LINT_LIBS)) \
       	\( -type d -name include_esp -prune \) \
       	-o \
	    \( -type f \( -name '*.c' -o -name '*.cpp' \) \
		-print0 \) \
	| xargs -0 $(CLANG_TIDY) $(CLANG_TIDY_EXTRAS) --header-filter='$(CLANG_TIDY_HEADER_FILTER)' -p "$(__HOST_TIDY_DB_DIR)"
else
	@echo "HOST_LINT_LIBS is empty, skipping host-lint"
endif

host-fullcheck: host-test host-lint


# ---- ESP ----
.PHONY: esp-menuconfig esp-build esp-sanitize-db esp-clean esp-flash esp-monitor esp-flashm esp-lint

__BUILD_DIR := build
__TIDY_DB_DIR := $(__BUILD_DIR)/tidy
PORT_ESP ?= /dev/tty.usbmodem1101

esp-menuconfig:
	idf.py menuconfig

esp-build:
	idf.py build

esp-sanitize-db: esp-build
	@echo ">> sanitize $(__BUILD_DIR)/compile_commands.json -> $(__TIDY_DB_DIR)/compile_commands.json"
	@./sanitize_compile_db.py "$(__BUILD_DIR)/compile_commands.json" "$(__TIDY_DB_DIR)/compile_commands.json"

esp-clean:
	rm -rf $(__BUILD_DIR) .cache managed_components dependencies.lock
	idf.py fullclean

esp-flash: esp-build
	idf.py -p $(PORT_ESP) flash

esp-monitor: esp-build
	idf.py -p $(PORT_ESP) monitor

esp-flashm: esp-build
	idf.py -p $(PORT_ESP) flash monitor

esp-lint: _check-esp-clang esp-sanitize-db
	find . \
    	\( -type d \( -name "managed_components" -o -name build -o -name ".cache" -o -name ".git" \) -prune \) \
    	-o \
    	-type f \( -name "*.c" -o -name "*.cpp" \) \
        -print0 \
		| xargs -0 ${CLANG_TIDY} $(CLANG_TIDY_EXTRAS) --header-filter='$(CLANG_TIDY_HEADER_FILTER)' -p ${__TIDY_DB_DIR}


# ---- All in one ----
.PHONY: lint test fullcheck clean

lint: esp-lint host-lint check-format
test: host-test
fullcheck: lint test
clean: host-clean esp-clean
