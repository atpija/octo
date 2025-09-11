; Minimaler Installer für Octo ohne externe NSIS-Makros

!define APP_NAME "octo-client"
!define APP_VERSION "0.1"
!define APP_EXE_NAME "octo.exe"

!include "MUI2.nsh"
!include "WinMessages.nsh"

Name "${APP_NAME}"
OutFile "${APP_NAME}-${APP_VERSION}-setup.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
RequestExecutionLevel admin

; Seiten
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

; Installieren
Section "Install"
    SetOutPath "$INSTDIR"
    File "dist\${APP_EXE_NAME}"

    CreateShortcut "$SMPROGRAMS\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE_NAME}"

    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; in PATH eintragen
    Call AddToPath
SectionEnd

; Deinstallieren
Section "Uninstall"
    Delete "$INSTDIR\${APP_EXE_NAME}"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"
    Delete "$SMPROGRAMS\${APP_NAME}.lnk"

    Call un.RemoveFromPath
SectionEnd

; === PATH hinzufügen ===
Function AddToPath
    Push $0
    Push $1
    ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH"

    ; Prüfen ob schon enthalten
    StrCpy $1 $0
    ${DoWhile} $1 != ""
        StrCpy $1 $1 "" 0
        StrCmp $1 "$INSTDIR" PathExists
        StrCpy $1 "" ; abbrechen
    ${Loop}

    ; Wenn leer, neu setzen
    StrCmp $0 "" 0 +2
    StrCpy $0 "$INSTDIR"
    StrCmp $0 "" 0 +2
    StrCpy $0 "$0;$INSTDIR"

    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH" $0
    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000

    PathExists:
    Pop $1
    Pop $0
FunctionEnd

; === PATH entfernen ===
Function un.RemoveFromPath
    Push $0
    ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH"

    ; ganz einfache Variante: "$INSTDIR;" entfernen
    StrLen $1 "$INSTDIR;"
    loop:
        StrCpy $2 $0 $1
        StrCmp $2 "$INSTDIR;" 0 next
        StrCpy $0 $0 "" $1
        Goto done
    next:
        StrCpy $0 $0 "" 1
        StrCmp $0 "" done loop
    done:

    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH" $0
    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000

    Pop $0
FunctionEnd

