Timeline Compactor & Splitter (Phone Takeout)

Prepare your Google Takeout exports for import into 3rd-party Timeline viewers with possible file size limits.

📌 What is this?

Google Timeline exports (Location History) generated via the Google Maps app on your phone can be massive and filled with redundant data. This script is a functional tool designed to process these specific JSON files. It compacts your data by removing noise and splits it into manageable, chronological parts to ensure compatibility with 3rd-party viewers that may have file size upload limits.
✨ Key Features

    Smart Compaction: Removes redundant WiFi records and filters out low-confidence activity logs.

    Coordinate Rounding: Saves significant space by rounding coordinates and probabilities without losing meaningful accuracy.

    Chronological Splitting: Keeps your timeline synchronized by splitting files based on time, ensuring related GPS points and semantic segments stay together.

    Detailed Savings Report: The console provides a byte-perfect report of how much storage space was saved by each individual setting.

🚀 Compatibility

    Primary Target: Specifically developed and tested for seamless import into Dawarich (free self-hosted location tracker).

    Source Data: Requires JSON exports generated through Google Takeout on mobile devices.

🛠 Usage

    Ensure you have Python installed.

    Open the script in a text editor to adjust settings (e.g., set your MAX_FILE_SIZE_MB or define a FILTER_START_DATE).

    Drag and drop your Google Takeout JSON file onto the script.

    The status window will display the exact storage savings achieved by each configuration.

🤝 Contributions & Testing

Your feedback is highly valued! If you use this script with other importers or 3rd-party viewers, please share your results. Suggestions for improvements or code contributions are always welcome.
