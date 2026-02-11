; Octo Runner Installer (English, same structure as client)
!define APP_NAME "octo-runner"
!define APP_VERSION "0.2.0"
!define APP_EXE_NAME "octo-runner.exe"
!define COMPANY_NAME "Jan Pirringer"
!define APP_DESCRIPTION "Octo Runner Application"
!define APP_URL "https://project-octo.com"
!define APP_ICON "octo_logo.ico"

!include "MUI2.nsh"
!include "WinMessages.nsh"
!include "LogicLib.nsh"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "${APP_NAME}-${APP_VERSION}-setup.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
RequestExecutionLevel admin

!define MUI_WELCOMEPAGE_TITLE "Welcome to ${APP_NAME} ${APP_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "This setup will install ${APP_NAME} on your computer.$\r$\n$\r$\n${APP_DESCRIPTION}$\r$\n$\r$\nClick Next to continue."
!define MUI_FINISHPAGE_TITLE "Installation complete"
!define MUI_FINISHPAGE_TEXT "${APP_NAME} was successfully installed."
!define MUI_FINISHPAGE_LINK "Visit our website"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

VIProductVersion "${APP_VERSION}.0.0"
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName" "${COMPANY_NAME}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription" "${APP_DESCRIPTION}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "LegalCopyright" "© ${COMPANY_NAME}"

Section "${APP_NAME} (Main program)" SEC_MAIN
    SectionIn RO

    SetOutPath "$INSTDIR"
    File "dist\${APP_EXE_NAME}"

    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Environment variables specific for server
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "OCTO_SERVER_HOME" "$INSTDIR"
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "OCTO_SERVER_CONFIG" "$INSTDIR\config"
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "OCTO_SERVER_DATA" "$APPDATA\${APP_NAME}"

    Call AddToPath
    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000

    CreateDirectory "$APPDATA\${APP_NAME}"
    CreateDirectory "$INSTDIR\config"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MAIN} "Main files of ${APP_NAME}"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
    Delete "$INSTDIR\${APP_EXE_NAME}"
    Delete "$INSTDIR\uninstall.exe"

    RMDir /r "$INSTDIR\config"
    RMDir "$INSTDIR"
    RMDir /r "$APPDATA\${APP_NAME}"

    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

    DeleteRegValue HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "OCTO_SERVER_HOME"
    DeleteRegValue HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "OCTO_SERVER_CONFIG"
    DeleteRegValue HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "OCTO_SERVER_DATA"

    Call un.RemoveFromPath
    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000
SectionEnd

; PATH functions and helpers are identical to client
Function AddToPath
    Push $0
    Push $1
    Push $2
    ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH"
    ${If} $0 == ""
        StrCpy $0 "$INSTDIR"
    ${Else}
        Push $0
        Push "$INSTDIR"
        Call StrContains
        Pop $1
        ${If} $1 == ""
            StrCpy $0 "$0;$INSTDIR"
        ${EndIf}
    ${EndIf}
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH" $0
    Pop $2
    Pop $1
    Pop $0
FunctionEnd

Function un.RemoveFromPath
    Push $0
    ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH"
    Push $0
    Push ";$INSTDIR"
    Push ""
    Call un.StrReplace
    Pop $0
    Push $0
    Push "$INSTDIR;"
    Push ""
    Call un.StrReplace
    Pop $0
    Push $0
    Push "$INSTDIR"
    Push ""
    Call un.StrReplace
    Pop $0
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH" $0
    Pop $0
FunctionEnd

Function StrContains
    Exch $0
    Exch
    Exch $1
    Push $2
    Push $3
    StrLen $2 $0
    StrLen $3 $1
    ${If} $2 > $3
        StrCpy $0 ""
        Goto done
    ${EndIf}
    IntOp $3 $3 - $2
    IntOp $3 $3 + 1
    ${For} $2 0 $3
        StrCpy $4 $1 $2 $2
        ${If} $4 == $0
            StrCpy $0 $2
            Goto done
        ${EndIf}
    ${Next}
    StrCpy $0 ""
    done:
    Pop $3
    Pop $2
    Pop $1
    Exch $0
FunctionEnd

Function un.StrReplace
    Exch $0
    Exch
    Exch $1
    Exch 2
    Exch $2
    Push $3
    Push $4
    Push $5
    StrLen $3 $1
    StrLen $4 $0
    StrCpy $5 ""
    loop:
        StrCpy $6 $2 $3
        ${If} $6 == $1
            StrCpy $5 "$5$0"
            StrCpy $2 $2 "" $3
        ${Else}
            StrCpy $6 $2 1
            StrCpy $5 "$5$6"
            StrCpy $2 $2 "" 1
        ${EndIf}
        ${If} $2 != ""
            Goto loop
        ${EndIf}
    StrCpy $0 $5
    Pop $5
    Pop $4
    Pop $3
    Pop $2
    Pop $1
    Exch $0
FunctionEnd

Function .onInit
    UserInfo::GetAccountType
    Pop $0
    ${If} $0 != "admin"
        MessageBox MB_ICONSTOP "Administrator rights required!"
        SetErrorLevel 740
        Quit
    ${EndIf}
FunctionEnd

