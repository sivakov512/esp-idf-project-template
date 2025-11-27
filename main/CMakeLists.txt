idf_component_register(
    SRCS
        "main.c"
    INCLUDE_DIRS "."
    REQUIRES
        "embedlibs"
        "slog"
    PRIV_REQUIRES
        "app"
)
