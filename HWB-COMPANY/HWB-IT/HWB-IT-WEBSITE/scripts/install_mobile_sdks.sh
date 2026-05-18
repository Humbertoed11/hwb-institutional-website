#!/bin/bash

# HWB-IT-013: High-Fidelity Mobile SDK Installation Sequence
# This script downloads and configures the necessary SDKs for Android and cross-platform (Flutter) development.

LOG_FILE="/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-SYSTEM-LOGS/mobile_sdk_install.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "--- SigmaFidelity: Initiating Mobile SDK Acquisition ---"
echo "Starting background download of Flutter SDK and Android command-line tools..."

# Setup Directories
DEV_DIR="/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-PROCESS-CONTROL/Mobile-SDKs"
mkdir -p "$DEV_DIR"
cd "$DEV_DIR"

# 1. Download Flutter SDK (Linux x64)
# Note: Using the stable release branch URL
FLUTTER_URL="https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.24.3-stable.tar.xz"
if [ ! -d "flutter" ]; then
    echo "Downloading Flutter SDK..."
    wget -qO flutter.tar.xz "$FLUTTER_URL"
    echo "Extracting Flutter SDK..."
    tar xf flutter.tar.xz
    rm flutter.tar.xz
else
    echo "Flutter SDK already present."
fi

# Add Flutter to PATH for this session (needs to be added to ~/.bashrc for permanent use)
export PATH="$DEV_DIR/flutter/bin:$PATH"

# 2. Download Android Command Line Tools
CMD_LINE_TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
if [ ! -d "android-sdk" ]; then
    echo "Downloading Android Command Line Tools..."
    wget -qO cmdtools.zip "$CMD_LINE_TOOLS_URL"
    echo "Extracting Android Tools..."
    mkdir -p android-sdk/cmdline-tools
    unzip -q cmdtools.zip -d android-sdk/cmdline-tools
    mv android-sdk/cmdline-tools/cmdline-tools android-sdk/cmdline-tools/latest
    rm cmdtools.zip
else
    echo "Android SDK directory already present."
fi

export ANDROID_HOME="$DEV_DIR/android-sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

echo "Accepting Android Licenses automatically..."
yes | sdkmanager --licenses > /dev/null 2>&1

echo "Pre-caching Flutter..."
flutter precache --no-analytics

echo "--- SDK Acquisition Complete ---"
echo "Flutter is now ready for autonomous mobile generation."
