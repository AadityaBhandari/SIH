#include <windows.h>
#include <stdio.h>
#include <string.h>

int main() {
    char dirPath[MAX_PATH];
    GetModuleFileNameA(NULL, dirPath, MAX_PATH);
    char *lastSlash = strrchr(dirPath, '\\');
    if (lastSlash) {
        *lastSlash = '\0';
    }

    char pythonExe[MAX_PATH];
    char scriptFile[MAX_PATH];
    snprintf(pythonExe, sizeof(pythonExe), "%s\\.venv\\Scripts\\python.exe", dirPath);
    snprintf(scriptFile, sizeof(scriptFile), "%s\\app.py", dirPath);

    DWORD attr = GetFileAttributesA(pythonExe);
    if (attr == INVALID_FILE_ATTRIBUTES) {
        printf("Error: Could not find Python environment at:\n%s\n", pythonExe);
        printf("\nPlease ensure the application remains in D:\\SIH.\n");
        system("pause");
        return 1;
    }

    char cmdLine[MAX_PATH * 3];
    snprintf(cmdLine, sizeof(cmdLine), "\"%s\" \"%s\"", pythonExe, scriptFile);

    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    if (CreateProcessA(NULL, cmdLine, NULL, NULL, TRUE, 0, NULL, dirPath, &si, &pi)) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    } else {
        printf("Failed to launch ARIA. Error code: %lu\n", GetLastError());
        system("pause");
        return 1;
    }

    return 0;
}
