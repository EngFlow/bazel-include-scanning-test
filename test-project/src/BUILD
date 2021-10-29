cc_binary(
    name = 'bin',
    srcs = ['bin.cc'],
    deps = [':lib'],
)

cc_library(
    name = 'lib',
    srcs = ['lib.cc'],
    hdrs = ['header.h'],
    deps = [':libdep', ':libdep-unused'],
)

cc_library(
    name = 'libdep',
    srcs = ['libdep.cc'],
    hdrs = ['header-dependency.h'],
)

cc_library(
    name = 'libdep-unused',
    srcs = ['libdep-unused.cc'],
    hdrs = ['header-unused.h'],
)
