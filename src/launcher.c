// SPDX-License-Identifier: MIT
#include <mach-o/dyld.h>
#include <libgen.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <glob.h>
#include <spawn.h>
#include <sys/wait.h>
#include <errno.h>
extern char **environ;

static int fail(const char *message) {
    fprintf(stderr, "Jellyfin + SVP: %s\n", message);
    return EXIT_FAILURE;
}

int main(int argc, char **argv) {
    (void)argc;
    glob_t matches = {0};
    const char *pattern = "/opt/homebrew/opt/vapoursynth/libexec/lib/python*/site-packages/vapoursynth/libvsscript.dylib";
    if (glob(pattern, 0, NULL, &matches) != 0 || matches.gl_pathc != 1) {
        globfree(&matches);
        return fail("Expected one Homebrew VapourSynth R80-style runtime. Run setup.py doctor.");
    }
    char modules[PATH_MAX];
    if (strlen(matches.gl_pathv[0]) >= sizeof(modules)) {
        globfree(&matches);
        return fail("VapourSynth path is too long.");
    }
    strcpy(modules, matches.gl_pathv[0]);
    if (setenv("VSSCRIPT_PATH", modules, 1) != 0) return fail("Cannot set VSSCRIPT_PATH.");
    // Strip library filename, then package directory, to obtain site-packages.
    *strrchr(modules, '/') = '\0';
    *strrchr(modules, '/') = '\0';
    unsetenv("PYTHONHOME");
    if (setenv("PYTHONPATH", modules, 1) != 0) return fail("Cannot set PYTHONPATH.");
    globfree(&matches);

    pid_t pid;
    char *open_args[] = {"/usr/bin/open", "-g", "-a", "/Applications/SVP 4 Mac.app", NULL};
    int status;
    if (posix_spawn(&pid, open_args[0], NULL, NULL, open_args, environ) != 0)
        return fail("Cannot start SVP.");
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR) return fail("Cannot wait for SVP launcher.");
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0)
        return fail("Install and open SVP 4 Mac before launching Jellyfin.");

    char launcher[PATH_MAX], executable[PATH_MAX];
    uint32_t size = sizeof(launcher);
    if (_NSGetExecutablePath(launcher, &size) != 0) return fail("Launcher path is too long.");
    int n = snprintf(executable, sizeof(executable), "%s/Jellyfin Media Player", dirname(launcher));
    if (n < 0 || (size_t)n >= sizeof(executable)) return fail("Player path is too long.");
    argv[0] = executable;
    execv(executable, argv);
    perror("Jellyfin + SVP");
    return EXIT_FAILURE;
}
