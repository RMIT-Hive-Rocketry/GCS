# Cleans up and removes empty logs
from glob import glob
import os

if __name__ == "__main__":
    # Root directory
    root = "logs"

    # Minimum number of lines for a log to not be deleted
    min_lines = 5

    # Loop through and read all log files
    for filename in glob(f"{root}/**/*.csv", recursive=True):
        with open(filename) as log_file:
            # Count number of lines in each file
            lines = len(
                [
                    line
                    for line in log_file.read().strip().split()
                    if len(line) > 0
                ]
            )

            # Delete files if number of lines is less than minimum
            if lines < min_lines:
                print(f"Deleted {filename} ({lines} lines)")
                os.remove(filename)

    # Delete empty folders recursively from child to parent folders
    deleted = set()
    for current_dir, subdirs, files in os.walk(root, topdown=False):
        still_has_subdirs = False
        for subdir in subdirs:
            if os.path.join(current_dir, subdir) not in deleted:
                still_has_subdirs = True
                break
        if not any(files) and not still_has_subdirs:
            os.rmdir(current_dir)
            deleted.add(current_dir)
            print(f"Deleted directory {current_dir}")
