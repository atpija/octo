; Enhanced Installer for Octo with Environment Variables
!define APP_NAME "octo-client"
!define APP_VERSION "0.2.1"
!define APP_EXE_NAME "octo.exe"
!define COMPANY_NAME "Jan Pirringer"
!define APP_DESCRIPTION "Octo Client Application"
!define APP_URL "https://project-octo.com"
!define APP_ICON "octo_logo.ico"

!include "MUI2.nsh"
!include "WinMessages.nsh"
!include "LogicLib.nsh"

; === General Settings ===
Name "${APP_NAME} ${APP_VERSION}"
OutFile "${APP_NAME}-${APP_VERSION}-setup.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
RequestExecutionLevel admin

; === UI Customization ===
!define MUI_WELCOMEPAGE_TITLE "Welcome to ${APP_NAME} ${APP_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "This setup will install ${APP_NAME} on your computer.$\r$\n$\r$\n${APP_DESCRIPTION}$\r$\n$\r$\nClick Next to continue."
!define MUI_FINISHPAGE_TITLE "Installation complete"
!define MUI_FINISHPAGE_TEXT "${APP_NAME} was successfully installed."
; Removed auto-run option here
!define MUI_FINISHPAGE_LINK "Visit our website"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"

; === Pages ===
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; === Languages ===
!insertmacro MUI_LANGUAGE "English"

; === Version Info ===
VIProductVersion "${APP_VERSION}.0.0"
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName" "${COMPANY_NAME}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription" "${APP_DESCRIPTION}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "LegalCopyright" "© ${COMPANY_NAME}"

; === Installer Sections ===
Section "${APP_NAME} (Main program)" SEC_MAIN
    SectionIn RO
    
    SetOutPath "$INSTDIR"
    File "dist\${APP_EXE_NAME}"

    ; Registry entries for Uninstall
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                     "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                     "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                     "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                     "Publisher" "${COMPANY_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                     "URLInfoAbout" "${APP_URL}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                     "InstallLocation" "$INSTDIR"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                       "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                       "NoRepair" 1

    ; Create Uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; === Environment Variables ===
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" \
                          "OCTO_HOME" "$INSTDIR"
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" \
                          "OCTO_CONFIG" "$INSTDIR\config"
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" \
                          "OCTO_DATA" "$APPDATA\${APP_NAME}"

    Call AddToPath
    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000

    CreateDirectory "$APPDATA\${APP_NAME}"
    CreateDirectory "$INSTDIR\config"
SectionEnd

Section "Context menu integration" SEC_CONTEXT
    WriteRegStr HKCR ".octo" "" "OctoFile"
    WriteRegStr HKCR "OctoFile" "" "Octo File"
    WriteRegStr HKCR "OctoFile\DefaultIcon" "" "$INSTDIR\${APP_EXE_NAME},0"
    WriteRegStr HKCR "OctoFile\shell\open\command" "" '"$INSTDIR\${APP_EXE_NAME}" "%1"'
SectionEnd

; === Component Descriptions ===
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MAIN} "Main files of ${APP_NAME}"
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC_CONTEXT} "Integrates ${APP_NAME} into context menu"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; === Uninstall Section ===
Section "Uninstall"
    Delete "$INSTDIR\${APP_EXE_NAME}"
    Delete "$INSTDIR\uninstall.exe"

    RMDir /r "$INSTDIR\config"
    RMDir "$INSTDIR"
    RMDir /r "$APPDATA\${APP_NAME}"

    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKCR ".octo"
    DeleteRegKey HKCR "OctoFile"

    DeleteRegValue HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "OCTO_HOME"
    DeleteRegValue HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "OCTO_CONFIG"
    DeleteRegValue HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "OCTO_DATA"

    Call un.RemoveFromPath
    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000
SectionEnd

; === PATH Functions ===
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

; === Helper Functions ===
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

; === Initialization ===
Function .onInit
    UserInfo::GetAccountType
    Pop $0
    ${If} $0 != "admin"
        MessageBox MB_ICONSTOP "Administrator rights required!"
        SetErrorLevel 740
        Quit
    ${EndIf}
FunctionEnd

