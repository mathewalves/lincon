#!/bin/bash

source ./src/whiptail/whiptail_framework.sh

language=$(get_language_from_config)

display_message_box 2 $language