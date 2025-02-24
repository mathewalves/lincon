#!/bin/bash

source ./src/whiptail/whiptail_framework.sh

# Get the language from .config or display a menu to select the language
language=$(get_language_from_config)
if [[ -z $language ]]; then
    LANGUAGE=$(display_menu 1 "en" \
    "1" "Português Brasileiro" \
    "2" "English")

    case $LANGUAGE in
        1)
            language="pt"
            ;;
        2)
            language="en"
            ;;
        *)
            echo "Invalid option"
            exit 1
            ;;
    esac

    save_language_to_config $language
fi

# Display a welcome message
display_message_box 2 $language

# Example of displaying a menu
MENU_OPTION=$(display_menu 3 $language \
"1" "Linux -> Docker" \
"2" "Linux -> Proxmox/LXC")

if [ $MENU_OPTION -eq 1 ]; then
    ./src/linux_docker.sh
elif [ $MENU_OPTION -eq 2 ]; then
    ./src/linux_proxmox.sh
else
    echo "Invalid option"
    exit 1
fi