# Ambrane Smartwatch Troubleshooting Manual

This manual provides detailed technical instructions for troubleshooting and resolving common issues with Ambrane smartwatches.

## 1. Device Pairing and Connection Issues
If a smartwatch fails to pair with a smartphone:
*   **Step 1: Check Bluetooth Status**: Ensure Bluetooth is enabled on the mobile device. Toggle it off and on again.
*   **Step 2: Unbind Previous Connections**: If the watch was previously paired with another phone, it MUST be unbound/forgotten from that device's Bluetooth settings and app.
*   **Step 3: Correct Companion App usage**: Do NOT connect the smartwatch directly using the phone's system Bluetooth settings. Connect ONLY via the designated app:
    *   **Da Fit**: Models Wise Eon Pro, Wise Eon Max, Wise Eon.
    *   **GloryFit**: Models Wise Rush, Wise Roam.
    *   **HaWoFit**: Model Wise Glaze.
    *   **FitCloudPro**: Models Wise Crest, Wise Glaze 2.
*   **Step 4: Factory Reset Watch**: If connection continues to fail, go to watch Settings > System > Reset, then clear the companion app cache and restart the pairing process inside the app.

## 2. Bluetooth Calling Setup (Dual Connectivity)
For watches supporting calling, two Bluetooth connections are required: one for App data, and one for Call audio.
*   **iOS Connection Procedure**:
    1. Bind watch inside the companion app.
    2. Go to iPhone Settings > Bluetooth.
    3. Find and select the audio device name (typically matches `[Watch Model] Phone` or `[Watch Model]_Audio`).
    4. Ensure the status shows "Connected".
*   **Android Connection Procedure**:
    1. Bind watch inside the companion app.
    2. Respond "Pair" or "Allow" to the system prompt asking for contact access and calling permissions.
    3. If prompt doesn't appear, go to system Bluetooth settings, find `[Watch Model] Phone` and pair manually.

## 3. Battery and Charging Issues
*   Use standard 5V/1A or 5V/2A adapters. Do not use high-wattage fast chargers (>25W) as they can damage the smartwatch battery.
*   Clean the gold charging pins on the back of the watch using a dry cloth or eraser to remove sweat/dirt buildup.
*   If the screen does not light up when charging, leave it connected for at least 30 minutes to revive a deeply discharged battery.
