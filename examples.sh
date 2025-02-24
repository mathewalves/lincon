#!/bin/bash

# Source the whiptail framework
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

# Example of displaying a message box
display_message_box 2 $language

# Example of displaying a menu
MENU_OPTION=$(display_menu 3 $language \
"1" "Option 1" \
"2" "Option 2" \
"3" "Option 3")

# Display the selected menu option
display_message_box 4 $language

# Example of displaying an input box
USER_INPUT=$(display_input_box 5 $language)

# Display the user input
display_message_box 6 $language

# Example of displaying a yes/no box
if display_yesno_box 7 $language; then
    display_message_box 8 $language
else
    display_message_box 9 $language
fi
