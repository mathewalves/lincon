#!/bin/bash

# Function to get message from CSV
function get_message_from_csv() {
    local id=$1
    local language=$2
    local csv_file

    if [[ $language == "pt" ]]; then
        csv_file="./languages/pt-br.csv"
    else
        csv_file="./languages/en.csv"
    fi

    while IFS=, read -r csv_id title message; do
        if [[ $csv_id == $id ]]; then
            echo "$title,$message"
            return
        fi
    done < "$csv_file"
}

# Function to display a message box
function display_message_box() {
    local id=$1
    local language=${2:-$(get_language_from_config)}
    IFS=, read -r title message <<< "$(get_message_from_csv $id $language)"
    whiptail --title "$title" --msgbox "$message" 8 78
}

# Function to display a menu
function display_menu() {
    local id=$1
    local language=${2:-$(get_language_from_config)}
    IFS=, read -r title prompt <<< "$(get_message_from_csv $id $language)"
    shift 2
    local options=("$@")
    whiptail --title "$title" --menu "$prompt" 15 60 4 "${options[@]}" 3>&1 1>&2 2>&3
}

# Function to display an input box
function display_input_box() {
    local id=$1
    local language=${2:-$(get_language_from_config)}
    IFS=, read -r title prompt <<< "$(get_message_from_csv $id $language)"
    whiptail --title "$title" --inputbox "$prompt" 8 60 3>&1 1>&2 2>&3
}

# Function to display a yes/no box
function display_yesno_box() {
    local id=$1
    local language=${2:-$(get_language_from_config)}
    IFS=, read -r title prompt <<< "$(get_message_from_csv $id $language)"
    whiptail --title "$title" --yesno "$prompt" 8 60
}

# Function to save the selected language to .config
function save_language_to_config() {
    local language=$1
    echo "LANGUAGE=$language" > .config
}

# Function to get the language from .config
function get_language_from_config() {
    if [[ -f .config ]]; then
        source .config
        echo $LANGUAGE
    else
        echo "en" # default language
    fi
}
