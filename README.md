# ULP File Organizer

## Description

The ULP File Organizer is a powerful and user-friendly desktop application designed to streamline the process of managing and validating large data files. This tool efficiently processes a target file, validates each line against a set of predefined rules, and appends the valid, unique lines to a master file. It also intelligently categorizes and logs any rejected lines, making it easy to identify and resolve data inconsistencies.

Whether you're cleaning up extensive datasets, merging multiple files, or simply organizing your data, the ULP File Organizer provides a seamless and intuitive solution. Its multithreaded architecture ensures that the application remains responsive even when handling files with millions of lines, while the real-time progress indicators keep you informed every step of the way.

## Features

-   **Intuitive Graphical User Interface (GUI):** A clean and modern interface built with PyQt5 for ease of use.
-   **Efficient File Processing:** Handles large files smoothly with a multithreaded backend, preventing the UI from freezing.
-   **Line-by-Line Validation:** Validates each line in the target file to ensure it meets the required format (three parts separated by colons).
-   **Duplicate Detection:** Checks for and prevents duplicate entries from being added to the master file.
-   **Comprehensive Logging:** Automatically creates detailed logs for all rejected lines, categorized by the reason for rejection (e.g., "Not Enough Parts," "Empty Line," "Duplicate").
-   **Real-Time Progress Tracking:** Monitor the validation process with a progress bar and live statistics, including total, processed, valid, and rejected line counts.
-   **Process Control:** Full control over the validation process with start, pause, resume, and stop functionalities.
-   **Persistent Settings:** Remembers the last used file paths for a quicker workflow on subsequent uses.
-   **Cross-Platform:** Built with Python and PyQt5, making it compatible with Windows, macOS, and Linux.

## Installation

To run the ULP File Organizer, you need to have Python and the PyQt5 library installed.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/ULP-File-Organizer.git
    cd ULP-File-Organizer
    ```

2.  **Install the required dependencies:**
    Make sure you have Python 3 installed. Then, install the necessary library using pip:
    ```bash
    pip install PyQt5
    ```

## Usage

1.  **Run the application:**
    ```bash
    python main.py
    ```

2.  **Select the files:**
    -   Click on the **"Select Master File"** button to choose the file where all valid data will be stored. If the file doesn't exist, it will be created.
    -   Click on the **"Select Target File"** button to choose the file that you want to process and validate.

3.  **Start the process:**
    -   Once both files are selected, the **"Start"** button will be enabled.
    -   Click **"Start"** to begin the validation process.

4.  **Monitor and control:**
    -   The progress bar and statistics will update in real-time.
    -   Use the **"Pause"** button to temporarily halt the process and **"Resume"** to continue.
    -   Use the **"Stop"** button to terminate the process at any time.

5.  **Review the logs:**
    -   After the process is complete (or stopped), a `Logs` folder will be created in the project directory.
    -   Inside, you will find a timestamped folder containing detailed `.txt` files for each rejection category.

## Configuration

The application does not require any special configuration. The file paths for the master and target files are saved in a `ulp_validator_settings.txt` file in the project root for your convenience.

## Requirements / Dependencies

-   [Python 3](https://www.python.org/downloads/)
-   [PyQt5](https://pypi.org/project/PyQt5/)

## Folder Structure

```
ULP-File-Organizer/
├── .gitattributes
├── main.py
├── README.md
└── Logs/
    └── 03-09-2025 12-30-00 PM/
        ├── Duplicate.txt
        ├── Empty Line.txt
        └── Not Enough Parts.txt
```

-   **`main.py`**: The main script containing the application's logic and GUI.
-   **`README.md`**: This file.
-   **`Logs/`**: This directory is created automatically to store the log files from the validation process.

## Contributing

Contributions are welcome! If you have any ideas, suggestions, or bug reports, please open an issue or submit a pull request.

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
