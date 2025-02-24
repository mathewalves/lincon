#!/bin/bash

source ./src/whiptail/whiptail_framework.sh

language=$(get_language_from_config)

checkList()
{
    # check if running as root
    if [ "$(whoami)" != "root" ]; then
        echo -e "\e[96mLog in as a superuser(root):\e[39m"
        sudo -E bash "$0" "$@"
        exit $?
    fi

    # check if the 'pct' command is available on the host machine (proxmox)
    if ! command -v pct &> /dev/null; then
        display_message_box 40 $language
        exit 1
    fi

    # check if the 'sshpass' command is available on the host machine
    if ! command -v sshpass &> /dev/null; then
        apt-get install -y sshpass

        # check if the installation was successful
        if [ $? -ne 0 ]; then
            echo "Error: Failed to install 'sshpass'. Exiting."
            exit 1
        fi
    fi
}

selectBridge() 
{
    local bridges=($(brctl show | awk 'NR>1 && /^vmbr/ {print $1}'))

    if [ ${#bridges[@]} -eq 0 ]; then
        display_message_box 41 $language
        exit 1
    fi

    local options=()
    local menu_items=()
    local index=1
    
    for bridge in "${bridges[@]}"; do
        menu_items+=("$index" "$bridge")
        options[$index]=$bridge
        ((index++))
    done

    local menu_choice
    menu_choice=$(display_menu 42 $language "${menu_items[@]}")
    local choice=${options[$menu_choice]}


    if [ $? -eq 0 ]; then
        echo "$choice"
    else
        display_message_box 44 $language
        exit 1
    fi
}

# function to choose between DHCP, manual IP configuration, or copying Linux network settings
selectIPConfig() 
{
    local choice

    choice=$(whiptail --title "IP Configuration" --menu "Choose network configuration:" 15 60 6 \
        "1" "Use DHCP" \
        "2" "Manual IP Configuration" 3>&1 1>&2 2>&3)

    case "$choice" in
        "1")
            ip="dhcp"
            gateway="dhcp"
            ;;
        "2")
            ip=$(createMenu "Container IP" "Enter the target container IP:")
            gateway=$(createMenu "Gateway IP" "Enter the gateway IP:")
            ;;
        *)
            display_message_box 42 $language
            exit 1
            ;;
    esac
}

main() 
{
    display_message_box 1 $language
    checkList
    userInput
    validateParameters
    convert
}
main